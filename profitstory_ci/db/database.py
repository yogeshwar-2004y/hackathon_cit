"""
Multi-tenant schema (SQLAlchemy ORM) on Neon PostgreSQL.
Tables: sellers, products, competitors, agent_runs, price_history, review_stats.
Uses DATABASE_URL (Neon) when set; no separate SQLite — one DB for less complexity.
"""
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

Base = declarative_base()

# Single DB: Neon PostgreSQL via DATABASE_URL (same as api/db.py and pgvector).
# No SQLite — one connection string for app + embeddings.
_raw_url = os.environ.get("DATABASE_URL", "").strip()
if _raw_url and (_raw_url.startswith("postgresql://") or _raw_url.startswith("postgres://")):
    # Ensure SQLAlchemy uses psycopg2 driver (Neon)
    if "postgresql://" in _raw_url and "+" not in _raw_url.split("://")[0]:
        _raw_url = _raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    elif _raw_url.startswith("postgres://"):
        _raw_url = "postgresql+psycopg2://" + _raw_url[len("postgres://"):]
    DATABASE_URL = _raw_url
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    # Fallback for local dev without Neon (optional)
    DB_DIR = os.path.join(os.path.dirname(__file__), "..")
    SQLITE_PATH = os.environ.get("SQLITE_DB_PATH", os.path.join(DB_DIR, "shadowspy.db"))
    DATABASE_URL = f"sqlite:///{SQLITE_PATH}"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Seller(Base):
    __tablename__ = "sellers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    business_name = Column(String(255), nullable=False)
    phone = Column(String(64), nullable=True)
    platform = Column(String(32), default="amazon")  # amazon | flipkart | snapdeal | all
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    products = relationship("Product", back_populates="seller")


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, autoincrement=True)
    seller_id = Column(Integer, ForeignKey("sellers.id"), nullable=False)
    product_name = Column(String(255), nullable=False)
    category = Column(String(128), nullable=False)
    platform = Column(String(32), nullable=False)  # amazon | flipkart | snapdeal
    platform_id = Column(String(128), nullable=False)  # ASIN / FSN / Snapdeal product ID
    price = Column(Float, nullable=True)
    cost = Column(Float, nullable=True)
    monthly_units = Column(Integer, default=40)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    seller = relationship("Seller", back_populates="products")
    competitors = relationship("Competitor", back_populates="product")
    agent_runs = relationship("AgentRun", back_populates="product")
    price_history_rel = relationship("PriceHistory", back_populates="product")
    review_stats_rel = relationship("ReviewStats", back_populates="product")


class Competitor(Base):
    __tablename__ = "competitors"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("sellers.id"), nullable=False)
    competitor_name = Column(String(255), nullable=False)
    platform = Column(String(32), nullable=False)
    platform_id = Column(String(128), nullable=False)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    product = relationship("Product", back_populates="competitors")


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    seller_id = Column(Integer, ForeignKey("sellers.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    run_id = Column(String(64), unique=True, nullable=False)
    status = Column(String(32), default="pending")  # pending | running | done | error
    vuln_scores = Column(Text, nullable=True)  # JSON
    pivot_memo = Column(Text, nullable=True)
    profit_sims = Column(Text, nullable=True)  # JSON
    signals = Column(Text, nullable=True)  # JSON
    error_msg = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    product = relationship("Product", back_populates="agent_runs")


class PriceHistory(Base):
    __tablename__ = "price_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    platform_id = Column(String(128), nullable=False)
    price = Column(Float, nullable=False)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    product = relationship("Product", back_populates="price_history_rel")


class ReviewStats(Base):
    __tablename__ = "review_stats"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    platform_id = Column(String(128), nullable=False)
    avg_sentiment = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True)
    rating = Column(Float, nullable=True)
    review_spike = Column(Integer, nullable=True)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    product = relationship("Product", back_populates="review_stats_rel")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    seller_id = Column(Integer, ForeignKey("sellers.id"), nullable=False)
    action = Column(String(64), nullable=False)  # login_ok, login_fail, signup, password_change, password_reset_request, password_reset_used
    resource = Column(String(128), nullable=True)  # e.g. account, product:123
    detail = Column(Text, nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id = Column(Integer, primary_key=True, autoincrement=True)
    seller_id = Column(Integer, ForeignKey("sellers.id"), nullable=False)
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
