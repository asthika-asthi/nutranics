"""
Appointments router (Task 07).

Model fields: type, location, scheduled_at, duration_mins, status (scheduled|confirmed|checked_in|completed|no_show|cancelled)
No room_id — rooms are not in the actual Appointment model.
Conflict detection: practitioner + time overlap.
Status transitions: scheduled→confirmed→checked_in→completed; or any →cancelled/no_show.
"""
import uuid
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.deps import get_db, get_current_user
from core.access import user_can_view_customer, user_can_edit_customer
from models import Appointment, Customer, Practitioner, PractitionerAvailability, PractitionerAbsence, Room, PlanSlot
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/appointments", tags=["appointments"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class AppointmentCreate(BaseModel):
    customer_id: str
    practitioner_id: str
    plan_slot_id: Optional[str] = None
    type: str = "consultation"
    location: str = "clinic"
    address: Optional[str] = None
    scheduled_at: str
    duration_mins: int = Query(ge=15, le=480, default=60)
    status: str = "scheduled"
    notes: Optional[str] = None
    parent_appointment_id: Optional[str] = None


class AppointmentUpdate(BaseModel):
    practitioner_id: Optional[str] = None
    type: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    scheduled_at: Optional[str] = None
    duration_mins: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    cancellation_reason: Optional[str] = None


class AppointmentResponse(BaseModel):
    id: str; customer_id: str; practitioner_id: str
    plan_slot_id: Optional[str]; type: str; location: str
    address: Optional[str]; status: str; scheduled_at: str
    duration_mins: int; notes: Optional[str]
    is_plan_generated: bool; parent_appointment_id: Optional[str]
    cancellation_reason: Optional[str]; check_in_token: Optional[str]
    next_reminder_at: Optional[str]
    customer_name: str; practitioner_name: str
    created_at: str; updated_at: str

    class Config:
        from_attributes = True


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# ─── Conflict detection ───────────────────────────────────────────────────────

def _check_practitioner_conflict(
    db: Session, practitioner_id: str, scheduled_at: datetime, duration_mins: int,
    exclude_id: str | None = None
) -> Appointment | None:
    end = scheduled_at + timedelta(minutes=duration_mins)
    q = db.query(Appointment).filter(
        Appointment.practitioner_id == practitioner_id,
        Appointment.status.in_(["scheduled", "confirmed", "checked_in"]),
        Appointment.scheduled_at < end,
        Appointment.scheduled_at + timedelta(minutes=Appointment.duration_mins) > scheduled_at,
    )
    if exclude_id:
        q = q.filter(Appointment.id != exclude_id)
    return q.first()


def _is_available_at(
    db: Session, practitioner_id: str, scheduled_at: datetime, duration_mins: int
) -> bool:
    dow = scheduled_at.weekday()
    t_start = scheduled_at.time()
    t_end = (scheduled_at + timedelta(minutes=duration_mins)).time()

    # Check for overlapping absence
    absence = db.query(PractitionerAbsence).filter(
        PractitionerAbsence.practitioner_id == practitioner_id,
        PractitionerAbsence.start_date <= scheduled_at.date(),
        PractitionerAbsence.end_date >= scheduled_at.date(),
    ).first()
    if absence and (absence.all_day or (
        absence.start_time and absence.end_time and
        absence.start_time < t_end and absence.end_time > t_start
    )):
        return False

    # Check availability window
    avail = db.query(PractitionerAvailability).filter(
        PractitionerAvailability.practitioner_id == practitioner_id,
        PractitionerAvailability.day_of_week == dow,
        PractitionerAvailability.is_available == True,
        PractitionerAvailability.start_time <= t_start,
        PractitionerAvailability.end_time >= t_end,
    ).first()
    return avail is not None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/", response_model=AppointmentResponse, status_code=201)
def create_appointment(
    data: AppointmentCreate,
    db: Session = Depends(get_db),
    cu: dict = Depends(get_current_user),
):
    if not user_can_edit_customer(cu, data.customer_id, db):
        raise HTTPException(403, "Not authorised")

    scheduled = _dt(data.scheduled_at)

    conflict = _check_practitioner_conflict(db, data.practitioner_id, scheduled, data.duration_mins)
    if conflict:
        raise HTTPException(409, detail=f"Practitioner conflict: {conflict.id}")

    if not _is_available_at(db, data.practitioner_id, scheduled, data.duration_mins):
        raise HTTPException(400, detail="Outside practitioner's available hours or on planned absence")

    now = datetime.utcnow()
    appt = Appointment(
        id=str(uuid.uuid4()), customer_id=data.customer_id,
        practitioner_id=data.practitioner_id, plan_slot_id=data.plan_slot_id,
        type=data.type, location=data.location, address=data.address,
        status=data.status, scheduled_at=scheduled,
        duration_mins=data.duration_mins, notes=data.notes,
        parent_appointment_id=data.parent_appointment_id,
        check_in_token=str(uuid.uuid4())[:8],
        created_at=now, updated_at=now,
    )
    db.add(appt)

    if data.plan_slot_id:
        slot = db.query(PlanSlot).filter(PlanSlot.id == data.plan_slot_id).first()
        if slot:
            slot.status = "booked"
            slot.appointment_id = appt.id

    db.commit()
    db.refresh(appt)
    return _appt_response(db, appt)


