"""
Comprehensive Unit and Integration Pytest Test Suite for Expense Tracker.
Tests DB operations, services, validation errors, and FastAPI endpoints using in-memory SQLite with Auth headers.
"""

from datetime import date
from decimal import Decimal
import pytest

from services.expense_service import ExpenseService
from services.analytics_service import AnalyticsService
from schemas.expense_schemas import (
    CategoryCreate,
    ExpenseCreate,
    BudgetCreate,
)


# --- Category Service Tests ---
def test_create_and_get_category(db_session, test_user):
    """Verify category creation and retrieval by name/id."""
    cat = ExpenseService.create_category(
        db_session,
        CategoryCreate(name="Groceries", description="Food items"),
        user_id=test_user.id
    )
    assert cat.id is not None
    assert cat.name == "Groceries"
    assert cat.description == "Food items"

    fetched = ExpenseService.get_category_by_id(db_session, cat.id, user_id=test_user.id)
    assert fetched is not None
    assert fetched.name == "Groceries"

    all_cats = ExpenseService.get_categories(db_session, user_id=test_user.id)
    assert len(all_cats) == 7  # 6 seeded + 1 newly added


def test_duplicate_category_raises_error(db_session, test_user):
    """Verify creating a category with duplicate name raises ValueError for same user."""
    ExpenseService.create_category(db_session, CategoryCreate(name="TransportCustom"), user_id=test_user.id)
    with pytest.raises(ValueError, match="already exists"):
        ExpenseService.create_category(db_session, CategoryCreate(name="TransportCustom"), user_id=test_user.id)


# --- Expense Service Tests ---
def test_expense_crud_and_filtering(db_session, test_user):
    """Verify expense logging, filtering by date and category, and deletion."""
    cat_food = ExpenseService.create_category(db_session, CategoryCreate(name="FoodCustom"), user_id=test_user.id)
    cat_travel = ExpenseService.create_category(db_session, CategoryCreate(name="TravelCustom"), user_id=test_user.id)

    exp1 = ExpenseService.create_expense(
        db_session,
        ExpenseCreate(
            amount=50.00,
            currency="LKR",
            expense_date=date(2026, 8, 10),
            description="Lunch",
            category_id=cat_food.id
        ),
        user_id=test_user.id
    )
    exp2 = ExpenseService.create_expense(
        db_session,
        ExpenseCreate(
            amount=200.00,
            currency="LKR",
            expense_date=date(2026, 8, 15),
            description="Taxi",
            category_id=cat_travel.id
        ),
        user_id=test_user.id
    )

    assert exp1.id is not None
    assert exp2.id is not None

    food_exps = ExpenseService.get_expenses(db_session, user_id=test_user.id, category_id=cat_food.id)
    assert len(food_exps) == 1
    assert food_exps[0].description == "Lunch"

    range_exps = ExpenseService.get_expenses(
        db_session,
        user_id=test_user.id,
        start_date=date(2026, 8, 12),
        end_date=date(2026, 8, 20)
    )
    assert len(range_exps) == 1
    assert range_exps[0].description == "Taxi"

    success = ExpenseService.delete_expense(db_session, exp1.id, user_id=test_user.id)
    assert success is True
    assert ExpenseService.get_expense_by_id(db_session, exp1.id, user_id=test_user.id) is None


def test_invalid_category_expense_creation(db_session, test_user):
    """Verify creating an expense with non-existent category raises ValueError."""
    with pytest.raises(ValueError, match="Category ID 999 not found"):
        ExpenseService.create_expense(
            db_session,
            ExpenseCreate(amount=100.0, description="Test", category_id=999),
            user_id=test_user.id
        )


# --- Analytics & Budget Alert Tests ---
def test_monthly_spending_report_and_budget_alerts(db_session, test_user):
    """Verify monthly report calculation and budget alert status (OK, WARNING, EXCEEDED)."""
    cat_food = ExpenseService.create_category(db_session, CategoryCreate(name="FoodAlerts"), user_id=test_user.id)
    cat_bills = ExpenseService.create_category(db_session, CategoryCreate(name="BillsAlerts"), user_id=test_user.id)

    ExpenseService.create_budget(
        db_session,
        BudgetCreate(category_id=cat_food.id, monthly_limit=1000.0, month=8, year=2026),
        user_id=test_user.id
    )

    ExpenseService.create_expense(
        db_session,
        ExpenseCreate(amount=850.0, expense_date=date(2026, 8, 5), description="Groceries", category_id=cat_food.id),
        user_id=test_user.id
    )
    ExpenseService.create_expense(
        db_session,
        ExpenseCreate(amount=150.0, expense_date=date(2026, 8, 6), description="Internet", category_id=cat_bills.id),
        user_id=test_user.id
    )

    report = AnalyticsService.get_monthly_spending_report(db_session, year=2026, month=8, user_id=test_user.id)
    assert report.total_spent == 1000.0

    food_summary = next(c for c in report.breakdown_by_category if c.name == "FoodAlerts")
    assert food_summary.total_spent == 850.0

    alerts = AnalyticsService.check_budget_status(db_session, year=2026, month=8, user_id=test_user.id)
    assert len(alerts) == 1
    assert alerts[0].status == "WARNING"


# --- REST API Integration Endpoints Tests ---
def test_api_full_lifecycle(client, auth_headers):
    """Integration test testing FastAPI REST routes and HTTP status codes with Bearer token."""
    res = client.get("/")
    assert res.status_code == 200

    # 1. Create Category via POST /api/categories
    res = client.post("/api/categories", json={"name": "UtilitiesCustom", "description": "Utility bills"}, headers=auth_headers)
    assert res.status_code == 201
    cat_id = res.json()["id"]

    # 2. Get Categories via GET /api/categories
    res = client.get("/api/categories", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1

    # 3. Create Expense via POST /api/expenses
    res = client.post(
        "/api/expenses",
        json={
            "amount": 3500.0,
            "currency": "LKR",
            "expense_date": "2026-08-01",
            "description": "Electricity Bill",
            "notes": "Paid online",
            "category_id": cat_id
        },
        headers=auth_headers
    )
    assert res.status_code == 201
    exp_id = res.json()["id"]

    # 4. List Expenses via GET /api/expenses
    res = client.get(f"/api/expenses?category_id={cat_id}", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 1

    # 5. Get Expense by ID via GET /api/expenses/{id}
    res = client.get(f"/api/expenses/{exp_id}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["description"] == "Electricity Bill"

    # 6. Set Budget via POST /api/analytics/budgets
    res = client.post(
        "/api/analytics/budgets",
        json={"category_id": cat_id, "monthly_limit": 5000.0, "month": 8, "year": 2026},
        headers=auth_headers
    )
    assert res.status_code == 201

    # 7. Get Monthly Report via GET /api/analytics/monthly?year=2026&month=8
    res = client.get("/api/analytics/monthly?year=2026&month=8", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["total_spent"] == 3500.0

    # 8. Delete Expense via DELETE /api/expenses/{id}
    res = client.delete(f"/api/expenses/{exp_id}", headers=auth_headers)
    assert res.status_code == 204
