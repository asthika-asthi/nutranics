"""
Communications — Email + Broadcast (Task 11).
"""
import uuid
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.deps import get_db, get_current_user
from models import CommunicationLog, AppointmentReminder, Customer, Practitioner, Appointment
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/communications", tags=["communications"])


class EmailSendRequest(BaseModel):
    customer_id: str; subject: str; body: str
    appointment_id: str | None = None; order_id: str | None = None


class EmailResponse(BaseModel):
    id: str; customer_id: str; subject: str; status: str
    sent_at: Optional[str]; error: Optional[str]
    created_at: str


class BroadcastCreate(BaseModel):
    customer_ids: list[str]
    subject: str; body: str
    channel: str = "email"


class BroadcastResponse(BaseModel):
    total: int; sent: int; failed: int
    errors: list[str]


@router.post("/send", response_model=EmailResponse, status_code=201)
def send_email(
    data: EmailSendRequest,
    db: Session = Depends(get_db),
    cu: dict = Depends(get_current_user),
):
    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise HTTPException(404, "Customer not found")

    now = datetime.utcnow()
    log = CommunicationLog(
        id=str(uuid.uuid4()), customer_id=data.customer_id,
        channel="email", subject=data.subject, body=data.body,
        status="sent", sent_at=now,
        created_by=cu["id"], created_at=now,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return EmailResponse(
        id=str(log.id), customer_id=str(log.customer_id),
        subject=log.subject, status=log.status,
        sent_at=log.sent_at.isoformat() if log.sent_at else None,
        error=None, created_at=log.created_at.isoformat() if log.created_at else "",
    )


@router.get("/customers/{customer_id}")
def list_customer_communications(
    customer_id: str,
    channel: str | None = None,
    db: Session = Depends(get_db),
    cu: dict = Depends(get_current_user),
):
    q = db.query(CommunicationLog).filter(CommunicationLog.customer_id == customer_id)
    if channel:
        q = q.filter(CommunicationLog.channel == channel)
    logs = q.order_by(CommunicationLog.created_at.desc()).limit(100).all()
    return [
        {"id": str(l.id), "customer_id": str(l.customer_id), "channel": l.channel,
         "subject": l.subject, "status": l.status,
         "sent_at": l.sent_at.isoformat() if l.sent_at else None,
         "created_at": l.created_at.isoformat() if l.created_at else ""}
        for l in logs
    ]


@router.post("/broadcast", response_model=BroadcastResponse, status_code=201)
def send_broadcast(
    data: BroadcastCreate,
    db: Session = Depends(get_db),
    cu: dict = Depends(get_current_user),
):
    """Stub broadcast: creates a CommunicationLog for each recipient."""
    sent = failed = 0
    errors = []
    now = datetime.utcnow()
    for cid in data.customer_ids:
        try:
            log = CommunicationLog(
                id=str(uuid.uuid4()), customer_id=cid,
                channel=data.channel, subject=data.subject, body=data.body,
                status="sent", sent_at=now,
                created_by=cu["id"], created_at=now,
            )
            db.add(log)
            sent += 1
        except Exception as e:
            failed += 1
            if len(errors) < 10:
                errors.append(f"{cid}: {e}")
    db.commit()
    return BroadcastResponse(total=len(data.customer_ids), sent=sent, failed=failed, errors=errors)


@router.get("/reminders/pending")
def list_pending_reminders(
    in_days: int = Query(default=1, ge=0, le=7),
    db: Session = Depends(get_db),
    cu: dict = Depends(get_current_user),
):
    """Return appointment reminders due in the next N days that haven't been sent."""
    today = date.today()
    window_end = today + timedelta(days=in_days + 1)
    reminders = (
        db.query(AppointmentReminder)
        .filter(
            AppointmentReminder.appointment_id != None,
            AppointmentReminder.sent_at == None,
        )
        .all()
    )
    result = []
    for r in reminders:
        appt = db.query(Appointment).filter(Appointment.id == r.appointment_id).first()
        if not appt:
            continue
        appt_date = appt.scheduled_at.date()
        if today <= appt_date <= window_end:
            customer = db.query(Customer).filter(Customer.id == appt.customer_id).first()
            result.append({
                "reminder_id": str(r.id),
                "appointment_id": str(appt.id),
                "customer_id": str(appt.customer_id),
                "customer_name": customer.name if customer else "",
                "practitioner_name": db.query(Practitioner).filter(Practitioner.id == appt.practitioner_id).first().name if appt.practitioner_id else "",
                "scheduled_at": appt.scheduled_at.isoformat() if appt.scheduled_at else "",
                "type": appt.type,
                "reminder_type": r.reminder_type,
            })
    return result


@router.patch("/reminders/{reminder_id}/sent")
def mark_reminder_sent(
    reminder_id: str,
    db: Session = Depends(get_db),
    cu: dict = Depends(get_current_user),
):
    r = db.query(AppointmentReminder).filter(AppointmentReminder.id == reminder_id).first()
    if not r:
        raise HTTPException(404, "Reminder not found")
    r.sent_at = datetime.utcnow()
    db.commit()
    return {"id": str(r.id), "sent_at": r.sent_at.isoformat()}