@router.get("/customers/{customer_id}")
def list_customer_appointments(
    customer_id: str,
    status: str | None = None,
    from_date: str | None = None,
    db: Session = Depends(get_db),
    cu: dict = Depends(get_current_user),
):
    if not user_can_view_customer(cu, customer_id, db):
        raise HTTPException(403, "Not authorised")

    q = db.query(Appointment).filter(Appointment.customer_id == customer_id)
    if status:
        q = q.filter(Appointment.status == status)
    if from_date:
        q = q.filter(Appointment.scheduled_at >= _dt(from_date))
    appts = q.order_by(Appointment.scheduled_at.desc()).all()
    return [_appt_response(db, a) for a in appts]


@router.get("/{appt_id}", response_model=AppointmentResponse)
def get_appointment(
    appt_id: str,
    db: Session = Depends(get_db),
    cu: dict = Depends(get_current_user),
):
    appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not appt:
        raise HTTPException(404, "Appointment not found")
    if not user_can_view_customer(cu, appt.customer_id, db):
        raise HTTPException(403, "Not authorised")
    return _appt_response(db, appt)


@router.patch("/{appt_id}", response_model=AppointmentResponse)
def update_appointment(
    appt_id: str,
    data: AppointmentUpdate,
    db: Session = Depends(get_db),
    cu: dict = Depends(get_current_user),
):
    appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not appt:
        raise HTTPException(404, "Appointment not found")
    if not user_can_edit_customer(cu, appt.customer_id, db):
        raise HTTPException(403, "Not authorised")

    practitioner_id = data.practitioner_id or appt.practitioner_id
    scheduled = _dt(data.scheduled_at) if data.scheduled_at else appt.scheduled_at
    duration = data.duration_mins or appt.duration_mins

    if data.scheduled_at or data.practitioner_id:
        conflict = _check_practitioner_conflict(db, practitioner_id, scheduled, duration, exclude_id=appt_id)
        if conflict:
            raise HTTPException(409, detail=f"Practitioner conflict: {conflict.id}")
        if not _is_available_at(db, practitioner_id, scheduled, duration):
            raise HTTPException(400, detail="Outside practitioner's available hours or on planned absence")

    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "scheduled_at":
            value = _dt(value)
        if hasattr(appt, field):
            setattr(appt, field, value)
    appt.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(appt)
    return _appt_response(db, appt)


@router.patch("/{appt_id}/status")
def transition_status(
    appt_id: str,
    status: str = Query(...),
    cancellation_reason: str | None = None,
    db: Session = Depends(get_db),
    cu: dict = Depends(get_current_user),
):
    valid = {
        "scheduled": ("confirmed", "cancelled"),
        "confirmed": ("checked_in", "cancelled", "no_show"),
        "checked_in": ("completed", "no_show"),
    }
    appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not appt:
        raise HTTPException(404, "Appointment not found")
    if not user_can_edit_customer(cu, appt.customer_id, db):
        raise HTTPException(403, "Not authorised")
    allowed = valid.get(appt.status, ())
    if status not in allowed:
        raise HTTPException(400, f"Cannot transition {appt.status} → {status}")
    appt.status = status
    if status == "cancelled":
        appt.cancellation_reason = cancellation_reason
    appt.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(appt)
    return _appt_response(db, appt)


# ─── Helper ───────────────────────────────────────────────────────────────────

def _appt_response(db: Session, appt: Appointment) -> dict:
    customer = db.query(Customer).filter(Customer.id == appt.customer_id).first()
    practitioner = db.query(Practitioner).filter(Practitioner.id == appt.practitioner_id).first()
    return {
        "id": str(appt.id),
        "customer_id": str(appt.customer_id),
        "practitioner_id": str(appt.practitioner_id),
        "plan_slot_id": str(appt.plan_slot_id) if appt.plan_slot_id else None,
        "type": appt.type,
        "location": appt.location,
        "address": appt.address,
        "status": appt.status,
        "scheduled_at": appt.scheduled_at.isoformat() if appt.scheduled_at else "",
        "duration_mins": appt.duration_mins,
        "notes": appt.notes,
        "is_plan_generated": appt.is_plan_generated,
        "parent_appointment_id": str(appt.parent_appointment_id) if appt.parent_appointment_id else None,
        "cancellation_reason": appt.cancellation_reason,
        "check_in_token": appt.check_in_token,
        "next_reminder_at": appt.next_reminder_at.isoformat() if appt.next_reminder_at else None,
        "customer_name": customer.name if customer else "",
        "practitioner_name": practitioner.name if practitioner else "",
        "created_at": appt.created_at.isoformat() if appt.created_at else "",
        "updated_at": appt.updated_at.isoformat() if appt.updated_at else "",
    }