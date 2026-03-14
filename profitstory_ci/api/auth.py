"""
Authentication: signup, login, JWT, get_current_seller, password policy, audit, forgot/reset password.
"""
import os
import re
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db, Seller, AuditEvent, PasswordResetToken

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


class ForgotPasswordBody(BaseModel):
    email: str


class ResetPasswordBody(BaseModel):
    token: str
    new_password: str


class ChangePasswordBody(BaseModel):
    old_password: str
    new_password: str


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
# Password policy & audit
# ---------------------------------------------------------------------------
PASSWORD_MIN_LEN = 8
PASSWORD_RE_UPPER = re.compile(r"[A-Z]")
PASSWORD_RE_LOWER = re.compile(r"[a-z]")
PASSWORD_RE_DIGIT = re.compile(r"\d")
PASSWORD_RE_SPECIAL = re.compile(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]")

def validate_password(password: str) -> tuple[bool, str]:
    if len(password) < PASSWORD_MIN_LEN:
        return False, f"Password must be at least {PASSWORD_MIN_LEN} characters"
    if not PASSWORD_RE_UPPER.search(password):
        return False, "Password must contain at least one uppercase letter"
    if not PASSWORD_RE_LOWER.search(password):
        return False, "Password must contain at least one lowercase letter"
    if not PASSWORD_RE_DIGIT.search(password):
        return False, "Password must contain at least one digit"
    if not PASSWORD_RE_SPECIAL.search(password):
        return False, "Password must contain at least one special character (!@#$%^&*...)"
    return True, ""


def _client_ip(request: Optional[Request]) -> Optional[str]:
    if not request:
        return None
    return request.client.host if request.client else (request.headers.get("x-forwarded-for") or "").split(",")[0].strip() or None


def log_audit(
    db: Session,
    seller_id: int,
    action: str,
    resource: Optional[str] = None,
    detail: Optional[str] = None,
    request: Optional[Request] = None,
):
    ev = AuditEvent(
        seller_id=seller_id,
        action=action,
        resource=resource,
        detail=detail,
        ip_address=_client_ip(request),
    )
    db.add(ev)
    db.commit()


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
def signup(body: SignupBody, request: Request, db: Session = Depends(get_db)):
    ok, msg = validate_password(body.password)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
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
    log_audit(db, seller.id, "signup", "account", body.email.strip().lower(), request)
    token = create_access_token(data={"sub": str(seller.id)})
    return TokenOut(access_token=token, seller=seller_to_out(seller))


@router.post("/login", response_model=TokenOut)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    seller = db.query(Seller).filter(Seller.email == form_data.username.strip().lower(), Seller.is_active == True).first()
    if not seller or not verify_password(form_data.password, seller.password_hash):
        if seller:
            log_audit(db, seller.id, "login_fail", "account", "Invalid password", request)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    log_audit(db, seller.id, "login_ok", "account", None, request)
    token = create_access_token(data={"sub": str(seller.id)})
    return TokenOut(access_token=token, seller=seller_to_out(seller))


@router.get("/me", response_model=SellerOut)
def me(seller: Seller = Depends(get_current_seller)):
    return seller_to_out(seller)


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordBody, request: Request, db: Session = Depends(get_db)):
    seller = db.query(Seller).filter(Seller.email == body.email.strip().lower(), Seller.is_active == True).first()
    if not seller:
        return {"message": "If an account exists with this email, you will receive a reset link."}
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_reset_token(raw_token)
    expires_at = datetime.utcnow() + timedelta(hours=1)
    rec = PasswordResetToken(seller_id=seller.id, token_hash=token_hash, expires_at=expires_at)
    db.add(rec)
    db.commit()
    log_audit(db, seller.id, "password_reset_request", "account", None, request)
    # In production send email with link. For dev, frontend can show link from reset_path.
    reset_path = f"/reset-password?token={raw_token}"
    return {
        "message": "If an account exists with this email, you will receive a reset link.",
        "reset_path": reset_path,
    }


@router.post("/reset-password")
def reset_password(body: ResetPasswordBody, request: Request, db: Session = Depends(get_db)):
    ok, msg = validate_password(body.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    token_hash = _hash_reset_token(body.token.strip())
    rec = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at == None,
            PasswordResetToken.expires_at > datetime.utcnow(),
        )
        .first()
    )
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link. Request a new one.")
    seller = db.query(Seller).filter(Seller.id == rec.seller_id).first()
    if not seller or not seller.is_active:
        raise HTTPException(status_code=400, detail="Account not found or inactive.")
    seller.password_hash = hash_password(body.new_password)
    rec.used_at = datetime.utcnow()
    db.commit()
    log_audit(db, seller.id, "password_reset_used", "account", None, request)
    return {"message": "Password updated. You can sign in with your new password."}


@router.post("/change-password")
def change_password(
    body: ChangePasswordBody,
    request: Request,
    db: Session = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
):
    if not verify_password(body.old_password, seller.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    ok, msg = validate_password(body.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    seller.password_hash = hash_password(body.new_password)
    db.commit()
    log_audit(db, seller.id, "password_change", "account", None, request)
    return {"message": "Password updated."}


@router.get("/audit")
def audit_events(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
):
    rows = (
        db.query(AuditEvent)
        .filter(AuditEvent.seller_id == seller.id)
        .order_by(AuditEvent.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {
        "events": [
            {
                "id": r.id,
                "action": r.action,
                "resource": r.resource,
                "detail": r.detail,
                "ip_address": r.ip_address,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


