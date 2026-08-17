"""
Unit and Integration Pytest Test Suite for JWT Auth & Multi-Tenant Data Isolation.
"""

import pytest

from services.auth_service import AuthService
from services.expense_service import ExpenseService
from schemas.auth_schemas import UserCreate, UserLogin
from schemas.expense_schemas import CategoryCreate, ExpenseCreate


# --- Unit Tests ---
def test_password_hashing_and_verification():
    """Verify bcrypt password hashing and comparison."""
    password = "SecretPassword123"
    hashed = AuthService.get_password_hash(password)

    assert hashed != password
    assert AuthService.verify_password(password, hashed) is True
    assert AuthService.verify_password("WrongPassword", hashed) is False


def test_user_registration_seeds_categories(db_session):
    """Verify registering a new user seeds default categories for that user."""
    user = AuthService.register_user(
        db_session,
        UserCreate(email="newuser@example.com", password="password123", full_name="New User")
    )
    assert user.id is not None
    assert user.email == "newuser@example.com"

    cats = ExpenseService.get_categories(db_session, user_id=user.id)
    assert len(cats) == 6
    cat_names = [c.name for c in cats]
    assert "Food & Groceries" in cat_names


# --- Integration Tests ---
def test_api_auth_register_login_and_me(client):
    """Integration test for register, login, token issuance, and GET /api/auth/me."""
    # 1. Register User
    reg_payload = {"email": "apiuser@example.com", "password": "password123", "full_name": "API User"}
    res = client.post("/api/auth/register", json=reg_payload)
    assert res.status_code == 201
    assert res.json()["email"] == "apiuser@example.com"

    # 2. Login User
    login_payload = {"email": "apiuser@example.com", "password": "password123"}
    res = client.post("/api/auth/login", json=login_payload)
    assert res.status_code == 200
    token_data = res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    # 3. GET /api/auth/me with Bearer token
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    res = client.get("/api/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["email"] == "apiuser@example.com"


def test_multi_tenant_data_isolation(client, db_session):
    """Integration test verifying User A's expenses are completely isolated from User B."""
    # 1. Register User A and User B
    user_a = AuthService.register_user(db_session, UserCreate(email="usera@example.com", password="passwordA123", full_name="User A"))
    user_b = AuthService.register_user(db_session, UserCreate(email="userb@example.com", password="passwordB123", full_name="User B"))

    token_a = AuthService.create_access_token({"sub": user_a.email})
    token_b = AuthService.create_access_token({"sub": user_b.email})

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 2. Fetch User A categories and create expense for User A
    cats_a = ExpenseService.get_categories(db_session, user_id=user_a.id)
    cat_a_id = cats_a[0].id

    res_create = client.post(
        "/api/expenses",
        json={"amount": 5000.0, "currency": "LKR", "description": "User A Private Expense", "category_id": cat_a_id},
        headers=headers_a
    )
    assert res_create.status_code == 201

    # 3. Fetch User A expenses -> returns 1
    res_exps_a = client.get("/api/expenses", headers=headers_a)
    assert res_exps_a.status_code == 200
    assert len(res_exps_a.json()) == 1

    # 4. Fetch User B expenses -> returns 0 (User A's expense is isolated!)
    res_exps_b = client.get("/api/expenses", headers=headers_b)
    assert res_exps_b.status_code == 200
    assert len(res_exps_b.json()) == 0
