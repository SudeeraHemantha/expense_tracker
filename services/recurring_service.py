"""
Recurring Expenses & Subscription Management Service logic scoped per user.
"""

from datetime import date, timedelta
from typing import List, Optional
from decimal import Decimal
from calendar import monthrange
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from database.models import RecurringExpense, Category, Expense
from schemas.expense_schemas import RecurringExpenseCreate, ExpenseCreate
from services.expense_service import ExpenseService
from config.settings import settings


class RecurringExpenseService:
    """Service handling recurring subscriptions, frequency advancements, and auto-logging per user."""

    @staticmethod
    def calculate_next_due_date(current_due: date, frequency: str) -> date:
        """Calculate the next due date based on frequency (DAILY, WEEKLY, MONTHLY, YEARLY)."""
        freq_upper = frequency.upper()

        if freq_upper == "DAILY":
            return current_due + timedelta(days=1)
        elif freq_upper == "WEEKLY":
            return current_due + timedelta(weeks=1)
        elif freq_upper == "MONTHLY":
            month = current_due.month % 12 + 1
            year = current_due.year + (current_due.month // 12)
            day = min(current_due.day, monthrange(year, month)[1])
            return date(year, month, day)
        elif freq_upper == "YEARLY":
            try:
                return date(current_due.year + 1, current_due.month, current_due.day)
            except ValueError:
                return date(current_due.year + 1, current_due.month, 28)
        else:
            return current_due + timedelta(days=30)

    @staticmethod
    def create_recurring(db: Session, recurring_in: RecurringExpenseCreate, user_id: int) -> RecurringExpense:
        """Register a new recurring expense rule for the user."""
        category = ExpenseService.get_category_by_id(db, recurring_in.category_id, user_id=user_id)
        if not category:
            raise ValueError(f"Category ID {recurring_in.category_id} not found.")

        st_date = recurring_in.start_date or date.today()
        rec_currency = recurring_in.currency or settings.DEFAULT_CURRENCY

        db_recurring = RecurringExpense(
            title=recurring_in.title,
            amount=Decimal(str(recurring_in.amount)),
            currency=rec_currency,
            category_id=recurring_in.category_id,
            frequency=recurring_in.frequency.upper(),
            start_date=st_date,
            next_due_date=st_date,
            is_active=True,
            auto_log=recurring_in.auto_log if recurring_in.auto_log is not None else True,
            user_id=user_id
        )

        db.add(db_recurring)
        db.commit()
        db.refresh(db_recurring)
        return db_recurring

    @staticmethod
    def get_recurring_expenses(
        db: Session,
        user_id: int,
        is_active: Optional[bool] = True
    ) -> List[RecurringExpense]:
        """Fetch recurring rules for the user optionally filtered by active status."""
        stmt = select(RecurringExpense).where(RecurringExpense.user_id == user_id)
        if is_active is not None:
            stmt = stmt.where(RecurringExpense.is_active == is_active)
        stmt = stmt.order_by(RecurringExpense.next_due_date.asc())
        return list(db.scalars(stmt).all())

    @staticmethod
    def get_recurring_by_id(db: Session, recurring_id: int, user_id: int) -> Optional[RecurringExpense]:
        """Fetch recurring rule by ID for the user."""
        stmt = select(RecurringExpense).where(RecurringExpense.id == recurring_id, RecurringExpense.user_id == user_id)
        return db.scalar(stmt)

    @staticmethod
    def delete_recurring(db: Session, recurring_id: int, user_id: int) -> bool:
        """Delete a recurring expense rule for the user."""
        rule = RecurringExpenseService.get_recurring_by_id(db, recurring_id, user_id=user_id)
        if not rule:
            return False

        db.delete(rule)
        db.commit()
        return True

    @staticmethod
    def process_due_recurring_expenses(
        db: Session,
        user_id: int,
        target_date: Optional[date] = None
    ) -> List[Expense]:
        """Check active recurring items for the user where next_due_date <= target_date, auto-log expense, advance next_due_date."""
        cutoff_date = target_date or date.today()

        stmt = (
            select(RecurringExpense)
            .where(
                and_(
                    RecurringExpense.user_id == user_id,
                    RecurringExpense.is_active == True,
                    RecurringExpense.next_due_date <= cutoff_date
                )
            )
        )
        due_rules = list(db.scalars(stmt).all())
        created_expenses: List[Expense] = []

        for rule in due_rules:
            if rule.auto_log:
                expense_in = ExpenseCreate(
                    amount=float(rule.amount),
                    currency=rule.currency,
                    expense_date=rule.next_due_date,
                    description=f"Recurring: {rule.title}",
                    notes=f"Auto-logged subscription commitment (Frequency: {rule.frequency})",
                    category_id=rule.category_id
                )
                exp = ExpenseService.create_expense(db, expense_in, user_id=user_id)
                created_expenses.append(exp)

            rule.next_due_date = RecurringExpenseService.calculate_next_due_date(
                rule.next_due_date,
                rule.frequency
            )
            db.commit()
            db.refresh(rule)

        return created_expenses
