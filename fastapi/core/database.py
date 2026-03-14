from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

db_url = os.getenv("SQLALCHEMY_DATABASE_URL")

engine = create_engine(
    db_url,
    pool_pre_ping=True
)

# TEST CONNECTION
with engine.connect() as conn:
    print("Connected to DB")

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()