"""
SQLAlchemy 2.0 ORM Models for Expense Tracker Database Schema.
Defines tables for User, Category, Expense, Budget, and RecurringExpense.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import (
    String,
    Integer,
    Numeric,
    Date,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
    and_,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.connection import Base


class User(Base):
    """User account model for JWT authentication & multi-tenant isolation."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    refresh_token_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    api_key_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Relationships
    categories: Mapped[List["Category"]] = relationship(
        "Category", back_populates="user", cascade="all, delete-orphan"
    )
    expenses: Mapped[List["Expense"]] = relationship(
        "Expense", back_populates="user", cascade="all, delete-orphan"
    )
    budgets: Mapped[List["Budget"]] = relationship(
        "Budget", back_populates="user", cascade="all, delete-orphan"
    )
    recurring_expenses: Mapped[List["RecurringExpense"]] = relationship(
        "RecurringExpense", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}')>"


class Category(Base):
    """Expense Category entity representing grouping of expenses."""
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="categories")
    expenses: Mapped[List["Expense"]] = relationship(
        "Expense", back_populates="category", cascade="all, delete-orphan"
    )
    budgets: Mapped[List["Budget"]] = relationship(
        "Budget", back_populates="category", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}')>"


class Expense(Base):
    """Expense transaction record."""
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="LKR", nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    category: Mapped["Category"] = relationship("Category", back_populates="expenses")
    user: Mapped["User"] = relationship("User", back_populates="expenses")

    def __repr__(self) -> str:
        return f"<Expense(id={self.id}, amount={self.amount}, description='{self.description}')>"


class Budget(Base):
    """Monthly Category Budget Limit."""
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    monthly_limit: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    category: Mapped["Category"] = relationship("Category", back_populates="budgets")
    user: Mapped["User"] = relationship("User", back_populates="budgets")

    def __repr__(self) -> str:
        return f"<Budget(category_id={self.category_id}, limit={self.monthly_limit}, month={self.month}/{self.year})>"


class RecurringExpense(Base):
    """Recurring expense subscription and commitment schedule."""
    __tablename__ = "recurring_expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="LKR", nullable=False)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), default="MONTHLY", nullable=False)  # DAILY, WEEKLY, MONTHLY, YEARLY
    start_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    next_due_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_log: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    category: Mapped["Category"] = relationship("Category")
    user: Mapped["User"] = relationship("User", back_populates="recurring_expenses")

    def __repr__(self) -> str:
        return f"<RecurringExpense(id={self.id}, title='{self.title}', amount={self.amount}, freq='{self.frequency}')>"
