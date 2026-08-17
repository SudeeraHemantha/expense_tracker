"""
FastAPI REST API endpoints for User Registration, Authentication (Login), Token Refresh, API Key Generation, and User Profile.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User
from services.auth_service import AuthService, get_current_user
from schemas.auth_schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    RefreshTokenInput,
    APIKeyResponse,
)
from config.limiter import limiter

router = APIRouter(prefix="/auth", tags=["User Authentication & Security"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Register a new user account")
def register_user(
    user_in: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new user account with hashed password and auto-seed default categories specifically for that user.
    """
    try:
        user = AuthService.register_user(db, user_in)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=Token, summary="User authentication, access token & refresh token issuance")
@limiter.limit("5/minute")
def login_user(
    request: Request,
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Authenticate user email and password credentials.
    Returns 30-minute JWT access token and 30-day JWT refresh token.
    Rate limited to max 5 requests per minute.
    """
    user = AuthService.authenticate_user(db, email=credentials.email, password=credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email address or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    access_token = AuthService.create_access_token(data={"sub": user.email})
    refresh_token = AuthService.create_refresh_token(db=db, user=user)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post("/refresh", response_model=Token, summary="Refresh 30-minute access token using 30-day refresh token")
def refresh_access_token(
    payload: RefreshTokenInput,
    db: Session = Depends(get_db)
):
    """
    Validate 30-day refresh token and issue a fresh 30-minute access token.
    """
    user = AuthService.validate_refresh_token(db=db, refresh_token=payload.refresh_token)
    new_access_token = AuthService.create_access_token(data={"sub": user.email})
    # Rotate refresh token
    new_refresh_token = AuthService.create_refresh_token(db=db, user=user)

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer"
    )


@router.post("/api-key", response_model=APIKeyResponse, summary="Generate or regenerate personal API key")
def generate_personal_api_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate or regenerate a persistent, revocable personal API Key (sk_live_...) for rapid access via X-API-Key header.
    """
    raw_api_key = AuthService.generate_api_key(db=db, user=current_user)
    return APIKeyResponse(
        api_key=raw_api_key,
        created_at=datetime.now(timezone.utc).isoformat()
    )


@router.get("/me", response_model=UserResponse, summary="Get current authenticated user profile")
def get_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Return profile data for the currently authenticated user.
    """
    return current_user
