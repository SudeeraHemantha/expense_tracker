"""
Analytics Service logic for monthly spending aggregation and budget alerts scoped per user.
"""

from calendar import monthrange
from datetime import date
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_

from database.models import Expense, Category, Budget
from schemas.expense_schemas import MonthlySpendingReport, CategorySummary, BudgetAlert
from services.expense_service import ExpenseService
from config.settings import settings


class AnalyticsService:
    """Service providing monthly spending reports and budget alert tracking for users."""

    @staticmethod
    def get_monthly_spending_report(
        db: Session, year: int, month: int, user_id: int
    ) -> MonthlySpendingReport:
        """Calculate monthly total spending and per-category breakdown for a user."""
        start_date = date(year, month, 1)
        end_day = monthrange(year, month)[1]
        end_date = date(year, month, end_day)

        stmt = (
            select(
                Category.name,
                func.sum(Expense.amount).label("total_spent")
            )
            .join(Expense, Category.id == Expense.category_id)
            .where(
                and_(
                    Expense.user_id == user_id,
                    Expense.expense_date >= start_date,
                    Expense.expense_date <= end_date
                )
            )
            .group_by(Category.id, Category.name)
            .order_by(func.sum(Expense.amount).desc())
        )

        results = db.execute(stmt).all()
        grand_total = float(sum(row.total_spent for row in results)) if results else 0.0

        breakdown: List[CategorySummary] = []
        for row in results:
            cat_spent = float(row.total_spent)
            percentage = (cat_spent / grand_total * 100.0) if grand_total > 0 else 0.0
            breakdown.append(
                CategorySummary(
                    name=row.name,
                    total_spent=round(cat_spent, 2),
                    percentage=round(percentage, 2)
                )
            )

        return MonthlySpendingReport(
            year=year,
            month=month,
            total_spent=round(grand_total, 2),
            breakdown_by_category=breakdown
        )

    @staticmethod
    def check_budget_status(
        db: Session, year: int, month: int, user_id: int
    ) -> List[BudgetAlert]:
        """Check spending against monthly budget limits for a user."""
        budgets = ExpenseService.get_budgets_by_period(db, year, month, user_id=user_id)
        if not budgets:
            return []

        report = AnalyticsService.get_monthly_spending_report(db, year, month, user_id=user_id)
        spent_map = {item.name: item.total_spent for item in report.breakdown_by_category}

        alerts: List[BudgetAlert] = []

        for b in budgets:
            cat_name = b.category.name if b.category else "Unknown"
            limit = float(b.monthly_limit)
            spent = spent_map.get(cat_name, 0.0)

            percentage = (spent / limit * 100.0) if limit > 0 else 0.0

            if percentage >= 100.0:
                alert_status = "EXCEEDED"
            elif percentage >= settings.ALERT_THRESHOLD_PERCENTAGE:
                alert_status = "WARNING"
            else:
                alert_status = "OK"

            alerts.append(
                BudgetAlert(
                    category=cat_name,
                    limit=round(limit, 2),
                    spent=round(spent, 2),
                    status=alert_status
                )
            )

        return alerts
