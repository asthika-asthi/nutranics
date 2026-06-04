import uuid
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.deps import get_db, get_current_user
from core.access import user_can_view_customer, user_can_edit_customer
from models import Plan, PlanItem, PlanTemplate, Customer, User
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/plans", tags=["treatment plans"])


# ─── Schemas ───────────────────────────────────────────────────────────────────

class PlanTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    default_duration_days: int = 30
    default_sessions: int = 6
    items: list["PlanItemTemplateCreate"] = []


class PlanItemTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    order_index: int = 0
    duration_days: Optional[int] = None
    session_number: Optional[int] = None


class PlanTemplateResponse(BaseModel):
    id: str; name: str; description: Optional[str]; default_duration_days: int
    default_sessions: int; created_at: str


class PlanCreate(BaseModel):
    customer_id: str
    name: str
    description: Optional[str] = None
    template_id: Optional[str] = None
    start_date: str  # ISO date
    status: str = "active"  # active, paused, completed, cancelled
    notes: Optional[str] = None


class PlanItemCreate(BaseModel):
    plan_id: str
    name: str
    description: Optional[str] = None
    order_index: int = 0
    duration_days: Optional[int] = None
    session_number: Optional[int] = None
    status: str = "pending"  # pending, in_progress, completed, skipped


class PlanResponse(BaseModel):
    id: str; customer_id: str; name: str; description: Optional[str]
    template_id: Optional[str]; start_date: str; end_date: Optional[str]
    status: str; notes: Optional[str]; created_at: str; updated_at: str


class PlanItemResponse(BaseModel):
    id: str; plan_id: str; name: str; description: Optional[str]
    order_index: int; duration_days: Optional[int]; session_number: Optional[int]
    status: str; created_at: str

    class Config:
        from_attributes = True


def _d(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


# ─── Plan Templates ───────────────────────────────────────────────────────────

@router.post("/templates", status_code=201)
def create_template(data: PlanTemplateCreate, db: Session = Depends(get_db), cu: dict = Depends(get_current_user)):
    now = datetime.utcnow()
    t = PlanTemplate(
        id=str(uuid.uuid4()), name=data.name, description=data.description,
        default_duration_days=data.default_duration_days, default_sessions=data.default_sessions,
        created_at=now, updated_at=now,
    )
    db.add(t)
    for i, item in enumerate(data.items):
        pi = PlanItem(
            id=str(uuid.uuid4()), plan_id=None, template_id=t.id, name=item.name,
            description=item.description, order_index=item.order_index or i,
            duration_days=item.duration_days, session_number=item.session_number,
            status="pending", created_at=now,
        )
        db.add(pi)
    db.commit()
    return PlanTemplateResponse(
        id=str(t.id), name=t.name, description=t.description,
        default_duration_days=t.default_duration_days, default_sessions=t.default_sessions,
        created_at=t.created_at.isoformat() if t.created_at else "",
    )


@router.get("/templates")
def list_templates(db: Session = Depends(get_db), cu: dict = Depends(get_current_user)):
    templates = db.query(PlanTemplate).order_by(PlanTemplate.name).all()
    return [PlanTemplateResponse(
        id=str(t.id), name=t.name, description=t.description,
        default_duration_days=t.default_duration_days, default_sessions=t.default_sessions,
        created_at=t.created_at.isoformat() if t.created_at else "",
    ) for t in templates]


# ─── Plans ─────────────────────────────────────────────────────────────────────

@router.post("/", response_model=PlanResponse, status_code=201)
def create_plan(data: PlanCreate, db: Session = Depends(get_db), cu: dict = Depends(get_current_user)):
    if not user_can_edit_customer(cu, data.customer_id, db):
        raise HTTPException(403, "Not authorised")
    now = datetime.utcnow()
    start = _d(data.start_date)
    end = start + timedelta(days=30) if start else None
    plan = Plan(
        id=str(uuid.uuid4()), customer_id=data.customer_id, name=data.name,
        description=data.description, template_id=data.template_id,
        start_date=start, end_date=end, status=data.status, notes=data.notes,
        created_at=now, updated_at=now,
    )
    db.add(plan)
    # If from template, copy template items
    if data.template_id:
        template_items = db.query(PlanItem).filter(
            PlanItem.template_id == data.template_id, PlanItem.plan_id == None
        ).order_by(PlanItem.order_index).all()
        for ti in template_items:
            item = PlanItem(
                id=str(uuid.uuid4()), plan_id=plan.id, template_id=data.template_id,
                name=ti.name, description=ti.description, order_index=ti.order_index,
                duration_days=ti.duration_days, session_number=ti.session_number,
                status="pending", created_at=now,
            )
            db.add(item)
    db.commit()
    db.refresh(plan)
    return PlanResponse(
        id=str(plan.id), customer_id=str(plan.customer_id), name=plan.name,
        description=plan.description, template_id=plan.template_id,
        start_date=plan.start_date.isoformat() if plan.start_date else "",
        end_date=plan.end_date.isoformat() if plan.end_date else None,
        status=plan.status, notes=plan.notes,
        created_at=plan.created_at.isoformat() if plan.created_at else "",
        updated_at=plan.updated_at.isoformat() if plan.updated_at else "",
    )


@router.get("/customers/{customer_id}")
def list_plans(customer_id: str, status: str | None = None, db: Session = Depends(get_db), cu: dict = Depends(get_current_user)):
    if not user_can_view_customer(cu, customer_id, db):
        raise HTTPException(403, "Not authorised")
    q = db.query(Plan).filter(Plan.customer_id == customer_id)
    if status:
        q = q.filter(Plan.status == status)
    plans = q.order_by(Plan.start_date.desc()).all()
    return [PlanResponse(
        id=str(p.id), customer_id=str(p.customer_id), name=p.name, description=p.description,
        template_id=p.template_id,
        start_date=p.start_date.isoformat() if p.start_date else "",
        end_date=p.end_date.isoformat() if p.end_date else None,
        status=p.status, notes=p.notes,
        created_at=p.created_at.isoformat() if p.created_at else "",
        updated_at=p.updated_at.isoformat() if p.updated_at else "",
    ) for p in plans]


@router.get("/{plan_id}", response_model=PlanResponse)
def get_plan(plan_id: str, db: Session = Depends(get_db), cu: dict = Depends(get_current_user)):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "Plan not found")
    if not user_can_view_customer(cu, plan.customer_id, db):
        raise HTTPException(403, "Not authorised")
    return PlanResponse(
        id=str(plan.id), customer_id=str(plan.customer_id), name=plan.name,
        description=plan.description, template_id=plan.template_id,
        start_date=plan.start_date.isoformat() if plan.start_date else "",
        end_date=plan.end_date.isoformat() if plan.end_date else None,
        status=plan.status, notes=plan.notes,
        created_at=plan.created_at.isoformat() if plan.created_at else "",
        updated_at=plan.updated_at.isoformat() if plan.updated_at else "",
    )


