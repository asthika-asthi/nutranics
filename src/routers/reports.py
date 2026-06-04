"""
Reports + Dashboard (Task 12).
"""
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, Integer

from core.deps import get_db, get_current_user
from models import Customer, Appointment, Payment, Order, Subscription, Product, Practitioner, User
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/reports", tags=["reports"])


class KpiResponse(BaseModel):
    total_customers: int; active_subscriptions: int
    appointments_this_month: int; revenue_this_month: float
    appointments_last_month: int; revenue_last_month: float
    top_products: list[dict]; upcoming_appointments_count: int


class RevenueByDay(BaseModel):
    date: str; revenue: float; appointments: int


class CustomerGrowth(BaseModel):
    month: str; new_customers: int; total_customers: int


@router.get("/dashboard", response_model=KpiResponse)
def dashboard(
    db: Session = Depends(get_db),
    cu: dict = Depends(get_current_user),
):
    today = date.today()
    first_this_month = date(today.year, today.month, 1)
    first_last_month = (first_this_month - timedelta(days=1)).replace(day=1)

    # Customers
    total_customers = db.query(func.count(Customer.id)).scalar() or 0

    # Subscriptions
    active_subscriptions = db.query(func.count(Subscription.id)).filter(
        Subscription.status == "active"
    ).scalar() or 0

    # Appointments this month
    appts_this = db.query(func.count(Appointment.id)).filter(
        extract("year", Appointment.scheduled_at) == today.year,
        extract("month", Appointment.scheduled_at) == today.month,
        Appointment.status != "cancelled",
    ).scalar() or 0

    # Appointments last month
    appts_last = db.query(func.count(Appointment.id)).filter(
        extract("year", Appointment.scheduled_at) == first_last_month.year,
        extract("month", Appointment.scheduled_at) == first_last_month.month,
        Appointment.status != "cancelled",
    ).scalar() or 0

    # Revenue this month (completed payments)
    rev_this = db.query(func.sum(Payment.amount)).join(Order).filter(
        Payment.status == "completed",
        func.date(Payment.created_at) >= first_this_month,
    ).scalar() or 0

    # Revenue last month
    rev_last = db.query(func.sum(Payment.amount)).join(Order).filter(
        Payment.status == "completed",
        func.date(Payment.created_at) >= first_last_month,
        func.date(Payment.created_at) < first_this_month,
    ).scalar() or 0

    # Top products by transaction volume
    top_prods = db.query(
        Product.name, func.sum(ProductTransaction.quantity_change).label("qty")
    ).join(ProductTransaction).group_by(Product.name).order_by(func.sum(ProductTransaction.quantity_change).desc()).limit(5).all()

    # Upcoming appointments
    upcoming = db.query(func.count(Appointment.id)).filter(
        Appointment.scheduled_at >= datetime.utcnow(),
        Appointment.status.in_(["scheduled", "confirmed"]),
    ).scalar() or 0

    return KpiResponse(
        total_customers=total_customers,
        active_subscriptions=active_subscriptions,
        appointments_this_month=appts_this,
        revenue_this_month=float(rev_this),
        appointments_last_month=appts_last,
        revenue_last_month=float(rev_last),
        top_products=[{"name": p[0], "quantity_sold": p[1] or 0} for p in top_prods],
        upcoming_appointments_count=upcoming,
    )


@router.get("/revenue/daily")
def revenue_by_day(
    from_date: str = Query(...),
    to_date: str = Query(...),
    db: Session = Depends(get_db),
    cu: dict = Depends(get_current_user),
):
    """Daily revenue + appointment count for a date range."""
    fd = date.fromisoformat(from_date)
    td = date.fromisoformat(to_date)
    days = (td - fd).days + 1
    result = []
    for i in range(days):
        day = fd + timedelta(days=i)
        rev = db.query(func.sum(Payment.amount)).filter(
            Payment.status == "completed",
            func.date(Payment.created_at) == day,
        ).scalar() or 0
        appts = db.query(func.count(Appointment.id)).filter(
            func.date(Appointment.scheduled_at) == day,
            Appointment.status != "cancelled",
        ).scalar() or 0
        result.append({"date": day.isoformat(), "revenue": float(rev), "appointments": appts})
    return result


@router.get("/customers/growth")
def customer_growth(
    months: int = Query(default=6, ge=3, le=24),
    db: Session = Depends(get_db),
    cu: dict = Depends(get_current_user),
):
    """Monthly new customer signups and cumulative total."""
    today = date.today()
    result = []
    total = 0
    for i in range(months - 1, -1, -1):
        m_date = today.replace(day=1) - timedelta(days=i * 30)
        m_year, m_month = m_date.year, m_date.month
        new_cust = db.query(func.count(Customer.id)).filter(
            extract("year", Customer.created_at) == m_year,
            extract("month", Customer.created_at) == m_month,
        ).scalar() or 0
        total += new_cust
        result.append({"month": m_date.strftime("%Y-%m"), "new_customers": new_cust, "total_customers": total})
    return result


@router.get("/appointments/by-practitioner")
def appointments_by_practitioner(
    from_date: str = Query(...),
    to_date: str = Query(...),
    db: Session = Depends(get_db),
    cu: dict = Depends(get_current_user),
):
    fd = date.fromisoformat(from_date)
    td = date.fromisoformat(to_date)
    results = (
        db.query(
            Practitioner.name,
            func.count(Appointment.id).label("total"),
            func.sum(func.cast(Appointment.status == "completed", Integer)).label("completed"),
            func.sum(func.cast(Appointment.status == "no_show", Integer)).label("no_show"),
        )
        .join(Appointment, Practitioner.id == Appointment.practitioner_id)
        .filter(
            func.date(Appointment.scheduled_at) >= fd,
            func.date(Appointment.scheduled_at) <= td,
        )
        .group_by(Practitioner.name)
        .all()
    )
    return [
        {"practitioner_name": r[0], "total": r[1], "completed": r[2] or 0, "no_show": r[3] or 0}
        for r in results
    ]