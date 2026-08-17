"""
Import Service for bulk bank statement CSV parsing and auto-categorized expense logging scoped per user.
"""

import io
import csv
from datetime import date, datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from services.expense_service import ExpenseService
from services.ai_expense_service import AIExpenseService
from schemas.expense_schemas import ExpenseCreate, CategoryCreate


class ImportService:
    """Service handling bulk bank statement CSV parsing and logging for authenticated user."""

    @staticmethod
    def _find_column_index(headers: List[str], keywords: List[str]) -> Optional[int]:
        """Find matching header column index by keywords."""
        for idx, h in enumerate(headers):
            h_clean = h.strip().lower()
            for kw in keywords:
                if kw in h_clean:
                    return idx
        return None

    @staticmethod
    def import_bank_csv(db: Session, file_bytes: bytes, user_id: int) -> Dict[str, Any]:
        """Parse bank statement CSV and bulk log auto-categorized expenses for the user."""
        if not file_bytes:
            raise ValueError("Uploaded CSV file buffer cannot be empty.")

        text_content = file_bytes.decode("utf-8", errors="replace")
        csv_io = io.StringIO(text_content)
        reader = csv.reader(csv_io)

        rows = list(reader)
        if not rows:
            raise ValueError("CSV file is empty.")

        headers = [str(col).strip() for col in rows[0]]
        data_rows = rows[1:]

        date_idx = ImportService._find_column_index(headers, ["date", "time", "trans"])
        amount_idx = ImportService._find_column_index(headers, ["amount", "debit", "price", "value", "spent"])
        desc_idx = ImportService._find_column_index(headers, ["description", "merchant", "narration", "payee", "memo", "details"])

        if date_idx is None:
            date_idx = 0
        if amount_idx is None:
            amount_idx = 1 if len(headers) > 1 else 0
        if desc_idx is None:
            desc_idx = 2 if len(headers) > 2 else 0

        db_categories = ExpenseService.get_categories(db, user_id=user_id)
        if not db_categories:
            default_cat = ExpenseService.create_category(db, CategoryCreate(name="General Expenses"), user_id=user_id)
            db_categories = [default_cat]

        category_names = [c.name for c in db_categories]
        category_map = {c.name.lower(): c.id for c in db_categories}
        default_cat_id = db_categories[0].id

        imported_count = 0
        skipped_count = 0

        for row in data_rows:
            if not row or len(row) <= max(date_idx, amount_idx, desc_idx):
                skipped_count += 1
                continue

            try:
                raw_date = row[date_idx].strip()
                parsed_date = date.today()
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
                    try:
                        parsed_date = datetime.strptime(raw_date, fmt).date()
                        break
                    except ValueError:
                        pass

                raw_amt = row[amount_idx].strip().replace(",", "").replace("$", "").replace("LKR", "").strip()
                amt = abs(float(raw_amt))
                if amt <= 0.0:
                    skipped_count += 1
                    continue

                desc = row[desc_idx].strip() or "Bank Statement Import"

                matched_cat_id = default_cat_id
                try:
                    parsed_ai = AIExpenseService.parse_natural_language(
                        text=f"Spent {amt} on {desc}",
                        available_categories=category_names,
                        ref_date=parsed_date
                    )
                    cat_name_low = parsed_ai.category_name.lower()
                    if cat_name_low in category_map:
                        matched_cat_id = category_map[cat_name_low]
                except Exception:
                    pass

                expense_in = ExpenseCreate(
                    amount=amt,
                    currency="LKR",
                    expense_date=parsed_date,
                    description=desc,
                    notes="Bulk imported from Bank Statement CSV",
                    category_id=matched_cat_id
                )
                ExpenseService.create_expense(db, expense_in, user_id=user_id)
                imported_count += 1
            except Exception:
                skipped_count += 1

        return {
            "total_rows": len(data_rows),
            "imported_count": imported_count,
            "skipped_count": skipped_count
        }
