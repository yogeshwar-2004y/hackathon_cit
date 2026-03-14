"""
Authentication: signup, login, JWT, get_current_seller.
"""
import os
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db, Seller

router = APIRouter()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv("JWT_SECRET", "shadowspy-secret-2026")
ALGORITHM = "HS256"
EXPIRY_DAYS = int(os.getenv("JWT_EXPIRY_DAYS", "7"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class SignupBody(BaseModel):
    email: str
    password: str
    business_name: str
    phone: Optional[str] = None
    platform: str = "amazon"


class SellerOut(BaseModel):
    id: int
    email: str
    business_name: str
    phone: Optional[str]
    platform: str
    is_active: bool

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    seller: SellerOut


# ---------------------------------------------------------------------------
# Helpers (bcrypt directly to avoid passlib/bcrypt version mismatch on Python 3.14)
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    secret = password.encode("utf-8")[:72]  # bcrypt limit 72 bytes
    return bcrypt.hashpw(secret, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=EXPIRY_DAYS)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def seller_to_out(s: Seller) -> SellerOut:
    return SellerOut(
        id=s.id,
        email=s.email,
        business_name=s.business_name,
        phone=s.phone,
        platform=s.platform,
        is_active=s.is_active,
    )


# ---------------------------------------------------------------------------
# Dependencies: current seller from JWT
# ---------------------------------------------------------------------------
def get_current_seller(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Seller:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    seller_id = payload.get("sub")
    if not seller_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        seller_id = int(seller_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    seller = db.query(Seller).filter(Seller.id == seller_id, Seller.is_active == True).first()
    if not seller:
        raise HTTPException(status_code=401, detail="Seller not found or inactive")
    return seller


def get_current_seller_from_token_or_query(request: Request, db: Session = Depends(get_db)):
    token = (request.headers.get("Authorization") or "").strip()
    if token.startswith("Bearer "):
        token = token[7:]
    if not token:
        token = request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    try:
        seller_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    seller = db.query(Seller).filter(Seller.id == seller_id, Seller.is_active == True).first()
    if not seller:
        raise HTTPException(status_code=401, detail="Seller not found")
    return seller


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.post("/signup", response_model=TokenOut)
def signup(body: SignupBody, db: Session = Depends(get_db)):
    existing = db.query(Seller).filter(Seller.email == body.email.strip().lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    seller = Seller(
        email=body.email.strip().lower(),
        password_hash=hash_password(body.password),
        business_name=body.business_name.strip(),
        phone=body.phone.strip() if body.phone else None,
        platform=(body.platform or "amazon").strip().lower(),
    )
    db.add(seller)
    db.commit()
    db.refresh(seller)
    token = create_access_token(data={"sub": str(seller.id)})
    return TokenOut(access_token=token, seller=seller_to_out(seller))


@router.post("/login", response_model=TokenOut)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    seller = db.query(Seller).filter(Seller.email == form_data.username.strip().lower(), Seller.is_active == True).first()
    if not seller or not verify_password(form_data.password, seller.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(data={"sub": str(seller.id)})
    return TokenOut(access_token=token, seller=seller_to_out(seller))


@router.get("/me", response_model=SellerOut)
def me(seller: Seller = Depends(get_current_seller)):
    return seller_to_out(seller)


