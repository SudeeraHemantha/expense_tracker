"""
CRUD Service logic for Expense Tracker (Categories, Expenses, Budgets) scoped per authenticated user.
"""

from datetime import date
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from database.models import Category, Expense, Budget
from schemas.expense_schemas import CategoryCreate, ExpenseCreate, BudgetCreate
from config.settings import settings


class ExpenseService:
    """Service class encapsulating DB queries and business logic for multi-tenant data."""

    # --- Category Operations ---
    @staticmethod
    def get_categories(db: Session, user_id: int) -> List[Category]:
        """Fetch all categories for the authenticated user."""
        stmt = select(Category).where(Category.user_id == user_id).order_by(Category.name.asc())
        return list(db.scalars(stmt).all())

    @staticmethod
    def get_category_by_id(db: Session, category_id: int, user_id: int) -> Optional[Category]:
        """Fetch a specific category by ID for the user."""
        stmt = select(Category).where(Category.id == category_id, Category.user_id == user_id)
        return db.scalar(stmt)

    @staticmethod
    def get_category_by_name(db: Session, name: str, user_id: int) -> Optional[Category]:
        """Fetch a category by name for the user."""
        stmt = select(Category).where(Category.name == name.strip(), Category.user_id == user_id)
        return db.scalar(stmt)

    @staticmethod
    def create_category(db: Session, category_in: CategoryCreate, user_id: int) -> Category:
        """
        Create a new expense category for the user.

        Raises:
            ValueError: If category with same name already exists for this user.
        """
        existing = ExpenseService.get_category_by_name(db, category_in.name, user_id)
        if existing:
            raise ValueError(f"Category '{category_in.name}' already exists.")

        db_category = Category(
            name=category_in.name.strip(),
            description=category_in.description.strip() if category_in.description else None,
            user_id=user_id
        )
        db.add(db_category)
        db.commit()
        db.refresh(db_category)
        return db_category

    # --- Expense Operations ---
    @staticmethod
    def create_expense(db: Session, expense_in: ExpenseCreate, user_id: int) -> Expense:
        """
        Create a new expense entry for the user.

        Raises:
            ValueError: If category_id does not exist for this user.
        """
        category = ExpenseService.get_category_by_id(db, expense_in.category_id, user_id)
        if not category:
            raise ValueError(f"Category ID {expense_in.category_id} not found.")

        exp_date = expense_in.expense_date or date.today()
        currency = expense_in.currency or settings.DEFAULT_CURRENCY

        db_expense = Expense(
            amount=Decimal(str(expense_in.amount)),
            currency=currency.upper(),
            expense_date=exp_date,
            description=expense_in.description.strip(),
            notes=expense_in.notes.strip() if expense_in.notes else None,
            category_id=expense_in.category_id,
            user_id=user_id
        )
        db.add(db_expense)
        db.commit()
        db.refresh(db_expense)
        return db_expense

    @staticmethod
    def get_expenses(
        db: Session,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Expense]:
        """Fetch filtered expenses for the user with pagination."""
        stmt = select(Expense).where(Expense.user_id == user_id)

        if start_date:
            stmt = stmt.where(Expense.expense_date >= start_date)
        if end_date:
            stmt = stmt.where(Expense.expense_date <= end_date)
        if category_id:
            stmt = stmt.where(Expense.category_id == category_id)

        stmt = stmt.order_by(Expense.expense_date.desc(), Expense.id.desc()).offset(skip).limit(limit)
        return list(db.scalars(stmt).all())

    @staticmethod
    def get_expense_by_id(db: Session, expense_id: int, user_id: int) -> Optional[Expense]:
        """Fetch single expense by ID for the user."""
        stmt = select(Expense).where(Expense.id == expense_id, Expense.user_id == user_id)
        return db.scalar(stmt)

    @staticmethod
    def delete_expense(db: Session, expense_id: int, user_id: int) -> bool:
        """Delete expense by ID for the user."""
        expense = ExpenseService.get_expense_by_id(db, expense_id, user_id)
        if not expense:
            return False

        db.delete(expense)
        db.commit()
        return True

    # --- Budget Operations ---
    @staticmethod
    def create_budget(db: Session, budget_in: BudgetCreate, user_id: int) -> Budget:
        """Create or update monthly budget threshold for the user."""
        category = ExpenseService.get_category_by_id(db, budget_in.category_id, user_id)
        if not category:
            raise ValueError(f"Category ID {budget_in.category_id} not found.")

        existing = ExpenseService.get_budget_by_category_and_period(
            db, budget_in.category_id, budget_in.month, budget_in.year, user_id
        )

        if existing:
            existing.monthly_limit = Decimal(str(budget_in.monthly_limit))
            db.commit()
            db.refresh(existing)
            return existing

        db_budget = Budget(
            category_id=budget_in.category_id,
            monthly_limit=Decimal(str(budget_in.monthly_limit)),
            month=budget_in.month,
            year=budget_in.year,
            user_id=user_id
        )
        db.add(db_budget)
        db.commit()
        db.refresh(db_budget)
        return db_budget

    @staticmethod
    def get_budget_by_category_and_period(
        db: Session, category_id: int, month: int, year: int, user_id: int
    ) -> Optional[Budget]:
        """Fetch budget threshold for specific category and month for the user."""
        stmt = select(Budget).where(
            and_(
                Budget.category_id == category_id,
                Budget.month == month,
                Budget.year == year,
                Budget.user_id == user_id
            )
        )
        return db.scalar(stmt)

    @staticmethod
    def get_budgets_by_period(db: Session, year: int, month: int, user_id: int) -> List[Budget]:
        """Fetch all category budget limits for a given year and month for the user."""
        stmt = select(Budget).where(
            and_(
                Budget.year == year,
                Budget.month == month,
                Budget.user_id == user_id
            )
        )
        return list(db.scalars(stmt).all())
