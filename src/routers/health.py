import uuid
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func

from core.deps import get_db, get_current_user
from core.access import user_can_view_customer
from models import TestResult, TestMarker, Recommendation, Customer, User, Order
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/health", tags=["health data"])


# ─── Schemas ───────────────────────────────────────────────────────────────────

class MarkerCreate(BaseModel):
    marker_name: str
    value: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    flag: str = "normal"  # normal, low, high, critical
    practitioner_notes: Optional[str] = None


class MarkerResponse(BaseModel):
    id: str
    test_result_id: str
    marker_name: str
    value: Optional[float]
    value_text: Optional[str]
    unit: Optional[str]
    reference_low: Optional[float]
    reference_high: Optional[float]
    is_out_of_range: bool
    flag: str
    practitioner_notes: Optional[str]
    created_at: str


class TestResultCreate(BaseModel):
    customer_id: str
    test_type: str  # "Micronutrient Panel", "Vitamin D", "Thyroid", etc.
    date_taken: str  # ISO date
    date_received: Optional[str] = None
    pdf_url: Optional[str] = None
    practitioner_notes: Optional[str] = None
    status: str = "pending"  # pending, reviewed, actioned
    markers: list[MarkerCreate] = []


class TestResultUpdate(BaseModel):
    date_received: Optional[str] = None
    pdf_url: Optional[str] = None
    practitioner_notes: Optional[str] = None
    status: Optional[str] = None


class TestResultResponse(BaseModel):
    id: str
    customer_id: str
    test_type: str
    date_taken: str
    date_received: Optional[str]
    pdf_url: Optional[str]
    practitioner_notes: Optional[str]
    status: str
    marker_count: int = 0
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class RecommendationCreate(BaseModel):
    customer_id: str
    test_marker_id: Optional[str] = None
    recommendation_text: str
    status: str = "pending"  # pending, accepted, declined, completed
    linked_order_id: Optional[str] = None


class RecommendationResponse(BaseModel):
    id: str
    customer_id: str
    test_marker_id: Optional[str]
    recommendation_text: str
    status: str
    linked_order_id: Optional[str]
    created_by: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


