"""
Pytest Test Suite for Persistent Auth, Refresh Tokens, Personal API Keys, and Rate Limiting Security.
"""

import pytest
from services.auth_service import AuthService
from schemas.auth_schemas import UserCreate


def test_refresh_token_rotation(client, db_session):
    """Test login issuing refresh token and rotating access token via POST /api/auth/refresh."""
    # 1. Register User
    user = AuthService.register_user(
        db_session,
        UserCreate(email="refreshtest@example.com", password="password123", full_name="Refresh User")
    )

    # 2. Login User
    res = client.post("/api/auth/login", json={"email": "refreshtest@example.com", "password": "password123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data

    old_access_token = data["access_token"]
    refresh_token = data["refresh_token"]

    # 3. Call POST /api/auth/refresh
    res_rf = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert res_rf.status_code == 200
    rf_data = res_rf.json()
    assert "access_token" in rf_data
    assert "refresh_token" in rf_data

    new_access_token = rf_data["access_token"]

    # 4. Use new access token to fetch profile
    res_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_access_token}"})
    assert res_me.status_code == 200
    assert res_me.json()["email"] == "refreshtest@example.com"


def test_api_key_generation_and_authentication(client, db_session):
    """Test generating a personal API Key and using X-API-Key header to authenticate requests."""
    # 1. Register User & get JWT access token
    user = AuthService.register_user(
        db_session,
        UserCreate(email="apikeytest@example.com", password="password123", full_name="API Key User")
    )
    jwt_token = AuthService.create_access_token(data={"sub": user.email})

    # 2. Generate API Key via POST /api/auth/api-key
    res_key = client.post("/api/auth/api-key", headers={"Authorization": f"Bearer {jwt_token}"})
    assert res_key.status_code == 200
    raw_api_key = res_key.json()["api_key"]
    assert raw_api_key.startswith("sk_live_")

    # 3. Use X-API-Key header to list categories
    res_cats = client.get("/api/categories", headers={"X-API-Key": raw_api_key})
    assert res_cats.status_code == 200
    categories = res_cats.json()
    assert len(categories) >= 1
    cat_id = categories[0]["id"]

    # 4. Use X-API-Key header to create expense
    exp_payload = {
        "amount": 2500.0,
        "currency": "LKR",
        "description": "Rapid API Key Transaction",
        "category_id": cat_id
    }
    res_exp = client.post("/api/expenses", json=exp_payload, headers={"X-API-Key": raw_api_key})
    assert res_exp.status_code == 201
    assert res_exp.json()["description"] == "Rapid API Key Transaction"

    # 5. Invalid API key returns 401 Unauthorized
    res_invalid = client.get("/api/expenses", headers={"X-API-Key": "sk_live_invalid_key_12345"})
    assert res_invalid.status_code == 401


def test_invalid_refresh_token_returns_401(client):
    """Verify invalid or corrupted refresh token returns 401 Unauthorized."""
    res = client.post("/api/auth/refresh", json={"refresh_token": "invalid_refresh_token_string"})
    assert res.status_code == 401
