"""
Payments + Invoice generation (Task 09).
"""
import uuid
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from core.deps import get_db, get_current_user
from core.access import user_can_view_customer
from models import Payment, Invoice, Order, Customer
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api", tags=["payments"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class PaymentCreate(BaseModel):
    customer_id: str; order_id: str
    amount: float = Query(gt=0)
    payment_method: str = "card"
    reference: Optional[str] = None


class PaymentResponse(BaseModel):
    id: str; customer_id: str; order_id: str; amount: float
    payment_method: str; status: str; reference: Optional[str]
    transaction_ref: Optional[str]; created_at: str


class InvoiceResponse(BaseModel):
    id: str; customer_id: str; order_id: str; invoice_number: str
    amount: float; tax_amount: float; total_amount: float
    status: str; issued_date: str; due_date: str
    paid_at: Optional[str]; created_at: str
    customer_name: str


# ─── Payments ─────────────────────────────────────────────────────────────────

@router.post("/payments", response_model=PaymentResponse, status_code=201)
def record_payment(
    data: PaymentCreate,
    db: Session = Depends(get_db),
    cu: dict = Depends(get_current_user),
):
    if not user_can_view_customer(cu, data.customer_id, db):
        raise HTTPException(403, "Not authorised")

    order = db.query(Order).filter(Order.id == data.order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")

    total_paid = db.query(func.sum(Payment.amount)).filter(
        Payment.order_id == data.order_id, Payment.status == "completed"
    ).scalar() or 0

    if total_paid + data.amount > float(order.total_amount):
        raise HTTPException(400, f"Overpayment: order total is {order.total_amount}, already paid {total_paid}")

    now = datetime.utcnow()
    payment = Payment(
        id=str(uuid.uuid4()), customer_id=data.customer_id, order_id=data.order_id,
        amount=data.amount, payment_method=data.payment_method,
        status="completed", reference=data.reference,
        transaction_ref=str(uuid.uuid4())[:12].upper(),
        created_at=now,
    )
    db.add(payment)

    # Update order paid amount
    order.total_paid = float(order.total_paid or 0) + data.amount
    if order.total_paid >= float(order.total_amount):
        order.payment_status = "paid"

    db.commit()
    db.refresh(payment)
    return _pay_response(payment)


@router.get("/customers/{customer_id}/payments")
def list_payments(
    customer_id: str, order_id: str | None = None,
    db: Session = Depends(get_db), cu: dict = Depends(get_current_user),
):
    if not user_can_view_customer(cu, customer_id, db):
        raise HTTPException(403, "Not authorised")
    q = db.query(Payment).filter(Payment.customer_id == customer_id)
    if order_id:
        q = q.filter(Payment.order_id == order_id)
    return [_pay_response(p) for p in q.order_by(Payment.created_at.desc()).all()]


# ─── Invoices ─────────────────────────────────────────────────────────────────

@router.post("/invoices", response_model=InvoiceResponse, status_code=201)
def create_invoice(
    customer_id: str, order_id: str,
    tax_rate: float = Query(default=0.0, ge=0, le=1),
    due_days: int = Query(default=30, ge=1),
    db: Session = Depends(get_db),
    cu: dict = Depends(get_current_user),
):
    if not user_can_view_customer(cu, customer_id, db):
        raise HTTPException(403, "Not authorised")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")

    # Generate invoice number
    count = db.query(func.count(Invoice.id)).scalar() or 0
    invoice_number = f"INV-{datetime.utcnow().year}-{str(count + 1).zfill(5)}"

    issued = date.today()
    due = issued + __import__("datetime").timedelta(days=due_days)
    amount = float(order.total_amount or 0)
    tax = round(amount * tax_rate, 2)
    total = amount + tax

    invoice = Invoice(
        id=str(uuid.uuid4()), customer_id=customer_id, order_id=order_id,
        invoice_number=invoice_number,
        amount=amount, tax_amount=tax, total_amount=total,
        status="issued", issued_date=issued, due_date=due,
        created_at=datetime.utcnow(),
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    return _inv_response(invoice, customer)


@router.get("/customers/{customer_id}/invoices")
def list_invoices(
    customer_id: str,
    status: str | None = None,
    db: Session = Depends(get_db), cu: dict = Depends(get_current_user),
):
    if not user_can_view_customer(cu, customer_id, db):
        raise HTTPException(403, "Not authorised")
    q = db.query(Invoice).filter(Invoice.customer_id == customer_id)
    if status:
        q = q.filter(Invoice.status == status)
    invoices = q.order_by(Invoice.issued_date.desc()).all()
    return [_inv_response(inv, None) for inv in invoices]


@router.patch("/invoices/{inv_id}/paid")
def mark_invoice_paid(
    inv_id: str,
    db: Session = Depends(get_db),
    cu: dict = Depends(get_current_user),
):
    inv = db.query(Invoice).filter(Invoice.id == inv_id).first()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    if not user_can_view_customer(cu, inv.customer_id, db):
        raise HTTPException(403, "Not authorised")
    inv.status = "paid"
    inv.paid_at = datetime.utcnow()
    db.commit()
    customer = db.query(Customer).filter(Customer.id == inv.customer_id).first()
    return _inv_response(inv, customer)


def _pay_response(p: Payment) -> dict:
    return {
        "id": str(p.id), "customer_id": str(p.customer_id), "order_id": str(p.order_id),
        "amount": float(p.amount), "payment_method": p.payment_method,
        "status": p.status, "reference": p.reference,
        "transaction_ref": p.transaction_ref,
        "created_at": p.created_at.isoformat() if p.created_at else "",
    }


def _inv_response(inv: Invoice, customer: Customer | None) -> dict:
    return {
        "id": str(inv.id), "customer_id": str(inv.customer_id), "order_id": str(inv.order_id),
        "invoice_number": inv.invoice_number,
        "amount": float(inv.amount), "tax_amount": float(inv.tax_amount or 0),
        "total_amount": float(inv.total_amount),
        "status": inv.status,
        "issued_date": inv.issued_date.isoformat() if inv.issued_date else "",
        "due_date": inv.due_date.isoformat() if inv.due_date else "",
        "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
        "created_at": inv.created_at.isoformat() if inv.created_at else "",
        "customer_name": customer.name if customer else "",
    }