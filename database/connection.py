"""
Database connection, engine initialization, session management, and get_db dependency.
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from config.settings import settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy 2.0 declarative models."""
    pass


# SQLite connection arguments for multithreaded access
connect_args = {}
if settings.DB_PATH.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DB_PATH,
    connect_args=connect_args,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create database tables if they do not exist."""
    Base.metadata.create_all(bind=engine)
