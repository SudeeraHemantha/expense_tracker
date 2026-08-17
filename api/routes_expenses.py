"""
FastAPI REST API Endpoints for Expense Logging and Filtering.
Protected with get_current_user for multi-user data isolation.
"""

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User
from services.expense_service import ExpenseService
from services.auth_service import get_current_user
from schemas.expense_schemas import ExpenseCreate, ExpenseResponse

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.get("", response_model=List[ExpenseResponse], summary="Filter and list expenses")
@router.get("/", response_model=List[ExpenseResponse], include_in_schema=False)
def list_expenses(
    start_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    skip: int = Query(0, ge=0, description="Pagination skip count"),
    limit: int = Query(100, ge=1, le=1000, description="Pagination page size"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve filtered list of financial expenses for the current user."""
    return ExpenseService.get_expenses(
        db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        skip=skip,
        limit=limit
    )


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED, summary="Log a new expense")
@router.post("/", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_expense(
    expense_in: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Log a new financial expense transaction for the current user."""
    try:
        return ExpenseService.create_expense(db, expense_in, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "Category ID" in str(e) else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{expense_id}", response_model=ExpenseResponse, summary="Get single expense details")
def get_expense_by_id(
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve details for a single expense by ID for the current user."""
    expense = ExpenseService.get_expense_by_id(db, expense_id, user_id=current_user.id)
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with ID {expense_id} not found."
        )
    return expense


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete expense record")
def delete_expense(
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an expense record by ID for the current user."""
    deleted = ExpenseService.delete_expense(db, expense_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with ID {expense_id} not found."
        )
    return None
