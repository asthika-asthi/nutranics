import uuid
import os
from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from core.deps import get_db, get_current_user
from core.access import user_can_view_customer, user_can_edit_customer, get_visible_customer_ids
from models import Customer, CustomerAssignment, CustomerNote, User
from pydantic import BaseModel

router = APIRouter(prefix="/api/customers", tags=["customers"])


# ─── Schemas ───────────────────────────────────────────────────────────────────

class HealthFlags(BaseModel):
    pregnant: bool | None = None
    allergies: list[str] = []
    medications: list[str] = []
    conditions: list[str] = []

class CustomerCreate(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    dob: str | None = None  # ISO date string
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    postcode: str | None = None
    source: str | None = None
    preferred_contact: str = "email"
    health_flags: dict | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    tags: list[str] | None = None

class CustomerUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    dob: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    postcode: str | None = None
    source: str | None = None
    preferred_contact: str | None = None
    health_flags: dict | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    tags: list[str] | None = None
    is_active: bool | None = None

class CustomerResponse(BaseModel):
    id: str
    practitioner_id: str
    name: str
    phone: str | None
    email: str | None
    dob: str | None
    address_line1: str | None
    address_line2: str | None
    city: str | None
    postcode: str | None
    source: str | None
    preferred_contact: str
    health_flags: dict | None
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    tags: list[str] | None
    is_active: bool
    created_at: str
    updated_at: str
    primary_practitioner_name: str | None = None

    class Config:
        from_attributes = True

class CustomerListResponse(BaseModel):
    items: list[CustomerResponse]
    total: int
    page: int
    page_size: int


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _parse_dob(dob_str: str | None) -> date | None:
    if not dob_str:
        return None
    return date.fromisoformat(dob_str)

def _build_customer_response(customer: Customer, practitioner_name: str | None = None) -> CustomerResponse:
    return CustomerResponse(
        id=str(customer.id),
        practitioner_id=str(customer.practitioner_id),
        name=customer.name,
        phone=customer.phone,
        email=customer.email,
        dob=customer.dob.isoformat() if customer.dob else None,
        address_line1=customer.address_line1,
        address_line2=customer.address_line2,
        city=customer.city,
        postcode=customer.postcode,
        source=customer.source,
        preferred_contact=customer.preferred_contact,
        health_flags=customer.health_flags,
        emergency_contact_name=customer.emergency_contact_name,
        emergency_contact_phone=customer.emergency_contact_phone,
        tags=customer.tags,
        is_active=customer.is_active,
        created_at=customer.created_at.isoformat() if customer.created_at else "",
        updated_at=customer.updated_at.isoformat() if customer.updated_at else "",
        primary_practitioner_name=practitioner_name,
    )


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("", response_model=CustomerResponse, status_code=201)
def create_customer(
    data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create a new customer. Practitioners can only create for themselves."""
    user_role = current_user.get("role")

    if user_role == "practitioner":
        practitioner_id = current_user.get("practitioner_id")
        if not practitioner_id:
            raise HTTPException(status_code=403, detail="No practitioner_id")
    elif user_role in ("owner", "admin"):
        # Must specify practitioner_id in data or use their own
        practitioner_id = current_user.get("practitioner_id")
    else:
        raise HTTPException(status_code=403, detail="Not authorised to create customers")

    dob = _parse_dob(data.dob)
    now = datetime.utcnow()

    customer = Customer(
        id=str(uuid.uuid4()),
        practitioner_id=practitioner_id,
        name=data.name,
        phone=data.phone,
        email=data.email,
        dob=dob,
        address_line1=data.address_line1,
        address_line2=data.address_line2,
        city=data.city,
        postcode=data.postcode,
        source=data.source,
        preferred_contact=data.preferred_contact,
        health_flags=data.health_flags,
        emergency_contact_name=data.emergency_contact_name,
        emergency_contact_phone=data.emergency_contact_phone,
        tags=data.tags,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    return _build_customer_response(customer)


@router.get("", response_model=CustomerListResponse)
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List customers with optional search and filters. Access controlled by role."""
    q = db.query(Customer)

    # Practitioner: only their assigned customers
    visible_ids = get_visible_customer_ids(current_user, db)
    if visible_ids:
        q = q.filter(Customer.id.in_(visible_ids))
    # owner/admin: all customers

    if search:
        q = q.filter(
            or_(
                Customer.name.ilike(f"%{search}%"),
                Customer.email.ilike(f"%{search}%"),
                Customer.phone.ilike(f"%{search}%"),
            )
        )

    if is_active is not None:
        q = q.filter(Customer.is_active == is_active)

    total = q.count()
    customers = q.order_by(Customer.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = [_build_customer_response(c) for c in customers]
    return CustomerListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get a single customer by ID."""
    if not user_can_view_customer(current_user, customer_id, db):
        raise HTTPException(status_code=403, detail="Not authorised to view this customer")

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return _build_customer_response(customer)


@router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: str,
    data: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update customer fields. Access controlled."""
    if not user_can_edit_customer(current_user, customer_id, db):
        raise HTTPException(status_code=403, detail="Not authorised to edit this customer")

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Apply updates
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "dob" and value:
            value = _parse_dob(value)
        if hasattr(customer, field):
            setattr(customer, field, value)

    customer.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(customer)

    return _build_customer_response(customer)


@router.delete("/{customer_id}", status_code=204)
def archive_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Soft-delete: set is_active=False. Owner/admin only."""
    if current_user.get("role") not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only owner/admin can archive customers")

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    customer.is_active = False
    customer.updated_at = datetime.utcnow()
    db.commit()