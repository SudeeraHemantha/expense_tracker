# Expense Tracker Backend & Streamlit Dashboard

Production-grade, modular Expense Tracker REST API and Streamlit UI built with **Python**, **FastAPI**, **SQLAlchemy 2.0**, **SQLite**, **Pydantic v2**, **Streamlit**, **JWT Auth & Refresh Tokens**, **Personal API Keys**, **slowapi Rate Limiting**, and an **AI Multimodal Vision & Data Processing Engine**.

---

## Key Features

- **JWT Auth & Refresh Tokens**: User registration (`POST /api/auth/register`), login (`POST /api/auth/login`), 30-minute access tokens, 30-day refresh tokens (`POST /api/auth/refresh`), and strict `user_id` multi-tenant data isolation.
- **Personal API Key Authentication**: Generate persistent, revocable API keys (`sk_live_...`) for rapid automated expense logging using `X-API-Key` HTTP headers without browser logins.
- **Rate Limiting & Security Hardening**: `slowapi` rate limiting (`5 req/min` for `/login`, `20 req/min` for `/ai/*` and `/export/*`) and security HTTP response headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`).
- **Streamlit Persistent Auth & Dashboard**: Browser cookie refresh token persistence, silent auto-login startup, Plotly analytics charts, budget progress bars, subscription management, camera receipt scanning, and "⚙️ Settings & Security" tab.
- **Monthly CSV & Formatted Excel Export**: Export monthly transaction reports as `.csv` files or multi-sheet formatted `.xlsx` workbooks (Transactions & Monthly Summary sheets).
- **Bulk Bank Statement CSV Import**: Upload generic bank statement CSVs with header auto-detection and AI-powered category classification.
- **Recurring Expenses & Subscriptions**: Track fixed monthly bills and subscriptions (Netflix, Rent, Internet) with automated execution when due (`DAILY`, `WEEKLY`, `MONTHLY`, `YEARLY`).
- **AI Vision Receipt OCR Scanner**: Upload or capture a photo of a store receipt (JPEG, PNG, WEBP) to extract merchant name, total amount, currency, transaction date, line items, and record transactions automatically.
- **AI Natural Language Expense Parsing**: Ingest freeform text (e.g., *"Spent 3500 LKR on groceries and vegetables yesterday"*) to extract amounts, currencies, relative dates (*"today"*, *"yesterday"*, *"last Friday"*), and map directly to database categories.
- **Category Management**: Create and retrieve expense categories per user with unique constraints.
- **Expense Logging & Filtering**: Log financial transactions manually or via AI, filter by date ranges and categories.
- **Monthly Spending Reports**: Compute monthly total spending, per-category breakdown, and percentage share.
- **Budget Monitoring & Threshold Alerts**: Set monthly category budget limits and track alert levels (`OK`, `WARNING` at >=80%, `EXCEEDED` at >=100%).
- **Automated Seeding & Testing**: Standalone database seed script and comprehensive `pytest` test suite with in-memory SQLite isolation.

---

## Project Structure

```
expense_tracker/
├── config/
│   ├── __init__.py
│   ├── limiter.py           # Shared slowapi rate limiter instance
│   └── settings.py          # App configuration & Pydantic BaseSettings
├── database/
│   ├── __init__.py
│   ├── connection.py        # SQLite engine, DeclarativeBase & get_db dependency
│   └── models.py            # ORM models (User, Category, Expense, Budget, RecurringExpense)
├── schemas/
│   ├── __init__.py
│   ├── expense_schemas.py   # Pydantic v2 validation DTOs, Analytics & Recurring models
│   ├── ai_schemas.py        # Natural Language & AI Vision parsing schemas
│   └── auth_schemas.py      # JWT auth, token refresh, and personal API key DTOs
├── services/
│   ├── __init__.py
│   ├── auth_service.py      # Password hashing, JWT access/refresh tokens, API keys & get_current_user
│   ├── expense_service.py   # CRUD business logic for categories, expenses, and budgets
│   ├── analytics_service.py # Aggregation engine for reports and budget alerts
│   ├── ai_expense_service.py# Natural language NLP & GenAI parsing service
│   ├── vision_expense_service.py # Multimodal AI Vision receipt OCR parsing service
│   ├── recurring_service.py # Subscriptions automation & due expense logging service
│   ├── export_service.py    # CSV and multi-sheet Excel report exporter service
│   └── import_service.py    # Bulk bank statement CSV parser and classifier service
├── api/
│   ├── __init__.py
│   ├── routes_auth.py       # REST endpoints for registration, login, refresh, api-key, profile
│   ├── routes_categories.py # REST endpoints for categories
│   ├── routes_expenses.py   # REST endpoints for expenses logging & filtering
│   ├── routes_analytics.py  # REST endpoints for monthly reports & budget alerts
│   ├── routes_ai.py         # REST endpoints for AI text & receipt image parsing
│   ├── routes_recurring.py  # REST endpoints for recurring subscriptions
│   └── routes_export_import.py # REST endpoints for CSV/Excel export & bank CSV import
├── frontend/
│   ├── __init__.py
│   └── app.py               # Streamlit interactive UI dashboard with cookie persistence
├── data/
│   └── .gitkeep             # Storage directory for SQLite expenses.db
├── scripts/
│   ├── __init__.py
│   └── seed_data.py         # Seed script populating categories & sample data
├── tests/
│   ├── __init__.py
│   ├── test_security_auth.py# Token refresh, API key auth & rate limiting test suite
│   ├── test_auth.py         # Auth & multi-tenant data isolation test suite
│   ├── test_expenses.py     # Expense & analytics unit/integration test suite
│   ├── test_ai_parsing.py   # AI Natural language parsing test suite
│   ├── test_vision_parsing.py # AI Vision receipt scanning test suite
│   ├── test_recurring.py    # Recurring expenses unit & integration test suite
│   └── test_export_import.py# Export & Import unit & integration test suite
├── .env.example             # Template for environment configuration
├── .gitignore                # Git version control ignore rules
├── requirements.txt         # Project dependencies
├── main.py                  # FastAPI application entrypoint with security headers
└── README.md                # Project documentation
```

---

## Environment Variables (.env)

Copy `.env.example` to `.env` in the root directory:

```bash
cp .env.example .env
```

| Variable | Description | Default |
| :--- | :--- | :--- |
| `SECRET_KEY` | Secret key for signing JWT tokens | `expense_tracker_production_secret_key...` |
| `ALGORITHM` | Algorithm for JWT signatures | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access Token expiration (minutes) | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh Token expiration (days) | `30` |
| `DB_PATH` | SQLite database connection string | `sqlite:///./data/expenses.db` |
| `DEFAULT_CURRENCY` | Default currency code | `LKR` |
| `ALERT_THRESHOLD_PERCENTAGE` | Budget warning threshold (%) | `80.0` |

