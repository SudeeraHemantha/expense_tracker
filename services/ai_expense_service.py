"""
AI Natural Language Ingestion Service scoped per user.
"""

import os
import re
import json
from datetime import date, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session

from database.models import Expense, Category
from schemas.ai_schemas import ParsedExpenseResponse
from schemas.expense_schemas import ExpenseCreate
from services.expense_service import ExpenseService
from config.settings import settings


class AIExpenseService:
    """Service for parsing natural language text into structured transactions per user."""

    @staticmethod
    def parse_natural_language(
        text: str,
        available_categories: List[str],
        ref_date: Optional[date] = None
    ) -> ParsedExpenseResponse:
        """Parse natural language text into structured expense response."""
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty.")

        today = ref_date or date.today()
        text_lower = text.lower().strip()

        # 1. Amount Extraction
        amount_match = re.search(r"(?:rs\.?|lkr|\$|€|£)?\s*(\d+(?:\.\d{1,2})?)\s*(?:lkr|rs\.?|\$|€|£)?", text_lower)
        if not amount_match:
            raise ValueError("Could not extract a valid transaction amount from text.")
        extracted_amount = float(amount_match.group(1))

        # 2. Currency Detection
        currency = settings.DEFAULT_CURRENCY
        if "$" in text_lower or "usd" in text_lower:
            currency = "USD"
        elif "€" in text_lower or "eur" in text_lower:
            currency = "EUR"
        elif "£" in text_lower or "gbp" in text_lower:
            currency = "GBP"

        # 3. Relative Date Extraction
        target_date = today
        if "yesterday" in text_lower:
            target_date = today - timedelta(days=1)
        elif "day before yesterday" in text_lower:
            target_date = today - timedelta(days=2)
        elif "today" in text_lower:
            target_date = today
        else:
            days_ago_match = re.search(r"(\d+)\s*days?\s*ago", text_lower)
            if days_ago_match:
                days_cnt = int(days_ago_match.group(1))
                target_date = today - timedelta(days=days_cnt)

        # 4. Dynamic Category Matching
        best_category = available_categories[0] if available_categories else "General"
        max_score = 0

        keywords_map = {
            "groceries": ["grocery", "groceries", "supermarket", "food", "vegetable", "fruit", "milk", "bread", "keells", "cargills"],
            "transport": ["fuel", "petrol", "diesel", "taxi", "uber", "pickme", "bus", "train", "cab", "parking"],
            "bills": ["electricity", "water", "internet", "dialog", "mobitel", "wifi", "bill", "utility", "phone"],
            "entertainment": ["movie", "cinema", "netflix", "spotify", "game", "restaurant", "party", "pub"],
            "education": ["book", "course", "tuition", "school", "university", "fee", "stationery"],
            "health": ["doctor", "medicine", "pharmacy", "hospital", "clinic", "fitness", "gym"]
        }

        for cat in available_categories:
            cat_low = cat.lower()
            if cat_low in text_lower:
                best_category = cat
                break

            for key, kw_list in keywords_map.items():
                if key in cat_low or any(k in cat_low for k in kw_list):
                    for kw in kw_list:
                        if kw in text_lower:
                            best_category = cat
                            max_score += 1

        return ParsedExpenseResponse(
            amount=extracted_amount,
            currency=currency,
            category_name=best_category,
            expense_date=target_date,
            description=text.strip(),
            confidence_score=0.90 if max_score > 0 else 0.75
        )

    @staticmethod
    def parse_and_create_expense(db: Session, text: str, user_id: int) -> Expense:
        """Parse freeform text and log transaction into user's database."""
        db_categories = ExpenseService.get_categories(db, user_id=user_id)
        if not db_categories:
            raise ValueError("No categories available for user to map expense.")

        category_names = [c.name for c in db_categories]
        parsed = AIExpenseService.parse_natural_language(text, available_categories=category_names)

        category = next((c for c in db_categories if c.name == parsed.category_name), db_categories[0])

        expense_in = ExpenseCreate(
            amount=parsed.amount,
            currency=parsed.currency,
            expense_date=parsed.expense_date,
            description=parsed.description,
            notes=f"AI Parsed (Confidence: {parsed.confidence_score:.2f})",
            category_id=category.id
        )

        return ExpenseService.create_expense(db, expense_in, user_id=user_id)
