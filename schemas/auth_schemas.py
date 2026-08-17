"""
Pydantic v2 schemas for User Authentication & Authorization DTOs.
Includes Token Refresh and Personal API Key models.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr, ConfigDict


class UserCreate(BaseModel):
    """Payload schema for user registration."""
    email: EmailStr = Field(..., description="Unique user email address")
    password: str = Field(..., min_length=6, max_length=100, description="Raw user password")
    full_name: str = Field(..., min_length=1, max_length=255, description="Full name of user")


class UserLogin(BaseModel):
    """Payload schema for user login credentials."""
    email: EmailStr = Field(..., description="Registered user email address")
    password: str = Field(..., description="Raw user password")


class UserResponse(BaseModel):
    """Response schema for User profile entity."""
    id: int
    email: EmailStr
    full_name: str
    created_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """JWT Bearer token response schema including access and refresh tokens."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class RefreshTokenInput(BaseModel):
    """Payload schema for token refresh request."""
    refresh_token: str = Field(..., description="Valid 30-day JWT refresh token")


class APIKeyResponse(BaseModel):
    """Response schema when generating a personal API key."""
    api_key: str = Field(..., description="Raw personal API key (sk_live_...)")
    created_at: str = Field(..., description="Creation timestamp ISO string")


class TokenData(BaseModel):
    """Parsed JWT payload token data."""
    email: Optional[str] = None
    token_type: Optional[str] = "access"
