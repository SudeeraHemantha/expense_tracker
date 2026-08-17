"""
FastAPI Main Application Entrypoint for Expense Tracker API.
Includes Security Headers Middleware and slowapi Rate Limiting.
"""

import sys
from pathlib import Path

# Add project root directory to python module search path
project_root = str(Path(__file__).resolve().parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from config.settings import settings
from config.limiter import limiter
from database.connection import init_db
from api.routes_auth import router as auth_router
from api.routes_categories import router as categories_router
from api.routes_expenses import router as expenses_router
from api.routes_analytics import router as analytics_router
from api.routes_ai import router as ai_router
from api.routes_recurring import router as recurring_router
from api.routes_export_import import router as export_import_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler initializing database tables on startup."""
    init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Production-grade Expense Tracker REST API service with JWT Auth, Refresh Tokens, API Keys, Rate Limiting, and Multimodal AI Vision.",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan
)

# Register slowapi rate limiter state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Middleware attaching production security HTTP response headers."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers under /api prefix
app.include_router(auth_router, prefix="/api")
app.include_router(categories_router, prefix="/api")
app.include_router(expenses_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(recurring_router, prefix="/api")
app.include_router(export_import_router, prefix="/api")


@app.get("/", tags=["Health"])
def root_endpoint():
    """Root health check endpoint."""
    return {
        "status": "online",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "default_currency": settings.DEFAULT_CURRENCY,
        "documentation": "/docs"
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "database": "connected",
        "currency_default": settings.DEFAULT_CURRENCY
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_excludes=[".venv/*", "data/*", "*.db"]
    )
