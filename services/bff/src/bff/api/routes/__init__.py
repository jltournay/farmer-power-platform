"""BFF API routes module.

Contains route handlers for:
- Health endpoints (health.py)
- Farmer endpoints (farmers.py)
"""

from bff.api.routes import farmers, health

__all__ = ["farmers", "health"]
