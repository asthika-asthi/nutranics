import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.deps import get_db, get_current_user
from core.access import user_can_view_customer, user_can_edit_customer
from models import CustomerNote
from pydantic import BaseModel

router = APIRouter(prefix="/api/customers", tags=["customer notes"])


class NoteCreate(BaseModel):
    customer_id: str
    content: str
    note_type: str = "general"
    sync_id: str | None = None  # Client-generated UUID for offline dedup


class NoteUpdate(BaseModel):
    content: str | None = None
    note_type: str | None = None


class NoteResponse(BaseModel):
    id: str
    customer_id: str
    practitioner_id: str
    content: str
    note_type: str
    is_synced: bool
    sync_id: str | None
    created_at: str
    server_created_at: str

    class Config:
        from_attributes = True


@router.post("/{customer_id}/notes", response_model=NoteResponse, status_code=201)
def create_note(
    customer_id: str,
    data: NoteCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Add a note to a customer. Practitioners can only note their assigned customers."""
    if not user_can_edit_customer(current_user, customer_id, db):
        raise HTTPException(status_code=403, detail="Not authorised")

    # Verify customer exists
    from models import Customer
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Check dedup: if sync_id provided and already exists, return existing
    if data.sync_id:
        existing = db.query(CustomerNote).filter(
            CustomerNote.sync_id == data.sync_id
        ).first()
        if existing:
            return NoteResponse(
                id=str(existing.id),
                customer_id=str(existing.customer_id),
                practitioner_id=str(existing.practitioner_id),
                content=existing.content,
                note_type=existing.note_type,
                is_synced=existing.is_synced,
                sync_id=existing.sync_id,
                created_at=existing.created_at.isoformat() if existing.created_at else "",
                server_created_at=existing.server_created_at.isoformat() if existing.server_created_at else "",
            )

    practitioner_id = current_user.get("practitioner_id")
    if not practitioner_id:
        raise HTTPException(status_code=403, detail="No practitioner_id")

    # Use client-provided created_at if sync_id present (offline-created note)
    created_at = datetime.utcnow()
    server_created_at = datetime.utcnow()

    note = CustomerNote(
        id=str(uuid.uuid4()),
        customer_id=customer_id,
        practitioner_id=practitioner_id,
        content=data.content,
        note_type=data.note_type,
        is_synced=True,
        sync_id=data.sync_id,
        created_at=created_at,
        server_created_at=server_created_at,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    return NoteResponse(
        id=str(note.id),
        customer_id=str(note.customer_id),
        practitioner_id=str(note.practitioner_id),
        content=note.content,
        note_type=note.note_type,
        is_synced=note.is_synced,
        sync_id=note.sync_id,
        created_at=note.created_at.isoformat() if note.created_at else "",
        server_created_at=note.server_created_at.isoformat() if note.server_created_at else "",
    )


@router.get("/{customer_id}/notes")
def list_notes(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all notes for a customer."""
    if not user_can_view_customer(current_user, customer_id, db):
        raise HTTPException(status_code=403, detail="Not authorised")

    notes = db.query(CustomerNote).filter(
        CustomerNote.customer_id == customer_id
    ).order_by(CustomerNote.created_at.desc()).all()

    return [
        NoteResponse(
            id=str(n.id),
            customer_id=str(n.customer_id),
            practitioner_id=str(n.practitioner_id),
            content=n.content,
            note_type=n.note_type,
            is_synced=n.is_synced,
            sync_id=n.sync_id,
            created_at=n.created_at.isoformat() if n.created_at else "",
            server_created_at=n.server_created_at.isoformat() if n.server_created_at else "",
        )
        for n in notes
    ]


@router.patch("/{customer_id}/notes/{note_id}", response_model=NoteResponse)
def update_note(
    customer_id: str,
    note_id: str,
    data: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update a note. Only the note author (same practitioner) can edit."""
    if not user_can_edit_customer(current_user, customer_id, db):
        raise HTTPException(status_code=403, detail="Not authorised")

    note = db.query(CustomerNote).filter(
        CustomerNote.id == note_id,
        CustomerNote.customer_id == customer_id,
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if data.content is not None:
        note.content = data.content
    if data.note_type is not None:
        note.note_type = data.note_type

    db.commit()
    db.refresh(note)

    return NoteResponse(
        id=str(note.id),
        customer_id=str(note.customer_id),
        practitioner_id=str(note.practitioner_id),
        content=note.content,
        note_type=note.note_type,
        is_synced=note.is_synced,
        sync_id=note.sync_id,
        created_at=note.created_at.isoformat() if note.created_at else "",
        server_created_at=note.server_created_at.isoformat() if note.server_created_at else "",
    )