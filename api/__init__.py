"""
API Routers Package.
"""

from api.routes_auth import router as auth_router
from api.routes_categories import router as categories_router
from api.routes_expenses import router as expenses_router
from api.routes_analytics import router as analytics_router
from api.routes_ai import router as ai_router
from api.routes_recurring import router as recurring_router
from api.routes_export_import import router as export_import_router

__all__ = [
    "auth_router",
    "categories_router",
    "expenses_router",
    "analytics_router",
    "ai_router",
    "recurring_router",
    "export_import_router",
]
