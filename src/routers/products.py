"""
Products + CSV import (Task 08).
"""
import csv
import io
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Response
from sqlalchemy.orm import Session

from core.deps import get_db, get_current_user
from models import Product, ProductTransaction
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/products", tags=["products"])


class ProductCreate(BaseModel):
    name: str; description: Optional[str] = None
    category: str; sku: str; supplier: Optional[str] = None
    cost_price: float = Query(ge=0); retail_price: float = Query(ge=0)
    stock_level: int = Query(ge=0); reorder_threshold: int = Query(ge=0, default=10)
    is_active: bool = True


class ProductUpdate(BaseModel):
    name: Optional[str] = None; description: Optional[str] = None
    category: Optional[str] = None; sku: Optional[str] = None; supplier: Optional[str] = None
    cost_price: Optional[float] = None; retail_price: Optional[float] = None
    stock_level: Optional[int] = None; reorder_threshold: Optional[int] = None
    is_active: Optional[bool] = None


class ProductResponse(BaseModel):
    id: str; name: str; description: Optional[str]; category: str; sku: str
    supplier: Optional[str]; cost_price: float; retail_price: float
    stock_level: int; reorder_threshold: int; is_active: bool
    created_at: str; updated_at: str


@router.post("/", response_model=ProductResponse, status_code=201)
def create_product(data: ProductCreate, db: Session = Depends(get_db), cu: dict = Depends(get_current_user)):
    existing = db.query(Product).filter(Product.sku == data.sku).first()
    if existing:
        raise HTTPException(400, f"SKU {data.sku} already exists")
    now = datetime.utcnow()
    p = Product(id=str(uuid.uuid4()), name=data.name, description=data.description,
                category=data.category, sku=data.sku, supplier=data.supplier,
                cost_price=data.cost_price, retail_price=data.retail_price,
                stock_level=data.stock_level, reorder_threshold=data.reorder_threshold,
                is_active=data.is_active, created_at=now, updated_at=now)
    db.add(p); db.commit(); db.refresh(p)
    return _prod_response(p)


@router.get("/")
def list_products(category: str | None = None, is_active: bool | None = None,
                  page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
                  db: Session = Depends(get_db), cu: dict = Depends(get_current_user)):
    q = db.query(Product)
    if category: q = q.filter(Product.category == category)
    if is_active is not None: q = q.filter(Product.is_active == is_active)
    total = q.count()
    items = q.order_by(Product.name).offset((page-1)*page_size).limit(page_size).all()
    return {"items": [_prod_response(p) for p in items], "total": total, "page": page, "page_size": page_size}


@router.get("/{prod_id}", response_model=ProductResponse)
def get_product(prod_id: str, db: Session = Depends(get_db), cu: dict = Depends(get_current_user)):
    p = db.query(Product).filter(Product.id == prod_id).first()
    if not p: raise HTTPException(404, "Product not found")
    return _prod_response(p)


@router.patch("/{prod_id}", response_model=ProductResponse)
def update_product(prod_id: str, data: ProductUpdate, db: Session = Depends(get_db), cu: dict = Depends(get_current_user)):
    p = db.query(Product).filter(Product.id == prod_id).first()
    if not p: raise HTTPException(404, "Product not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        if hasattr(p, field): setattr(p, field, value)
    p.updated_at = datetime.utcnow()
    db.commit(); db.refresh(p)
    return _prod_response(p)


@router.post("/import/csv", status_code=201)
async def import_products_csv(file: UploadFile = File(...), db: Session = Depends(get_db), cu: dict = Depends(get_current_user)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Must be a .csv file")
    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file")
    reader = csv.DictReader(io.StringIO(content.decode()))
    created, updated, errors = 0, 0, []
    required = {"name", "category", "sku", "unit_cost", "unit_price"}
    for row_num, row in enumerate(reader, start=2):
        if not required.issubset(row.keys()):
            errors.append(f"Row {row_num}: missing required columns {required - set(row.keys())}")
            continue
        try:
            sku = row["sku"].strip()
            cost = float(row["unit_cost"]); price = float(row["unit_price"])
            qty = int(row.get("stock_level", row.get("quantity_in_stock", 0)))
            existing = db.query(Product).filter(Product.sku == sku).first()
            now = datetime.utcnow()
            if existing:
                existing.name = row["name"].strip()
                existing.category = row["category"].strip()
                existing.cost_price = cost; existing.retail_price = price
                existing.stock_level = qty
                if "supplier" in row and row["supplier"].strip():
                    existing.supplier = row["supplier"].strip()
                existing.updated_at = now
                updated += 1
            else:
                p = Product(
                    id=str(uuid.uuid4()), name=row["name"].strip(), category=row["category"].strip(),
                    sku=sku, supplier=row.get("supplier", "").strip() or None,
                    cost_price=cost, retail_price=price,
                    stock_level=qty, reorder_threshold=int(row.get("reorder_threshold", 10)),
                    is_active=True, created_at=now, updated_at=now,
                )
                db.add(p); created += 1
        except Exception as e:
            errors.append(f"Row {row_num}: {e}")
    db.commit()
    return {"created": created, "updated": updated, "errors": errors[:50]}


@router.post("/{prod_id}/transactions")
def log_transaction(prod_id: str, quantity_change: int = Query(...),
                    transaction_type: str = Query(...), order_id: str | None = None,
                    db: Session = Depends(get_db), cu: dict = Depends(get_current_user)):
    """Record stock movement (sale, return, adjustment, restock)."""
    p = db.query(Product).filter(Product.id == prod_id).first()
    if not p: raise HTTPException(404, "Product not found")
    if p.stock_level + quantity_change < 0:
        raise HTTPException(400, f"Insufficient stock: have {p.stock_level}, trying to remove {abs(quantity_change)}")
    p.stock_level += quantity_change
    tx = ProductTransaction(
        id=str(uuid.uuid4()), product_id=prod_id, order_id=order_id,
        quantity=quantity_change, transaction_type=transaction_type,
        created_at=datetime.utcnow(),
    )
    db.add(tx); db.commit(); db.refresh(p)
    return {"product_id": prod_id, "new_stock": p.stock_level, "transaction_id": str(tx.id)}


def _prod_response(p: Product) -> dict:
    return {
        "id": str(p.id), "name": p.name, "description": p.description,
        "category": p.category, "sku": p.sku, "supplier": p.supplier,
        "cost_price": float(p.cost_price or 0), "retail_price": float(p.retail_price or 0),
        "stock_level": p.stock_level, "reorder_threshold": p.reorder_threshold,
        "is_active": p.is_active,
        "created_at": p.created_at.isoformat() if p.created_at else "",
        "updated_at": p.updated_at.isoformat() if p.updated_at else "",
    }