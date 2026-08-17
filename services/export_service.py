"""
Export Service for generating CSV and formatted Excel (.xlsx) financial reports scoped per user.
"""

import io
import csv
from datetime import date
from typing import Tuple
import pandas as pd
from sqlalchemy.orm import Session

from services.expense_service import ExpenseService
from services.analytics_service import AnalyticsService


class ExportService:
    """Service handling CSV text generation and multi-sheet Excel workbook export for authenticated user."""

    @staticmethod
    def export_monthly_csv(db: Session, year: int, month: int, user_id: int) -> str:
        """Generate CSV text representation of all transactions in a selected month for the user."""
        start_date = date(year, month, 1)
        end_day = 31 if month in [1, 3, 5, 7, 8, 10, 12] else (29 if (month == 2 and year % 4 == 0) else (28 if month == 2 else 30))
        end_date = date(year, month, end_day)

        expenses = ExpenseService.get_expenses(db, user_id=user_id, start_date=start_date, end_date=end_date, limit=10000)

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["ID", "Date", "Category", "Amount", "Currency", "Description", "Notes"])

        for exp in expenses:
            cat_name = exp.category.name if exp.category else "Uncategorized"
            writer.writerow([
                exp.id,
                exp.expense_date.isoformat(),
                cat_name,
                f"{exp.amount:.2f}",
                exp.currency,
                exp.description,
                exp.notes or ""
            ])

        return output.getvalue()

    @staticmethod
    def export_monthly_excel(db: Session, year: int, month: int, user_id: int) -> bytes:
        """Generate formatted Excel (.xlsx) workbook bytes for the user."""
        start_date = date(year, month, 1)
        end_day = 31 if month in [1, 3, 5, 7, 8, 10, 12] else (29 if (month == 2 and year % 4 == 0) else (28 if month == 2 else 30))
        end_date = date(year, month, end_day)

        expenses = ExpenseService.get_expenses(db, user_id=user_id, start_date=start_date, end_date=end_date, limit=10000)
        report = AnalyticsService.get_monthly_spending_report(db, year, month, user_id=user_id)

        tx_data = []
        for exp in expenses:
            cat_name = exp.category.name if exp.category else "Uncategorized"
            tx_data.append({
                "Transaction ID": exp.id,
                "Date": exp.expense_date.isoformat(),
                "Category": cat_name,
                "Amount": float(exp.amount),
                "Currency": exp.currency,
                "Description": exp.description,
                "Notes": exp.notes or ""
            })

        df_transactions = pd.DataFrame(tx_data) if tx_data else pd.DataFrame(columns=["Transaction ID", "Date", "Category", "Amount", "Currency", "Description", "Notes"])

        summary_meta = [
            {"Metric": "Report Period", "Value": f"{year}-{month:02d}"},
            {"Metric": "Total Spent", "Value": report.total_spent},
            {"Metric": "Active Categories Count", "Value": len(report.breakdown_by_category)}
        ]
        df_meta = pd.DataFrame(summary_meta)

        breakdown_data = [
            {"Category Name": c.name, "Total Spent": c.total_spent, "Percentage Share (%)": c.percentage}
            for c in report.breakdown_by_category
        ]
        df_breakdown = pd.DataFrame(breakdown_data) if breakdown_data else pd.DataFrame(columns=["Category Name", "Total Spent", "Percentage Share (%)"])

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_transactions.to_excel(writer, sheet_name="Transactions", index=False)
            df_meta.to_excel(writer, sheet_name="Summary", index=False, startrow=0)
            df_breakdown.to_excel(writer, sheet_name="Summary", index=False, startrow=len(df_meta) + 3)

        buffer.seek(0)
        return buffer.getvalue()
