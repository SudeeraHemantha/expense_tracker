"""
FastAPI REST API endpoints for Recurring Expenses & Subscriptions management.
Protected with get_current_user for multi-user data isolation.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User
from services.recurring_service import RecurringExpenseService
from services.auth_service import get_current_user
from schemas.expense_schemas import (
    RecurringExpenseCreate,
    RecurringExpenseResponse,
    ExpenseResponse,
)

router = APIRouter(prefix="/recurring", tags=["Recurring Expenses & Subscriptions"])


@router.get("", response_model=List[RecurringExpenseResponse], summary="List recurring subscriptions")
@router.get("/", response_model=List[RecurringExpenseResponse], include_in_schema=False)
def list_recurring_expenses(
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve all registered recurring expense subscriptions and upcoming due dates for current user."""
    return RecurringExpenseService.get_recurring_expenses(db, user_id=current_user.id, is_active=is_active)


@router.post("", response_model=RecurringExpenseResponse, status_code=status.HTTP_201_CREATED, summary="Register recurring expense")
@router.post("/", response_model=RecurringExpenseResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_recurring_expense(
    recurring_in: RecurringExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Register a new recurring commitment or subscription for current user."""
    try:
        return RecurringExpenseService.create_recurring(db, recurring_in, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "Category ID" in str(e) else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/process", response_model=List[ExpenseResponse], summary="Process due recurring expenses")
def process_due_recurring(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check all active recurring items for current user where next_due_date <= today, auto-log expense, advance due dates."""
    created_expenses = RecurringExpenseService.process_due_recurring_expenses(db, user_id=current_user.id)
    return created_expenses


@router.delete("/{recurring_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete recurring subscription rule")
def delete_recurring_expense(
    recurring_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a recurring subscription rule by ID for current user."""
    deleted = RecurringExpenseService.delete_recurring(db, recurring_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recurring rule with ID {recurring_id} not found."
        )
    return None
