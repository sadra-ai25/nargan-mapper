"""
Database Connection - اتصال به SQLite
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool


DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'nargan.db')
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """دریافت session دیتابیس"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """راه‌اندازی اولیه دیتابیس"""
    from .models import License, UsageLog
    Base.metadata.create_all(bind=engine)