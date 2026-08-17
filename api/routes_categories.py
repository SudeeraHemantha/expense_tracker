"""
FastAPI REST API Endpoints for Category Management.
Protected with get_current_user for multi-user data isolation.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User
from services.expense_service import ExpenseService
from services.auth_service import get_current_user
from schemas.expense_schemas import CategoryCreate, CategoryResponse

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=List[CategoryResponse], summary="Retrieve all categories")
@router.get("/", response_model=List[CategoryResponse], include_in_schema=False)
def list_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve all expense categories registered for the current user."""
    return ExpenseService.get_categories(db, user_id=current_user.id)


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED, summary="Create category")
@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_category(
    category_in: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new unique expense category for the current user."""
    try:
        return ExpenseService.create_category(db, category_in, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
