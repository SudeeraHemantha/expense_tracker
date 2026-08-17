"""
Pydantic v2 Schemas for Expense Tracker API (DTOs & Analytics).
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


# Category Schemas
class CategoryBase(BaseModel):
    """Base schema for category payload."""
    name: str = Field(..., min_length=1, max_length=50, description="Unique category name")
    description: Optional[str] = Field(default=None, max_length=255, description="Category description")


class CategoryCreate(CategoryBase):
    """Schema for creating a new category."""
    pass


class CategoryResponse(CategoryBase):
    """Response schema for category entity."""
    model_config = ConfigDict(from_attributes=True)

    id: int


# Expense Schemas
class ExpenseBase(BaseModel):
    """Base schema for expense payload."""
    amount: float = Field(..., gt=0.0, description="Expense transaction amount")
    currency: Optional[str] = Field(default="LKR", min_length=3, max_length=3, description="3-character currency code")
    expense_date: Optional[date] = Field(default=None, description="Date of expense")
    description: str = Field(..., min_length=1, max_length=255, description="Brief expense description")
    notes: Optional[str] = Field(default=None, description="Detailed expense notes")
    category_id: int = Field(..., gt=0, description="ID of category")


class ExpenseCreate(ExpenseBase):
    """Schema for creating a new expense entry."""
    pass


class ExpenseResponse(ExpenseBase):
    """Response schema for expense entity."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    expense_date: date
    currency: str
    created_at: Optional[datetime] = None
    category: Optional[CategoryResponse] = None


# Budget Schemas
class BudgetBase(BaseModel):
    """Base schema for budget payload."""
    category_id: int = Field(..., gt=0, description="ID of category")
    monthly_limit: float = Field(..., gt=0.0, description="Maximum monthly spending threshold")
    month: int = Field(..., ge=1, le=12, description="Month of budget (1-12)")
    year: int = Field(..., ge=2000, le=2100, description="Year of budget (YYYY)")


class BudgetCreate(BudgetBase):
    """Schema for creating or updating a budget threshold."""
    pass


class BudgetResponse(BudgetBase):
    """Response schema for budget entity."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: Optional[CategoryResponse] = None


# Analytics Schemas
class CategorySummary(BaseModel):
    """Spending breakdown per category in a given timeframe."""
    name: str = Field(..., description="Category name")
    total_spent: float = Field(..., description="Total amount spent in this category")
    percentage: float = Field(..., description="Percentage of overall spending for the period")

    model_config = ConfigDict(from_attributes=True)


class MonthlySpendingReport(BaseModel):
    """Aggregated report of total monthly spending and breakdown by category."""
    year: int = Field(..., description="Report year (YYYY)")
    month: int = Field(..., description="Report month (1-12)")
    total_spent: float = Field(..., description="Grand total spent in the month")
    breakdown_by_category: List[CategorySummary] = Field(default=[], description="Category spending breakdown")

    model_config = ConfigDict(from_attributes=True)


class BudgetAlert(BaseModel):
    """Budget alert status for a category in a month."""
    category: str = Field(..., description="Category name")
    limit: float = Field(..., description="Monthly spending limit")
    spent: float = Field(..., description="Current total spending in category")
    status: str = Field(..., description="Status: OK, WARNING (>=80%), or EXCEEDED (>100%)")

    model_config = ConfigDict(from_attributes=True)


# Recurring Expense Schemas
class RecurringExpenseBase(BaseModel):
    """Base schema for recurring subscription or bill rule."""
    title: str = Field(..., min_length=1, max_length=255, description="Subscription or bill title (e.g. Netflix, Internet)")
    amount: float = Field(..., gt=0.0, description="Recurring bill amount")
    currency: Optional[str] = Field(default="LKR", min_length=3, max_length=3, description="Currency code")
    category_id: int = Field(..., gt=0, description="Category ID")
    frequency: str = Field(..., pattern=r"^(DAILY|WEEKLY|MONTHLY|YEARLY)$", description="Frequency: DAILY, WEEKLY, MONTHLY, YEARLY")
    start_date: Optional[date] = Field(default=None, description="Start date of recurring commitment")
    auto_log: Optional[bool] = Field(default=True, description="Automatically log expense when due")


class RecurringExpenseCreate(RecurringExpenseBase):
    """Schema for registering a new recurring rule."""
    pass


class RecurringExpenseResponse(RecurringExpenseBase):
    """Response schema for recurring subscription entity."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    start_date: date
    next_due_date: date
    is_active: bool
    currency: str
    auto_log: bool
    category: Optional[CategoryResponse] = None
