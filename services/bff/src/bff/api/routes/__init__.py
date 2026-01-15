"""BFF API routes module.

Contains route handlers for:
- Health endpoints (health.py)
- Farmer endpoints (farmers.py)
- Admin endpoints (admin/)
"""

from bff.api.routes import admin, farmers, health

__all__ = ["admin", "farmers", "health"]
