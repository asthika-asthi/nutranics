#!/usr/bin/env python3
"""
Seed script — populates the database with realistic demo data.
Run with: python -m scripts.seed_data
"""
import sys, uuid
sys.path.insert(0, "src")

from datetime import datetime, date, time, timedelta
from sqlalchemy.orm import Session

from core.deps import SessionLocal
from models import (
    User, Practitioner, Customer, CustomerAssignment,
    Plan, PlanItem, Subscription, PlanSlot,
    Room, PractitionerAvailability,
    Product,
)
from core.security import hash_password

ITEM_TYPES = ["iv_drip", "supplement", "food_guidance", "follow_up_test", "check_in_call", "consultation", "other"]
FREQUENCIES = ["monthly", "weekly", "per_cycle"]

def create_practitioner(db: Session, name: str, email: str, specialisms: list[str] | None = None) -> Practitioner:
    p = Practitioner(
        id=str(uuid.uuid4()), name=name, email=email,
        specialisms=specialisms or [],
        is_active=True, created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    db.add(p)
    return p

def create_user(db: Session, email: str, role: str, practitioner_id: str | None = None) -> User:
    u = User(
        id=str(uuid.uuid4()), email=email, role=role,
        practitioner_id=practitioner_id,
        password_hash=hash_password("Demo1234!"),
        is_active=True,
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    db.add(u)
    return u

def create_plan(db: Session, name: str, monthly_price: float, contract: str,
                items: list[dict], is_template: bool = True) -> Plan:
    p = Plan(
        id=str(uuid.uuid4()), name=name, description=f"Auto-generated plan: {name}",
        monthly_price=monthly_price, contract_length=contract,
        is_template=is_template, is_active=True,
        created_by=None, created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    db.add(p)
    db.flush()
    for i, item in enumerate(items):
        pi = PlanItem(
            id=str(uuid.uuid4()), plan_id=p.id,
            item_type=item["type"], item_name=item["name"],
            quantity_per_cycle=item.get("qty", 1), frequency=item.get("freq", "monthly"),
            notes=item.get("notes", ""),
        )
        db.add(pi)
    return p

def create_customer(db: Session, name: str, email: str, phone: str, practitioner_id: str) -> Customer:
    c = Customer(
        id=str(uuid.uuid4()), practitioner_id=practitioner_id, name=name,
        email=email, phone=phone,
        preferred_contact="email",
        is_active=True, created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    db.add(c)
    return c

def seed(db: Session):
    print("Seeding database...")

    # Practitioners
    dr_chen = create_practitioner(db, "Dr Sarah Chen", "s.chen@wellnessclinic.com", ["IV therapy", "Nutritional medicine"])
    dr_patel = create_practitioner(db, "Dr Raj Patel", "r.patel@wellnessclinic.com", ["Hormone optimisation", "IV therapy"])
    dr_kim = create_practitioner(db, "Dr Ji-Soo Kim", "j.kim@wellnessclinic.com", ["Naturopathic medicine", "Detox"])
    db.flush()
    print(f"  Practitioners: {dr_chen.name}, {dr_patel.name}, {dr_kim.name}")

    # Availability — Mon-Fri 9-17 for all
    for prac in [dr_chen, dr_patel, dr_kim]:
        for dow in range(5):  # Mon=0 … Fri=4
            # Single 9-17 window per day (model unique constraint: one row per practitioner per day)
            a = PractitionerAvailability(
                id=str(uuid.uuid4()), practitioner_id=prac.id,
                day_of_week=dow, is_available=True,
                start_time=time(9, 0), end_time=time(17, 0),
                created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
            )
            db.add(a)
    print("  Availability windows added")

    # Rooms
    rooms = []
    for name in ["Room A — IV Suite", "Room B — Consultation", "Room C — Therapy Room"]:
        r = Room(id=str(uuid.uuid4()), name=name, is_active=True)
        db.add(r)
        rooms.append(r)
    print(f"  Rooms: {[r.name for r in rooms]}")

    # Users
    owner = create_user(db, "admin@wellnessclinic.com", "owner", None)
    practioner_user = create_user(db, "s.chen@wellnessclinic.com", "practitioner", dr_chen.id)
    db.flush()
    print(f"  Users: {owner.email}, {practioner_user.email} (password: Demo1234!)")

    # Plans
    plans = {
        "essential": create_plan(db, "Essential Wellness", 149.00, "12 weeks", [
            {"type": "iv_drip", "name": "Energy Revive IV", "qty": 1, "freq": "monthly"},
            {"type": "supplement", "name": "Basic Supplement Pack", "qty": 1, "freq": "monthly"},
            {"type": "check_in_call", "name": "Monthly Check-in Call", "qty": 1, "freq": "monthly"},
        ]),
        "comprehensive": create_plan(db, "Comprehensive Health", 299.00, "12 weeks", [
            {"type": "iv_drip", "name": "Myers Cocktail IV", "qty": 2, "freq": "monthly"},
            {"type": "supplement", "name": "Advanced Supplement Protocol", "qty": 1, "freq": "monthly"},
            {"type": "follow_up_test", "name": "Micronutrient Panel Retest", "qty": 1, "freq": "per_cycle"},
            {"type": "check_in_call", "name": "Bi-weekly Check-in", "qty": 2, "freq": "monthly"},
        ]),
        "executive": create_plan(db, "Executive Health", 499.00, "12 weeks", [
            {"type": "iv_drip", "name": "NAD+ Cellular Restoration", "qty": 2, "freq": "monthly"},
            {"type": "iv_drip", "name": "Detox IV", "qty": 1, "freq": "monthly"},
            {"type": "consultation", "name": "45-min Consultation", "qty": 1, "freq": "monthly"},
            {"type": "supplement", "name": "Premium Supplement Stack", "qty": 1, "freq": "monthly"},
            {"type": "follow_up_test", "name": "Full Biomarker Panel", "qty": 1, "freq": "per_cycle"},
        ]),
    }
    db.flush()
    print(f"  Plans: {list(plans.keys())}")

    # Customers
    customers_data = [
        ("Emma Thompson", "emma.thompson@email.com", "07700011111"),
        ("James O'Connor", "james.oconnor@email.com", "07700022222"),
        ("Sophia Ahmed", "sophia.ahmed@email.com", "07700033333"),
        ("Marcus Webb", "marcus.webb@email.com", "07700044444"),
        ("Laura Fitzpatrick", "laura.fitz@email.com", "07700055555"),
        ("Oliver Nakamura", "oliver.nakamura@email.com", "07700066666"),
    ]
    customers = []
    for name, email, phone in customers_data:
        c = create_customer(db, name, email, phone, dr_chen.id)
        # Assign to all practitioners
        for prac in [dr_chen, dr_patel, dr_kim]:
            a = CustomerAssignment(
                id=str(uuid.uuid4()), customer_id=c.id, practitioner_id=prac.id,
                can_view=True, notes="primary",
                assigned_at=datetime.utcnow(),
            )
            db.add(a)
        customers.append(c)
    db.flush()
    print(f"  Customers: {len(customers)} created")

    # Subscriptions — first 4 customers on plans
    for i, (plan_key, plan) in enumerate(plans.items()):
        if i >= len(customers):
            break
        cust = customers[i]
        start = date.today() - timedelta(days=30 * (i + 1))
        next_bill = start + timedelta(days=30)
        sub = Subscription(
            id=str(uuid.uuid4()), customer_id=cust.id, plan_id=plan.id,
            status="active", start_date=start, billing_day=1,
            next_billing_date=next_bill, months_billed=i + 1,
            current_cycle_start=start, current_cycle_end=next_bill,
            total_billed=plan.monthly_price * (i + 1), total_paid=plan.monthly_price * (i + 1),
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        db.add(sub)
        db.flush()
        # Schedule 3 plan slots
        slot_date = start + timedelta(days=7)
        plan_items = db.query(PlanItem).filter(PlanItem.plan_id == plan.id).limit(3).all()
        for pi in plan_items:
            window_end = slot_date + timedelta(days=5)
            slot = PlanSlot(
                id=str(uuid.uuid4()), subscription_id=sub.id, plan_item_id=pi.id,
                item_type=pi.item_type, item_name=pi.item_name,
                suggested_date=slot_date, booking_window_start=slot_date,
                booking_window_end=window_end, status="pending",
                created_at=datetime.utcnow(),
            )
            db.add(slot)
            slot_date += timedelta(days=14)
        print(f"  Subscription: {cust.name} -> {plan.name}")
    db.flush()

    # Products
    products_data = [
        ("Vitamin D3 5000 IU", "Supplements", "VIT-D3-5K", 8.50, 15.99, 200),
        ("B-Complex Injection Kit", "IV Supplies", "B-COMPLEX-KIT", 22.00, 39.99, 45),
        ("NAD+ 500mg", "IV Supplies", "NAD-500", 45.00, 89.99, 30),
        ("Magnesium Glycinate", "Supplements", "MAG-GLY-60", 12.00, 24.99, 120),
        ("Myers Cocktail 10ml", "IV Supplies", "MYERS-10", 18.00, 34.99, 60),
        ("Glutathione 600mg", "IV Supplies", "GSH-600", 15.00, 29.99, 80),
        ("Zinc Picolinate 30mg", "Supplements", "ZN-PIC-30", 6.50, 13.99, 150),
        ("Omega-3 Fish Oil", "Supplements", "OM3-60CAP", 10.00, 19.99, 90),
        ("Consultation Deposit", "Services", "CONSULT-DEP", 50.00, 50.00, 999),
        ("Blood Test Panel", "Lab", "BLOOD-PANEL", 35.00, 79.99, 25),
    ]
    for name, cat, sku, cost, price, qty in products_data:
        p = Product(
            id=str(uuid.uuid4()), name=name, category=cat, sku=sku,
            cost_price=cost, retail_price=price,
            stock_level=qty, reorder_threshold=20,
            is_active=True, created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        db.add(p)
    print(f"  Products: {len(products_data)} created")

    db.commit()
    print("\n✅ Seed complete!")
    print(f"   Owner login: admin@wellnessclinic.com / Demo1234!")
    print(f"   Practitioner login: s.chen@wellnessclinic.com / Demo1234!")
    print(f"   All customer passwords: Demo1234!")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()