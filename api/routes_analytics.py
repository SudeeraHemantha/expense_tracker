"""
FastAPI REST API Endpoints for Monthly Analytics Reports and Budget Monitoring.
Protected with get_current_user for multi-user data isolation.
"""

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User
from services.expense_service import ExpenseService
from services.analytics_service import AnalyticsService
from services.auth_service import get_current_user
from schemas.expense_schemas import (
    MonthlySpendingReport,
    BudgetCreate,
    BudgetResponse,
    BudgetAlert,
)

router = APIRouter(prefix="/analytics", tags=["Analytics & Budgets"])


@router.get("/monthly", response_model=MonthlySpendingReport, summary="Get monthly spending report")
def get_monthly_spending_report(
    year: Optional[int] = Query(None, ge=2000, le=2100, description="Report Year (YYYY)"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Report Month (1-12)"),
    month_year: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}$", description="Month in YYYY-MM format"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate monthly total spending and per-category percentage breakdown for current user."""
    today = date.today()

    if month_year:
        try:
            parsed_year, parsed_month = map(int, month_year.split("-"))
            year, month = parsed_year, parsed_month
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid month_year format. Use YYYY-MM."
            )

    target_year = year if year is not None else today.year
    target_month = month if month is not None else today.month

    return AnalyticsService.get_monthly_spending_report(db, target_year, target_month, user_id=current_user.id)


@router.get("/budgets", response_model=List[BudgetAlert], summary="Get category budget alerts status")
def get_budget_alerts(
    year: Optional[int] = Query(None, ge=2000, le=2100, description="Year (YYYY)"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Month (1-12)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve monthly budget limits and alert status (OK, WARNING, EXCEEDED) for current user."""
    today = date.today()
    target_year = year if year is not None else today.year
    target_month = month if month is not None else today.month

    return AnalyticsService.check_budget_status(db, target_year, target_month, user_id=current_user.id)


@router.post("/budgets", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED, summary="Set category monthly budget limit")
def set_category_budget(
    budget_in: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set or update monthly category budget limit threshold for current user."""
    try:
        return ExpenseService.create_budget(db, budget_in, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "Category ID" in str(e) else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