---

## Local Setup & Installation

### 1. Prerequisites

Ensure Python 3.10+ is installed on your system.

### 2. Environment Setup & Dependencies

Create and activate a Python virtual environment:

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

Install required dependencies:

```bash
pip install -r requirements.txt
```

---

## Running the Application

### 1. Database Seeding

Run the seed script to create database tables and insert sample records:

```bash
python scripts/seed_data.py
```

### 2. Launch FastAPI Backend Server

Start the Uvicorn ASGI server:

```bash
python main.py
```

Or using Uvicorn directly:

```bash
uvicorn main:app --reload --port 8000
```

The API server will be available at: `http://127.0.0.1:8000`

### 3. Launch Streamlit Frontend Dashboard

In a new terminal window (with virtualenv activated), start the Streamlit frontend:

```bash
streamlit run frontend/app.py
```

The interactive dashboard will open automatically at: `http://localhost:8501`

---

## API Documentation & Interactive UI

FastAPI generates interactive Swagger OpenAPI documentation:

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc UI**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### Summary of Key API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/auth/register` | Register a new user account with hashed password and auto-seeded categories |
| `POST` | `/api/auth/login` | Authenticate credentials (Rate limit: 5/min) and issue access & 30-day refresh tokens |
| `POST` | `/api/auth/refresh` | Issue new 30-minute access token using valid 30-day refresh token |
| `POST` | `/api/auth/api-key` | Generate or regenerate persistent, revocable personal API Key (`sk_live_...`) |
| `GET` | `/api/auth/me` | Retrieve profile information for the authenticated user |
| `GET` | `/api/export/csv` | Download CSV transaction report for a selected year and month (Rate limit: 20/min) |
| `GET` | `/api/export/excel` | Download formatted Excel (.xlsx) workbook (Rate limit: 20/min) |
| `POST` | `/api/import/csv` | Upload bank statement CSV for auto-categorized bulk transaction ingestion |
| `POST` | `/api/recurring` | Register a new recurring subscription or bill commitment |
| `GET` | `/api/recurring` | List active recurring subscriptions and upcoming due dates |
| `POST` | `/api/recurring/process` | Trigger auto-logging for due recurring transactions and advance next due dates |
| `DELETE` | `/api/recurring/{id}` | Delete a recurring subscription rule |
| `POST` | `/api/ai/parse-receipt` | Upload a receipt image file (JPEG, PNG, WEBP) for OCR vision parsing (Rate limit: 20/min) |
| `POST` | `/api/ai/parse-expense` | Parse freeform text (*"Spent 3500 LKR on groceries yesterday"*) (Rate limit: 20/min) |
| `GET` | `/api/categories` | Retrieve all registered categories for authenticated user |
| `POST` | `/api/categories` | Create a new category for authenticated user |
| `GET` | `/api/expenses` | Retrieve filtered expenses (`start_date`, `end_date`, `category_id`, `skip`, `limit`) |
| `POST` | `/api/expenses` | Log a new expense record |
| `GET` | `/api/expenses/{id}` | Get single expense details |
| `DELETE` | `/api/expenses/{id}` | Delete an expense record |
| `GET` | `/api/analytics/monthly` | Get monthly spending report (`year`, `month` or `month_year=YYYY-MM`) |
| `GET` | `/api/analytics/budgets` | Get monthly budget alerts status (`OK`, `WARNING`, `EXCEEDED`) |
| `POST` | `/api/analytics/budgets` | Set or update a monthly category budget limit |
| `GET` | `/health` | Application health check endpoint |

---

## Running Automated Tests

Run the full unit and integration test suite using `pytest`:

```bash
python -m pytest tests/ -v
```

All tests execute against an isolated in-memory SQLite database (`sqlite:///:memory:`).