def _parse_date(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


# ─── Test Results ─────────────────────────────────────────────────────────────

@router.post("/test-results", response_model=TestResultResponse, status_code=201)
def create_test_result(
    data: TestResultCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Upload/create a test result with markers."""
    if not user_can_view_customer(current_user, data.customer_id, db):
        raise HTTPException(status_code=403, detail="Not authorised")

    now = datetime.utcnow()
    date_taken = _parse_date(data.date_taken)
    date_received = _parse_date(data.date_received)

    result = TestResult(
        id=str(uuid.uuid4()),
        customer_id=data.customer_id,
        test_type=data.test_type,
        date_taken=date_taken,
        date_received=date_received,
        pdf_url=data.pdf_url,
        practitioner_notes=data.practitioner_notes,
        status=data.status,
        created_at=now,
        updated_at=now,
    )
    db.add(result)

    # Create markers
    for m in data.markers:
        # Auto-flag out of range
        is_out_of = False
        if m.reference_low is not None and m.value is not None and m.value < m.reference_low:
            is_out_of = True
        elif m.reference_high is not None and m.value is not None and m.value > m.reference_high:
            is_out_of = True

        marker = TestMarker(
            id=str(uuid.uuid4()),
            test_result_id=result.id,
            marker_name=m.marker_name,
            value=m.value,
            value_text=m.value_text,
            unit=m.unit,
            reference_low=m.reference_low,
            reference_high=m.reference_high,
            is_out_of_range=is_out_of,
            flag=m.flag,
            practitioner_notes=m.practitioner_notes,
            created_at=now,
        )
        db.add(marker)

    db.commit()
    db.refresh(result)

    marker_count = db.query(TestMarker).filter(TestMarker.test_result_id == result.id).count()

    return TestResultResponse(
        id=str(result.id),
        customer_id=str(result.customer_id),
        test_type=result.test_type,
        date_taken=result.date_taken.isoformat() if result.date_taken else "",
        date_received=result.date_received.isoformat() if result.date_received else None,
        pdf_url=result.pdf_url,
        practitioner_notes=result.practitioner_notes,
        status=result.status,
        marker_count=marker_count,
        created_at=result.created_at.isoformat() if result.created_at else "",
        updated_at=result.updated_at.isoformat() if result.updated_at else "",
    )


@router.get("/customers/{customer_id}/test-results")
def list_test_results(
    customer_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List test results for a customer."""
    if not user_can_view_customer(current_user, customer_id, db):
        raise HTTPException(status_code=403, detail="Not authorised")

    q = db.query(TestResult).filter(TestResult.customer_id == customer_id)
    if status:
        q = q.filter(TestResult.status == status)

    total = q.count()
    results = q.order_by(TestResult.date_taken.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for r in results:
        marker_count = db.query(func.count(TestMarker.id)).filter(TestMarker.test_result_id == r.id).scalar()
        items.append(TestResultResponse(
            id=str(r.id),
            customer_id=str(r.customer_id),
            test_type=r.test_type,
            date_taken=r.date_taken.isoformat() if r.date_taken else "",
            date_received=r.date_received.isoformat() if r.date_received else None,
            pdf_url=r.pdf_url,
            practitioner_notes=r.practitioner_notes,
            status=r.status,
            marker_count=marker_count or 0,
            created_at=r.created_at.isoformat() if r.created_at else "",
            updated_at=r.updated_at.isoformat() if r.updated_at else "",
        ))

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/test-results/{result_id}")
def get_test_result(
    result_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get a single test result with all markers."""
    result = db.query(TestResult).filter(TestResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Test result not found")

    if not user_can_view_customer(current_user, result.customer_id, db):
        raise HTTPException(status_code=403, detail="Not authorised")

    markers = db.query(TestMarker).filter(TestMarker.test_result_id == result_id).all()

    return {
        "id": str(result.id),
        "customer_id": str(result.customer_id),
        "test_type": result.test_type,
        "date_taken": result.date_taken.isoformat() if result.date_taken else "",
        "date_received": result.date_received.isoformat() if result.date_received else None,
        "pdf_url": result.pdf_url,
        "practitioner_notes": result.practitioner_notes,
        "status": result.status,
        "created_at": result.created_at.isoformat() if result.created_at else "",
        "updated_at": result.updated_at.isoformat() if result.updated_at else "",
        "markers": [
            MarkerResponse(
                id=str(m.id),
                test_result_id=str(m.test_result_id),
                marker_name=m.marker_name,
                value=float(m.value) if m.value else None,
                value_text=m.value_text,
                unit=m.unit,
                reference_low=float(m.reference_low) if m.reference_low else None,
                reference_high=float(m.reference_high) if m.reference_high else None,
                is_out_of_range=m.is_out_of_range,
                flag=m.flag,
                practitioner_notes=m.practitioner_notes,
                created_at=m.created_at.isoformat() if m.created_at else "",
            )
            for m in markers
        ],
    }


@router.patch("/test-results/{result_id}", response_model=TestResultResponse)
def update_test_result(
    result_id: str,
    data: TestResultUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update status/notes of a test result."""
    result = db.query(TestResult).filter(TestResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Test result not found")

    if not user_can_view_customer(current_user, result.customer_id, db):
        raise HTTPException(status_code=403, detail="Not authorised")

    for field, value in data.model_dump(exclude_unset=True).items():
        if field in ("date_received",) and value:
            value = _parse_date(value)
        if hasattr(result, field):
            setattr(result, field, value)
    result.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(result)

    marker_count = db.query(func.count(TestMarker.id)).filter(TestMarker.test_result_id == result.id).scalar()

    return TestResultResponse(
        id=str(result.id),
        customer_id=str(result.customer_id),
        test_type=result.test_type,
        date_taken=result.date_taken.isoformat() if result.date_taken else "",
        date_received=result.date_received.isoformat() if result.date_received else None,
        pdf_url=result.pdf_url,
        practitioner_notes=result.practitioner_notes,
        status=result.status,
        marker_count=marker_count or 0,
        created_at=result.created_at.isoformat() if result.created_at else "",
        updated_at=result.updated_at.isoformat() if result.updated_at else "",
    )


# ─── Recommendations ──────────────────────────────────────────────────────────

@router.post("/recommendations", response_model=RecommendationResponse, status_code=201)
def create_recommendation(
    data: RecommendationCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create a supplement/recommendation from a test marker."""
    if not user_can_view_customer(current_user, data.customer_id, db):
        raise HTTPException(status_code=403, detail="Not authorised")

    now = datetime.utcnow()
    rec = Recommendation(
        id=str(uuid.uuid4()),
        customer_id=data.customer_id,
        test_marker_id=data.test_marker_id,
        recommendation_text=data.recommendation_text,
        status=data.status,
        linked_order_id=data.linked_order_id,
        created_by=current_user.get("id"),
        created_at=now,
        updated_at=now,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    return RecommendationResponse(
        id=str(rec.id),
        customer_id=str(rec.customer_id),
        test_marker_id=rec.test_marker_id,
        recommendation_text=rec.recommendation_text,
        status=rec.status,
        linked_order_id=rec.linked_order_id,
        created_by=rec.created_by,
        created_at=rec.created_at.isoformat() if rec.created_at else "",
        updated_at=rec.updated_at.isoformat() if rec.updated_at else "",
    )


@router.get("/customers/{customer_id}/recommendations")
def list_recommendations(
    customer_id: str,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List recommendations for a customer."""
    if not user_can_view_customer(current_user, customer_id, db):
        raise HTTPException(status_code=403, detail="Not authorised")

    q = db.query(Recommendation).filter(Recommendation.customer_id == customer_id)
    if status:
        q = q.filter(Recommendation.status == status)

    recs = q.order_by(Recommendation.created_at.desc()).all()
    return [
        RecommendationResponse(
            id=str(r.id),
            customer_id=str(r.customer_id),
            test_marker_id=r.test_marker_id,
            recommendation_text=r.recommendation_text,
            status=r.status,
            linked_order_id=r.linked_order_id,
            created_by=r.created_by,
            created_at=r.created_at.isoformat() if r.created_at else "",
            updated_at=r.updated_at.isoformat() if r.updated_at else "",
        )
        for r in recs
    ]


@router.patch("/recommendations/{rec_id}/status")
def update_recommendation_status(
    rec_id: str,
    status: str = Query(..., description="New status: pending, accepted, declined, completed"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update status of a recommendation (accepted/declined/completed)."""
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    if not user_can_view_customer(current_user, rec.customer_id, db):
        raise HTTPException(status_code=403, detail="Not authorised")

    valid = ("pending", "accepted", "declined", "completed")
    if status not in valid:
        raise HTTPException(status_code=400, detail=f"status must be one of: {valid}")

    rec.status = status
    rec.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rec)

    return RecommendationResponse(
        id=str(rec.id),
        customer_id=str(rec.customer_id),
        test_marker_id=rec.test_marker_id,
        recommendation_text=rec.recommendation_text,
        status=rec.status,
        linked_order_id=rec.linked_order_id,
        created_by=rec.created_by,
        created_at=rec.created_at.isoformat() if rec.created_at else "",
        updated_at=rec.updated_at.isoformat() if rec.updated_at else "",
    )