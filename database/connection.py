"""
Database connection, engine initialization, session management, and get_db dependency.
"""

from typing import Generator
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from config.settings import settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy 2.0 declarative models."""
    pass


# SQLite connection arguments for multithreaded access
db_url = settings.effective_db_path
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    db_url,
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
    """
    Create database tables if they do not exist, auto-migrate missing columns,
    and fallback to drop-and-recreate in local development mode if schema corruption/mismatch occurs.
    """
    # Ensure models are imported so Base.metadata contains all tables
    import database.models  # noqa: F401

    try:
        # 1. Create missing tables
        Base.metadata.create_all(bind=engine)

        # 2. Inspect existing tables and automatically add missing columns
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())

        with engine.begin() as conn:
            for table_name, table_obj in Base.metadata.tables.items():
                if table_name not in existing_tables:
                    continue

                existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
                for column in table_obj.columns:
                    if column.name not in existing_columns:
                        col_type = column.type.compile(engine.dialect)
                        default_clause = ""
                        if not column.nullable:
                            default_clause = " DEFAULT ''"

                        alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type}{default_clause}"
                        conn.execute(text(alter_sql))

                        if column.index:
                            idx_name = f"ix_{table_name}_{column.name}"
                            conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({column.name})"))

        # 3. Validation query check (verify users table has all required columns)
        with engine.connect() as conn:
            conn.execute(text("SELECT id, email, refresh_token_hash, api_key_hash FROM users LIMIT 1"))

    except Exception as e:
        # In local development mode, if schema mismatch occurs, recreate tables cleanly
        if settings.DEBUG or settings.APP_ENV == "development":
            print(f"[Database Init] Schema mismatch/error detected ({e}). Recreating database tables for development mode...")
            try:
                Base.metadata.drop_all(bind=engine)
                Base.metadata.create_all(bind=engine)
                print("[Database Init] Tables successfully recreated.")
            except Exception as drop_err:
                print(f"[Database Init] Could not recreate tables: {drop_err}")
        else:
            raise e
