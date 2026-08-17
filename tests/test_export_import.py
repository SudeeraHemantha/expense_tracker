"""
Unit and Integration Pytest Test Suite for Monthly CSV/Excel Export & Bulk Bank CSV Import with Auth headers.
"""

import io
from datetime import date
import pytest
import pandas as pd
import openpyxl

from services.expense_service import ExpenseService
from services.export_service import ExportService
from services.import_service import ImportService
from schemas.expense_schemas import CategoryCreate, ExpenseCreate


# --- Unit Tests ---
def test_export_monthly_csv_unit(db_session, test_user):
    """Verify CSV export string generation."""
    cats = ExpenseService.get_categories(db_session, user_id=test_user.id)
    cat_id = cats[0].id

    ExpenseService.create_expense(
        db_session,
        ExpenseCreate(
            amount=4500.0,
            currency="LKR",
            expense_date=date(2026, 8, 15),
            description="Supermarket Groceries",
            category_id=cat_id
        ),
        user_id=test_user.id
    )

    csv_output = ExportService.export_monthly_csv(db_session, 2026, 8, user_id=test_user.id)

    assert "ID,Date,Category,Amount,Currency,Description,Notes" in csv_output
    assert "4500.00" in csv_output
    assert "Supermarket Groceries" in csv_output


def test_export_monthly_excel_unit(db_session, test_user):
    """Verify Excel workbook generation with 'Transactions' and 'Summary' sheets."""
    cats = ExpenseService.get_categories(db_session, user_id=test_user.id)
    cat_id = cats[0].id

    ExpenseService.create_expense(
        db_session,
        ExpenseCreate(
            amount=1500.0,
            currency="LKR",
            expense_date=date(2026, 8, 10),
            description="Taxi Ride",
            category_id=cat_id
        ),
        user_id=test_user.id
    )

    excel_bytes = ExportService.export_monthly_excel(db_session, 2026, 8, user_id=test_user.id)
    assert len(excel_bytes) > 0

    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    sheet_names = wb.sheetnames

    assert "Transactions" in sheet_names
    assert "Summary" in sheet_names


def test_import_bank_csv_unit(db_session, test_user):
    """Verify bank statement CSV parsing and auto-categorized expense bulk logging."""
    mock_csv_content = (
        "Date,Amount,Description\n"
        "2026-08-01,3500.00,Supermarket Groceries\n"
        "2026-08-02,2500.00,Petrol Fuel Fillup\n"
    ).encode("utf-8")

    result = ImportService.import_bank_csv(db_session, mock_csv_content, user_id=test_user.id)

    assert result["total_rows"] == 2
    assert result["imported_count"] == 2
    assert result["skipped_count"] == 0


# --- Integration Tests ---
def test_api_export_and_import_endpoints_integration(client, test_user, auth_headers):
    """Integration test verifying GET /api/export/csv, GET /api/export/excel, and POST /api/import/csv with auth."""
    res = client.get("/api/export/csv?year=2026&month=8", headers=auth_headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]

    res = client.get("/api/export/excel?year=2026&month=8", headers=auth_headers)
    assert res.status_code == 200
    assert "spreadsheetml" in res.headers["content-type"]

    csv_bytes = (
        "Transaction Date,Debit Amount,Merchant Narration\n"
        "2026-08-05,1850.00,Electricity Bill Online Payment\n"
    ).encode("utf-8")

    files = {"file": ("statement.csv", csv_bytes, "text/csv")}
    res = client.post("/api/import/csv", files=files, headers=auth_headers)

    assert res.status_code == 200
    data = res.json()
    assert "summary" in data
    assert data["summary"]["imported_count"] == 1