@router.patch("/{plan_id}", response_model=PlanResponse)
def update_plan(plan_id: str, status: str | None = None, notes: str | None = None,
                db: Session = Depends(get_db), cu: dict = Depends(get_current_user)):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "Plan not found")
    if not user_can_edit_customer(cu, plan.customer_id, db):
        raise HTTPException(403, "Not authorised")
    if status:
        plan.status = status
    if notes is not None:
        plan.notes = notes
    plan.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(plan)
    return PlanResponse(
        id=str(plan.id), customer_id=str(plan.customer_id), name=plan.name,
        description=plan.description, template_id=plan.template_id,
        start_date=plan.start_date.isoformat() if plan.start_date else "",
        end_date=plan.end_date.isoformat() if plan.end_date else None,
        status=plan.status, notes=plan.notes,
        created_at=plan.created_at.isoformat() if plan.created_at else "",
        updated_at=plan.updated_at.isoformat() if plan.updated_at else "",
    )


# ─── Plan Items ────────────────────────────────────────────────────────────────

@router.post("/items", response_model=PlanItemResponse, status_code=201)
def add_plan_item(data: PlanItemCreate, db: Session = Depends(get_db), cu: dict = Depends(get_current_user)):
    plan = db.query(Plan).filter(Plan.id == data.plan_id).first()
    if not plan:
        raise HTTPException(404, "Plan not found")
    if not user_can_edit_customer(cu, plan.customer_id, db):
        raise HTTPException(403, "Not authorised")
    now = datetime.utcnow()
    item = PlanItem(
        id=str(uuid.uuid4()), plan_id=data.plan_id, template_id=None,
        name=data.name, description=data.description, order_index=data.order_index,
        duration_days=data.duration_days, session_number=data.session_number,
        status=data.status, created_at=now,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return PlanItemResponse(
        id=str(item.id), plan_id=str(item.plan_id), name=item.name,
        description=item.description, order_index=item.order_index,
        duration_days=item.duration_days, session_number=item.session_number,
        status=item.status, created_at=item.created_at.isoformat() if item.created_at else "",
    )


@router.get("/{plan_id}/items")
def list_plan_items(plan_id: str, db: Session = Depends(get_db), cu: dict = Depends(get_current_user)):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "Plan not found")
    if not user_can_view_customer(cu, plan.customer_id, db):
        raise HTTPException(403, "Not authorised")
    items = db.query(PlanItem).filter(PlanItem.plan_id == plan_id).order_by(PlanItem.order_index).all()
    return [PlanItemResponse(
        id=str(i.id), plan_id=str(i.plan_id), name=i.name, description=i.description,
        order_index=i.order_index, duration_days=i.duration_days,
        session_number=i.session_number, status=i.status,
        created_at=i.created_at.isoformat() if i.created_at else "",
    ) for i in items]


@router.patch("/items/{item_id}", response_model=PlanItemResponse)
def update_plan_item(item_id: str, status: str | None = None, db: Session = Depends(get_db), cu: dict = Depends(get_current_user)):
    item = db.query(PlanItem).filter(PlanItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "Plan item not found")
    plan = db.query(Plan).filter(Plan.id == item.plan_id).first()
    if not plan or not user_can_edit_customer(cu, plan.customer_id, db):
        raise HTTPException(403, "Not authorised")
    if status:
        item.status = status
    db.commit()
    db.refresh(item)
    return PlanItemResponse(
        id=str(item.id), plan_id=str(item.plan_id), name=item.name,
        description=item.description, order_index=item.order_index,
        duration_days=item.duration_days, session_number=item.session_number,
        status=item.status, created_at=item.created_at.isoformat() if item.created_at else "",
    )