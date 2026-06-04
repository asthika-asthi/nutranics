"""
Subscriptions + PlanSlot management (Task 06).

ERD model mapping:
  Plan.is_template=True  → subscription plan template
  PlanItem                → line items belonging to a Plan template
  Subscription            → per-customer active plan instance  ← "Treatment Plan" in PRD
  PlanSlot                → scheduled treatment slots within a Subscription

Key flows:
  POST /subscriptions           → create a customer subscription (from a plan template)
  GET  /subscriptions/{sub_id}   → get subscription with its plan_slots
  PATCH /subscriptions/{sub_id}/status   → pause / cancel / resume
  GET  /subscriptions/customers/{customer_id}   → all subscriptions for a customer
  POST /subscriptions/{sub_id}/slots          → schedule remaining plan items as slots
  PATCH /subscriptions/slots/{slot_id}         → mark slot attended / missed / cancelled
"""
import uuid
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from core.deps import get_db, get_current_user
from core.access import user_can_edit_customer, user_can_view_customer
from models import Subscription, Plan, PlanItem, PlanSlot
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class SlotResponse(BaseModel):
    id: str; subscription_id: str; plan_item_id: str
    item_type: str; item_name: str
    suggested_date: str; booking_window_start: str; booking_window_end: str
    status: str; appointment_id: Optional[str]
    missed_reason: Optional[str]; created_at: str


class SubscriptionCreate(BaseModel):
    customer_id: str
    plan_id: str
    start_date: str  # ISO date
    billing_day: int = Query(ge=1, le=31)


class SubscriptionResponse(BaseModel):
    id: str; customer_id: str; plan_id: str; status: str
    start_date: str; billing_day: int; next_billing_date: str
    paused_at: Optional[str]; pause_resume_date: Optional[str]
    cancelled_at: Optional[str]; cancel_reason: Optional[str]
    cancellation_fee: Optional[float]; total_billed: float; total_paid: float
    plan_name: str; plan_monthly_price: float
    created_at: str


