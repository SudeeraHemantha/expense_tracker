"""
Authentication & Authorization Security Service using bcrypt password hashing, JWT tokens,
Refresh Tokens, and Personal API Keys (X-API-Key).
Provides get_current_user dependency supporting dual-mode authentication.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets
import hashlib
import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader

from database.connection import get_db
from database.models import User, Category
from schemas.auth_schemas import UserCreate, TokenData
from config.settings import settings

security_bearer = HTTPBearer(auto_error=False)
security_api_key = APIKeyHeader(name="X-API-Key", auto_error=False)

DEFAULT_CATEGORIES = [
    ("Food & Groceries", "Supermarket items, groceries, and dining out"),
    ("Transport", "Fuel, public transit, taxis, and vehicle maintenance"),
    ("Bills & Utilities", "Electricity, water, internet, and mobile recharges"),
    ("Entertainment", "Movies, streaming subscriptions, and leisure activities"),
    ("Education", "Books, courses, tuition, and learning materials"),
    ("Health", "Medicines, doctor appointments, and fitness")
]


class AuthService:
    """Service handling password hashing, JWT token issuance, refresh tokens, and API key management."""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify plain text password against stored bcrypt hash."""
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            return False

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Generate bcrypt hash for raw password (max 72 bytes)."""
        pwd_bytes = password.encode('utf-8')[:72]
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

    @staticmethod
    def hash_token(token_str: str) -> str:
        """Generate SHA-256 hash for long token strings (refresh tokens and API keys)."""
        return hashlib.sha256(token_str.encode('utf-8')).hexdigest()

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Generate a signed 30-minute JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_refresh_token(db: Session, user: User) -> str:
        """Generate a signed 30-day JWT refresh token, hash with SHA-256, and store in database."""
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode = {"sub": user.email, "exp": expire, "type": "refresh"}
        refresh_token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        hashed_rf = AuthService.hash_token(refresh_token)
        user.refresh_token_hash = hashed_rf
        db.commit()
        db.refresh(user)

        return refresh_token

    @staticmethod
    def validate_refresh_token(db: Session, refresh_token: str) -> User:
        """
        Validate 30-day refresh token against database SHA-256 hash and return user entity.

        Raises:
            HTTPException 401: If token is invalid, expired, or revoked.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            email: str = payload.get("sub")
            token_type: str = payload.get("type")
            if email is None or token_type != "refresh":
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        user = AuthService.get_user_by_email(db, email=email)
        if user is None or not user.is_active or not user.refresh_token_hash:
            raise credentials_exception

        hashed_rf = AuthService.hash_token(refresh_token)
        if not secrets.compare_digest(hashed_rf, user.refresh_token_hash):
            raise credentials_exception

        return user

    @staticmethod
    def generate_api_key(db: Session, user: User) -> str:
        """Generate persistent, revocable sk_live_... API key, store SHA-256 hash in user profile, and return raw key."""
        raw_key = f"sk_live_{secrets.token_urlsafe(32)}"
        hashed_key = AuthService.hash_token(raw_key)

        user.api_key_hash = hashed_key
        db.commit()
        db.refresh(user)

        return raw_key

    @staticmethod
    def get_user_by_api_key(db: Session, api_key: str) -> Optional[User]:
        """Fetch active user by personal API key SHA-256 hash match."""
        if not api_key or not api_key.startswith("sk_live_"):
            return None
        hashed_key = AuthService.hash_token(api_key)
        stmt = select(User).where(User.api_key_hash == hashed_key)
        return db.scalar(stmt)

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Fetch user entity by email address."""
        stmt = select(User).where(User.email == email)
        return db.scalar(stmt)

    @staticmethod
    def register_user(db: Session, user_in: UserCreate) -> User:
        """
        Register a new user account with hashed password and auto-seed default categories.

        Raises:
            ValueError: If email is already registered.
        """
        existing_user = AuthService.get_user_by_email(db, user_in.email)
        if existing_user:
            raise ValueError(f"User with email '{user_in.email}' already exists.")

        hashed_pwd = AuthService.get_password_hash(user_in.password)
        db_user = User(
            email=user_in.email.lower().strip(),
            hashed_password=hashed_pwd,
            full_name=user_in.full_name.strip(),
            is_active=True
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        # Seed default categories specifically for this user
        for cat_name, cat_desc in DEFAULT_CATEGORIES:
            db_cat = Category(
                name=cat_name,
                description=cat_desc,
                user_id=db_user.id
            )
            db.add(db_cat)

        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate user credentials against stored hash."""
        user = AuthService.get_user_by_email(db, email.lower().strip())
        if not user:
            return None
        if not AuthService.verify_password(password, user.hashed_password):
            return None
        return user


def get_current_user(
    api_key_header: Optional[str] = Depends(security_api_key),
    auth_credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency extracting credentials via dual authentication:
    1. X-API-Key header (for persistent API access without login)
    2. Authorization: Bearer JWT access token (for browser UI sessions)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or API key",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Mode 1: Check X-API-Key Header
    if api_key_header:
        user = AuthService.get_user_by_api_key(db, api_key_header)
        if user and user.is_active:
            return user
        raise credentials_exception

    # Mode 2: Check Authorization: Bearer <token> Header
    if auth_credentials and auth_credentials.credentials:
        token = auth_credentials.credentials
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            email: str = payload.get("sub")
            token_type: str = payload.get("type", "access")

            if email is None or token_type != "access":
                raise credentials_exception

            token_data = TokenData(email=email, token_type=token_type)
        except JWTError:
            raise credentials_exception

        user = AuthService.get_user_by_email(db, email=token_data.email)
        if user is None or not user.is_active:
            raise credentials_exception

        return user

    raise credentials_exception
