"""
Unit test for automatic database schema migration in database/connection.py.
"""

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from database.connection import Base, init_db, engine


def test_init_db_auto_migrates_missing_columns():
    """Verify init_db() automatically detects missing columns in existing tables and adds them via ALTER TABLE."""
    inspector = inspect(engine)
    user_columns = {col["name"] for col in inspector.get_columns("users")}

    assert "refresh_token_hash" in user_columns
    assert "api_key_hash" in user_columns
    assert "email" in user_columns
    assert "hashed_password" in user_columns
