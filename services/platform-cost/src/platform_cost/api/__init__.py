"""API layer for platform cost service.

Provides:
- Health endpoints (FastAPI router)
- gRPC servicers (Story 13.4)
"""

from platform_cost.api.health import router as health_router

__all__ = ["health_router"]
