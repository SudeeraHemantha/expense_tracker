"""
Unit and Integration tests for AI Natural Language Expense Parser with Auth headers.
"""

from datetime import date
import pytest

from services.expense_service import ExpenseService
from services.ai_expense_service import AIExpenseService
from schemas.expense_schemas import CategoryCreate


# --- Unit Tests ---
def test_parse_amount_currency_relative_date_and_category():
    """Verify natural language parsing of amount, currency, relative date ('yesterday'), and category."""
    ref_today = date(2026, 8, 17)
    text = "Spent 3500 LKR on groceries and vegetables yesterday"
    categories = ["Food & Groceries", "Transport", "Bills & Utilities"]

    parsed = AIExpenseService.parse_natural_language(text, available_categories=categories, ref_date=ref_today)

    assert parsed.amount == 3500.0
    assert parsed.currency == "LKR"
    assert parsed.category_name == "Food & Groceries"
    assert parsed.expense_date == date(2026, 8, 16)
    assert parsed.confidence_score >= 0.75


def test_parse_transport_fuel_today():
    """Verify parsing transport expense for today."""
    ref_today = date(2026, 8, 17)
    text = "Paid 2500 LKR for petrol fuel fill up today"
    categories = ["Food & Groceries", "Transport", "Bills & Utilities"]

    parsed = AIExpenseService.parse_natural_language(text, available_categories=categories, ref_date=ref_today)

    assert parsed.amount == 2500.0
    assert parsed.currency == "LKR"
    assert parsed.category_name == "Transport"
    assert parsed.expense_date == date(2026, 8, 17)


def test_empty_text_raises_value_error():
    """Verify empty text string raises ValueError."""
    with pytest.raises(ValueError, match="Input text cannot be empty"):
        AIExpenseService.parse_natural_language("", available_categories=["Food"])


# --- Integration Tests ---
def test_api_ai_parse_expense_endpoint(client, test_user, auth_headers):
    """Integration test verifying POST /api/ai/parse-expense creates an expense record in DB with auth."""
    payload = {"text": "Spent 4500 LKR on supermarket groceries yesterday"}
    res = client.post("/api/ai/parse-expense", json=payload, headers=auth_headers)

    assert res.status_code == 201
    data = res.json()
    assert data["amount"] == 4500.0
    assert data["currency"] == "LKR"
    assert "Spent 4500 LKR" in data["description"]
    assert "AI Parsed" in data["notes"]