def _d(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


def _next_billing(start: date, billing_day: int) -> date:
    """Return next billing date on or after start."""
    year, month = start.year, start.month
    day = min(billing_day, 28)  # safe for all months
    next_date = date(year, month, day)
    if next_date <= start:
        month += 1
        if month > 12:
            month, year = 1, year + 1
        day = min(billing_day, 28)
        next_date = date(year, month, day)
    return next_date


# ─── Subscriptions ─────────────────────────────────────────────────────────────

@router.post("/", response_model=SubscriptionResponse, status_code=201)
def create_subscription(
    data: SubscriptionCreate,
    db: Session = Depends(get_db),
    cu: dict = Depends(get_current_user),
):
    if not user_can_edit_customer(cu, data.customer_id, db):
        raise HTTPException(403, "Not authorised")

    plan = db.query(Plan).filter(Plan.id == data.plan_id, Plan.is_template == True).first()
    if not plan:
        raise HTTPException(404, "Plan template not found")

    start = _d(data.start_date)
    next_bill = _next_billing(start, data.billing_day)

    now = datetime.utcnow()
    sub = Subscription(
        id=str(uuid.uuid4()), customer_id=data.customer_id, plan_id=data.plan_id,
        status="active", start_date=start, billing_day=data.billing_day,
        next_billing_date=next_bill, months_billed=0,
        current_cycle_start=start, current_cycle_end=next_bill,
        created_at=now, updated_at=now,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    return _sub_response(sub, plan, [])


@router.get("/customers/{customer_id}")
def list_customer_subscriptions(
    customer_id: str,
    status: str | None = None,
    db: Session = Depends(get_db),
    cu: dict = Depends(get_current_user),
):
    if not user_can_view_customer(cu, customer_id, db):
        raise HTTPException(403, "Not authorised")

    q = db.query(Subscription).filter(Subscription.customer_id == customer_id)
    if status:
        q = q.filter(Subscription.status == status)

    subs = q.order_by(Subscription.start_date.desc()).all()
    result = []
    for s in subs:
        plan = db.query(Plan).filter(Plan.id == s.plan_id).first()
        slots = db.query(PlanSlot).filter(PlanSlot.subscription_id == s.id).order_by(PlanSlot.suggested_date).all()
        result.append(_sub_response(s, plan, slots))
    return result


@router.get("/{sub_id}", response_model=SubscriptionResponse)
def get_subscription(
    sub_id: str,
    db: Session = Depends(get_db),
    cu: dict = Depends(get_current_user),
):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(404, "Subscription not found")
    if not user_can_view_customer(cu, sub.customer_id, db):
        raise HTTPException(403, "Not authorised")
    plan = db.query(Plan).filter(Plan.id == sub.plan_id).first()
    slots = db.query(PlanSlot).filter(PlanSlot.subscription_id == sub_id).order_by(PlanSlot.suggested_date).all()
    return _sub_response(sub, plan, slots)


@router.patch("/{sub_id}/status", response_model=SubscriptionResponse)
def update_subscription_status(
    sub_id: str,
    status: str = Query(...),
    cancel_reason: str | None = None,
    cancellation_fee: float | None = None,
    db: Session = Depends(get_db),
    cu: dict = Depends(get_current_user),
):
    """Transition subscription status: active→paused→active, or active→cancelled."""
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(404, "Subscription not found")
    if not user_can_edit_customer(cu, sub.customer_id, db):
        raise HTTPException(403, "Not authorised")

    valid = {"active": ("paused", "cancelled"), "paused": ("active", "cancelled")}
    allowed = valid.get(sub.status, ())
    if status not in allowed:
        raise HTTPException(400, f"Cannot transition from {sub.status} to {status}")

    today = date.today()
    if status == "paused":
        sub.paused_at = today
        sub.pause_resume_date = None
    elif status == "active" and sub.status == "paused":
        sub.pause_resume_date = today
    elif status == "cancelled":
        sub.cancelled_at = today
        sub.cancel_reason = cancel_reason
        sub.cancellation_fee = cancellation_fee

    sub.status = status
    sub.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(sub)
    plan = db.query(Plan).filter(Plan.id == sub.plan_id).first()
    slots = db.query(PlanSlot).filter(PlanSlot.subscription_id == sub_id).all()
    return _sub_response(sub, plan, slots)


# ─── Plan Slots ────────────────────────────────────────────────────────────────

@router.post("/{sub_id}/slots", status_code=201)
def schedule_slots(
    sub_id: str,
    start_date: str = Query(..., description="ISO date to start scheduling from"),
    db: Session = Depends(get_db),
    cu: dict = Depends(get_current_user),
):
    """
    Generate PlanSlot records for all pending plan items in the subscription's plan template.
    Each item becomes a slot with a suggested_date (bi-weekly intervals) and a 5-day booking window.
    """
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(404, "Subscription not found")
    if not user_can_edit_customer(cu, sub.customer_id, db):
        raise HTTPException(403, "Not authorised")
    if sub.status not in ("active", "paused"):
        raise HTTPException(400, "Can only schedule slots for active or paused subscriptions")

    # Get existing slot plan item ids
    existing = {s.plan_item_id for s in db.query(PlanSlot).filter(PlanSlot.subscription_id == sub_id).all()}

    # Get plan template items
    template_items = (
        db.query(PlanItem)
        .filter(PlanItem.plan_id == sub.plan_id, PlanItem.id.notin_(existing))
        .order_by(PlanItem.order_index)
        .all()
    )
    if not template_items:
        return {"scheduled": 0, "slots": []}

    start = _d(start_date)
    now = datetime.utcnow()
    created = []
    slot_date = start

    for item in template_items:
        window_end = slot_date + timedelta(days=5)
        slot = PlanSlot(
            id=str(uuid.uuid4()), subscription_id=sub_id, plan_item_id=item.id,
            item_type=item.item_type, item_name=item.item_name,
            suggested_date=slot_date, booking_window_start=slot_date,
            booking_window_end=window_end,
            status="pending", created_at=now,
        )
        db.add(slot)
        created.append(slot)
        # Advance bi-weekly
        slot_date += timedelta(days=14)

    db.commit()
    return {
        "scheduled": len(created),
        "slots": [
            SlotResponse(
                id=str(s.id), subscription_id=str(s.subscription_id),
                plan_item_id=str(s.plan_item_id), item_type=s.item_type, item_name=s.item_name,
                suggested_date=s.suggested_date.isoformat() if s.suggested_date else "",
                booking_window_start=s.booking_window_start.isoformat() if s.booking_window_start else "",
                booking_window_end=s.booking_window_end.isoformat() if s.booking_window_end else "",
                status=s.status, appointment_id=s.appointment_id,
                missed_reason=s.missed_reason,
                created_at=s.created_at.isoformat() if s.created_at else "",
            )
            for s in created
        ],
    }


@router.get("/{sub_id}/slots")
def list_slots(
    sub_id: str,
    status: str | None = None,
    db: Session = Depends(get_db),
    cu: dict = Depends(get_current_user),
):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(404, "Subscription not found")
    if not user_can_view_customer(cu, sub.customer_id, db):
        raise HTTPException(403, "Not authorised")

    q = db.query(PlanSlot).filter(PlanSlot.subscription_id == sub_id)
    if status:
        q = q.filter(PlanSlot.status == status)

    slots = q.order_by(PlanSlot.suggested_date).all()
    return [_slot_response(s) for s in slots]


@router.patch("/slots/{slot_id}")
def update_slot(
    slot_id: str,
    status: str | None = None,
    appointment_id: str | None = None,
    missed_reason: str | None = None,
    db: Session = Depends(get_db),
    cu: dict = Depends(get_current_user),
):
    """
    Update slot status (pending → booked → attended / missed).
    When status=attended → set appointment_id.
    When status=missed  → optionally set missed_reason.
    """
    slot = db.query(PlanSlot).filter(PlanSlot.id == slot_id).first()
    if not slot:
        raise HTTPException(404, "Slot not found")

    sub = db.query(Subscription).filter(Subscription.id == slot.subscription_id).first()
    if not sub or not user_can_edit_customer(cu, sub.customer_id, db):
        raise HTTPException(403, "Not authorised")

    if status:
        valid = {"pending": ("booked", "cancelled"), "booked": ("attended", "missed", "cancelled")}
        allowed = valid.get(slot.status, ())
        if status not in allowed:
            raise HTTPException(400, f"Cannot transition from {slot.status} to {status}")
        slot.status = status
        if status == "missed":
            slot.missed_at = datetime.utcnow()
            slot.missed_reason = missed_reason
        if appointment_id is not None:
            slot.appointment_id = appointment_id

    db.commit()
    db.refresh(slot)
    return _slot_response(slot)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _sub_response(sub: Subscription, plan: Plan | None, slots: list[PlanSlot]) -> dict:
    return {
        "id": str(sub.id),
        "customer_id": str(sub.customer_id),
        "plan_id": str(sub.plan_id),
        "status": sub.status,
        "start_date": sub.start_date.isoformat() if sub.start_date else "",
        "billing_day": sub.billing_day,
        "next_billing_date": sub.next_billing_date.isoformat() if sub.next_billing_date else "",
        "paused_at": sub.paused_at.isoformat() if sub.paused_at else None,
        "pause_resume_date": sub.pause_resume_date.isoformat() if sub.pause_resume_date else None,
        "cancelled_at": sub.cancelled_at.isoformat() if sub.cancelled_at else None,
        "cancel_reason": sub.cancel_reason,
        "cancellation_fee": float(sub.cancellation_fee) if sub.cancellation_fee else None,
        "total_billed": float(sub.total_billed or 0),
        "total_paid": float(sub.total_paid or 0),
        "plan_name": plan.name if plan else "",
        "plan_monthly_price": float(plan.monthly_price) if plan and plan.monthly_price else 0.0,
        "created_at": sub.created_at.isoformat() if sub.created_at else "",
        "slots": [_slot_response(s) for s in slots],
    }


def _slot_response(s: PlanSlot) -> SlotResponse:
    return SlotResponse(
        id=str(s.id), subscription_id=str(s.subscription_id), plan_item_id=str(s.plan_item_id),
        item_type=s.item_type, item_name=s.item_name,
        suggested_date=s.suggested_date.isoformat() if s.suggested_date else "",
        booking_window_start=s.booking_window_start.isoformat() if s.booking_window_start else "",
        booking_window_end=s.booking_window_end.isoformat() if s.booking_window_end else "",
        status=s.status, appointment_id=s.appointment_id,
        missed_reason=s.missed_reason,
        created_at=s.created_at.isoformat() if s.created_at else "",
    )