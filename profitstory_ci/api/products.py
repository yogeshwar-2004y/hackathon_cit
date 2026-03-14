"""
Product and competitor CRUD. All routes require auth; seller_id from JWT.
"""
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from db.database import get_db, Seller, Product, Competitor
from api.auth import get_current_seller

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ProductCreate(BaseModel):
    product_name: str
    category: str
    platform: str
    platform_id: str
    price: Optional[float] = None
    cost: Optional[float] = None
    monthly_units: int = 40


class ProductUpdate(BaseModel):
    product_name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    cost: Optional[float] = None
    monthly_units: Optional[int] = None


class CompetitorCreate(BaseModel):
    competitor_name: str
    platform: str
    platform_id: str
    notes: Optional[str] = None


class CompetitorUpdate(BaseModel):
    competitor_name: Optional[str] = None
    platform_id: Optional[str] = None
    notes: Optional[str] = None


class ProductOut(BaseModel):
    id: int
    seller_id: int
    product_name: str
    category: str
    platform: str
    platform_id: str
    price: Optional[float]
    cost: Optional[float]
    monthly_units: int
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class CompetitorOut(BaseModel):
    id: int
    product_id: int
    seller_id: int
    competitor_name: str
    platform: str
    platform_id: str
    notes: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


def _product_to_out(p: Product) -> dict:
    competitor_count = len([c for c in (p.competitors or []) if c.is_active]) if hasattr(p, "competitors") else 0
    return {
        "id": p.id,
        "seller_id": p.seller_id,
        "product_name": p.product_name,
        "category": p.category,
        "platform": p.platform,
        "platform_id": p.platform_id,
        "price": p.price,
        "cost": p.cost,
        "monthly_units": p.monthly_units or 40,
        "is_active": p.is_active,
        "created_at": p.created_at.isoformat() if p.created_at else "",
        "updated_at": p.updated_at.isoformat() if p.updated_at else "",
        "competitor_count": competitor_count,
    }


def _competitor_to_out(c: Competitor) -> dict:
    return {
        "id": c.id,
        "product_id": c.product_id,
        "seller_id": c.seller_id,
        "competitor_name": c.competitor_name,
        "platform": c.platform,
        "platform_id": c.platform_id,
        "notes": c.notes,
        "is_active": c.is_active,
        "created_at": c.created_at.isoformat() if c.created_at else "",
        "updated_at": c.updated_at.isoformat() if c.updated_at else "",
    }


def _get_product_or_403(db: Session, product_id: int, seller_id: int) -> Product:
    product = db.query(Product).filter(Product.id == product_id, Product.is_active == True).first()
    if not product or product.seller_id != seller_id:
        raise HTTPException(status_code=403, detail="Product not found or access denied")
    return product


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------
@router.post("/products", response_model=dict)
def create_product(
    body: ProductCreate,
    db: Session = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
):
    product = Product(
        seller_id=seller.id,
        product_name=body.product_name.strip(),
        category=body.category.strip(),
        platform=body.platform.strip().lower(),
        platform_id=body.platform_id.strip(),
        price=body.price,
        cost=body.cost,
        monthly_units=body.monthly_units if body.monthly_units is not None else 40,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return _product_to_out(product)


@router.get("/products", response_model=List[dict])
def list_products(
    db: Session = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
):
    products = db.query(Product).options(joinedload(Product.competitors)).filter(Product.seller_id == seller.id, Product.is_active == True).order_by(Product.updated_at.desc()).all()
    return [_product_to_out(p) for p in products]


@router.get("/products/{product_id}", response_model=dict)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
):
    product = _get_product_or_403(db, product_id, seller.id)
    out = _product_to_out(product)
    out["competitors"] = [_competitor_to_out(c) for c in product.competitors if c.is_active]
    return out


@router.patch("/products/{product_id}", response_model=dict)
def update_product(
    product_id: int,
    body: ProductUpdate,
    db: Session = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
):
    product = _get_product_or_403(db, product_id, seller.id)
    if body.product_name is not None:
        product.product_name = body.product_name.strip()
    if body.category is not None:
        product.category = body.category.strip()
    if body.price is not None:
        product.price = body.price
    if body.cost is not None:
        product.cost = body.cost
    if body.monthly_units is not None:
        product.monthly_units = body.monthly_units
    db.commit()
    db.refresh(product)
    return _product_to_out(product)


@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
):
    product = _get_product_or_403(db, product_id, seller.id)
    product.is_active = False
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Competitors
# ---------------------------------------------------------------------------
@router.post("/products/{product_id}/competitors", response_model=dict)
def add_competitor(
    product_id: int,
    body: CompetitorCreate,
    db: Session = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
):
    product = _get_product_or_403(db, product_id, seller.id)
    comp = Competitor(
        product_id=product.id,
        seller_id=seller.id,
        competitor_name=body.competitor_name.strip(),
        platform=body.platform.strip().lower(),
        platform_id=body.platform_id.strip(),
        notes=body.notes.strip() if body.notes else None,
    )
    db.add(comp)
    db.commit()
    db.refresh(comp)
    return _competitor_to_out(comp)


@router.get("/products/{product_id}/competitors", response_model=List[dict])
def list_competitors(
    product_id: int,
    db: Session = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
):
    product = _get_product_or_403(db, product_id, seller.id)
    return [_competitor_to_out(c) for c in product.competitors if c.is_active]


def _get_competitor_or_403(db: Session, product_id: int, comp_id: int, seller_id: int) -> Competitor:
    product = _get_product_or_403(db, product_id, seller_id)
    comp = db.query(Competitor).filter(Competitor.id == comp_id, Competitor.product_id == product_id, Competitor.is_active == True).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Competitor not found")
    return comp


@router.patch("/products/{product_id}/competitors/{comp_id}", response_model=dict)
def update_competitor(
    product_id: int,
    comp_id: int,
    body: CompetitorUpdate,
    db: Session = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
):
    comp = _get_competitor_or_403(db, product_id, comp_id, seller.id)
    if body.competitor_name is not None:
        comp.competitor_name = body.competitor_name.strip()
    if body.platform_id is not None:
        comp.platform_id = body.platform_id.strip()
    if body.notes is not None:
        comp.notes = body.notes.strip() or None
    db.commit()
    db.refresh(comp)
    return _competitor_to_out(comp)


@router.delete("/products/{product_id}/competitors/{comp_id}")
def delete_competitor(
    product_id: int,
    comp_id: int,
    db: Session = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
):
    comp = _get_competitor_or_403(db, product_id, comp_id, seller.id)
    comp.is_active = False
    db.commit()
    return {"ok": True}
