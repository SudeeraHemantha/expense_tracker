"""
Seed script to populate standard categories and sample financial records for testing and demonstration.
"""

import sys
from pathlib import Path
from datetime import date
from decimal import Decimal

# Ensure project root is in sys.path when running script directly
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.connection import init_db, SessionLocal
from services.expense_service import ExpenseService
from schemas.expense_schemas import CategoryCreate, ExpenseCreate, BudgetCreate


DEFAULT_CATEGORIES = [
    {"name": "Food & Groceries", "description": "Supermarket purchases, groceries, dining, and snacks"},
    {"name": "Transport", "description": "Fuel, taxi fares, public transport, and vehicle maintenance"},
    {"name": "Bills & Utilities", "description": "Electricity, water, internet, mobile, and recurring bills"},
    {"name": "Entertainment", "description": "Movies, streaming subscriptions, leisure, and hobbies"},
    {"name": "Education", "description": "Books, tuition fees, online courses, and learning materials"},
    {"name": "Health", "description": "Medical expenses, pharmacy, gym memberships, and healthcare"},
]


def seed_database() -> None:
    """Initialize database schema and insert default categories and sample records."""
    print("Initializing database tables...")
    init_db()

    db = SessionLocal()
    try:
        print("Seeding standard categories...")
        category_map = {}
        for cat_data in DEFAULT_CATEGORIES:
            cat_name = cat_data["name"]
            existing = ExpenseService.get_category_by_name(db, cat_name)
            if not existing:
                category = ExpenseService.create_category(
                    db,
                    CategoryCreate(name=cat_name, description=cat_data["description"])
                )
                print(f"  + Created Category: {cat_name} (ID: {category.id})")
                category_map[cat_name] = category
            else:
                print(f"  = Category exists: {cat_name} (ID: {existing.id})")
                category_map[cat_name] = existing

        # Seed sample expenses for testing/demo
        today = date.today()
        current_year = today.year
        current_month = today.month

        existing_expenses = ExpenseService.get_expenses(db, limit=5)
        if not existing_expenses:
            print("Seeding sample expenses and budgets...")
            sample_expenses = [
                {"cat": "Food & Groceries", "amount": 4500.00, "desc": "Weekly Supermarket Groceries", "day": 2},
                {"cat": "Food & Groceries", "amount": 1200.00, "desc": "Restaurant Dinner with Team", "day": 5},
                {"cat": "Transport", "amount": 3000.00, "desc": "Monthly Fuel Fill-up", "day": 3},
                {"cat": "Transport", "amount": 650.00, "desc": "Uber Taxi Ride", "day": 7},
                {"cat": "Bills & Utilities", "amount": 8500.00, "desc": "Electricity Bill Payment", "day": 1},
                {"cat": "Bills & Utilities", "amount": 2500.00, "desc": "Fiber Broadband Internet", "day": 4},
                {"cat": "Entertainment", "amount": 1500.00, "desc": "Movie Tickets & Snacks", "day": 8},
                {"cat": "Education", "amount": 5000.00, "desc": "Online Certification Course", "day": 6},
                {"cat": "Health", "amount": 1800.00, "desc": "Pharmacy Supplies & Vitamins", "day": 9},
            ]

            for exp in sample_expenses:
                cat_obj = category_map[exp["cat"]]
                exp_date = date(current_year, current_month, exp["day"])
                created_exp = ExpenseService.create_expense(
                    db,
                    ExpenseCreate(
                        amount=exp["amount"],
                        currency="LKR",
                        expense_date=exp_date,
                        description=exp["desc"],
                        category_id=cat_obj.id,
                        notes="Seeded sample transaction record"
                    )
                )
                print(f"  + Expense: [{created_exp.expense_date}] {created_exp.description} - LKR {created_exp.amount}")

            # Seed sample budgets
            sample_budgets = [
                {"cat": "Food & Groceries", "limit": 10000.00},
                {"cat": "Transport", "limit": 4000.00},
                {"cat": "Bills & Utilities", "limit": 12000.00},
                {"cat": "Entertainment", "limit": 2000.00},
            ]

            for b in sample_budgets:
                cat_obj = category_map[b["cat"]]
                created_budget = ExpenseService.create_budget(
                    db,
                    BudgetCreate(
                        category_id=cat_obj.id,
                        monthly_limit=b["limit"],
                        month=current_month,
                        year=current_year
                    )
                )
                print(f"  + Budget: {b['cat']} - Limit: LKR {created_budget.monthly_limit} ({current_year}-{current_month:02d})")

        print("Database seeding completed successfully.")

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
