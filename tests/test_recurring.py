"""
Unit and Integration Pytest Test Suite for Recurring Expenses & Subscriptions Engine with Auth headers.
"""

from datetime import date, timedelta
import pytest

from services.expense_service import ExpenseService
from services.recurring_service import RecurringExpenseService
from schemas.expense_schemas import CategoryCreate, RecurringExpenseCreate


# --- Unit Tests ---
def test_calculate_next_due_date_advancement():
    """Verify next due date calculation for DAILY, WEEKLY, MONTHLY, and YEARLY frequencies."""
    start = date(2026, 8, 1)

    daily_next = RecurringExpenseService.calculate_next_due_date(start, "DAILY")
    assert daily_next == date(2026, 8, 2)

    weekly_next = RecurringExpenseService.calculate_next_due_date(start, "WEEKLY")
    assert weekly_next == date(2026, 8, 8)

    monthly_next = RecurringExpenseService.calculate_next_due_date(start, "MONTHLY")
    assert monthly_next == date(2026, 9, 1)

    yearly_next = RecurringExpenseService.calculate_next_due_date(start, "YEARLY")
    assert yearly_next == date(2027, 8, 1)


def test_recurring_crud_and_auto_logging(db_session, test_user):
    """Verify creating a recurring subscription and auto-logging due expenses."""
    cats = ExpenseService.get_categories(db_session, user_id=test_user.id)
    cat_id = cats[0].id

    past_due_date = date.today() - timedelta(days=5)
    rec_in = RecurringExpenseCreate(
        title="Fiber Internet Bill",
        amount=3500.0,
        currency="LKR",
        category_id=cat_id,
        frequency="MONTHLY",
        start_date=past_due_date,
        auto_log=True
    )

    rule = RecurringExpenseService.create_recurring(db_session, rec_in, user_id=test_user.id)
    assert rule.id is not None
    assert rule.next_due_date == past_due_date

    new_expenses = RecurringExpenseService.process_due_recurring_expenses(db_session, user_id=test_user.id, target_date=date.today())

    assert len(new_expenses) == 1
    logged_exp = new_expenses[0]
    assert logged_exp.amount == 3500.0
    assert "Recurring: Fiber Internet Bill" in logged_exp.description


# --- Integration Tests ---
def test_api_recurring_endpoints_lifecycle(client, test_user, auth_headers, db_session):
    """Integration test for POST /api/recurring, GET /api/recurring, and POST /api/recurring/process."""
    cats = ExpenseService.get_categories(db_session, user_id=test_user.id)
    cat_id = cats[0].id

    payload = {
        "title": "Netflix Premium",
        "amount": 2200.0,
        "currency": "LKR",
        "category_id": cat_id,
        "frequency": "MONTHLY",
        "start_date": (date.today() - timedelta(days=1)).isoformat(),
        "auto_log": True
    }

    res = client.post("/api/recurring", json=payload, headers=auth_headers)
    assert res.status_code == 201
    rec_id = res.json()["id"]

    res = client.get("/api/recurring", headers=auth_headers)
    assert res.status_code == 200
    sub_list = res.json()
    assert len(sub_list) == 1
    assert sub_list[0]["title"] == "Netflix Premium"

    res = client.post("/api/recurring/process", headers=auth_headers)
    assert res.status_code == 200
    processed = res.json()
    assert len(processed) == 1

    res = client.delete(f"/api/recurring/{rec_id}", headers=auth_headers)
    assert res.status_code == 204
