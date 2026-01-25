"""Admin API routes for platform admin portal.

Provides CRUD endpoints for:
- Regions (AC1)
- Factories (AC2)
- Collection Points (AC3)
- Farmers (AC4)
- Grading Models (Story 9.6a)
- Knowledge Management (Story 9.9a)
- Platform Cost Monitoring (Story 9.10a)
- Source Configurations (Story 9.11b)

All routes require platform_admin role (AC5).
"""

from bff.api.routes.admin.collection_points import router as collection_points_router
from bff.api.routes.admin.factories import router as factories_router
from bff.api.routes.admin.farmers import router as farmers_router
from bff.api.routes.admin.grading_models import router as grading_models_router
from bff.api.routes.admin.knowledge import router as knowledge_router
from bff.api.routes.admin.platform_cost import router as platform_cost_router
from bff.api.routes.admin.regions import router as regions_router
from bff.api.routes.admin.source_configs import router as source_configs_router
from fastapi import APIRouter

# Combined admin router
router = APIRouter(prefix="/api/admin", tags=["admin"])

# Include all sub-routers
router.include_router(regions_router)
router.include_router(factories_router)
router.include_router(collection_points_router)
router.include_router(farmers_router)
router.include_router(grading_models_router)
router.include_router(knowledge_router)
router.include_router(platform_cost_router)
router.include_router(source_configs_router)

__all__ = ["router"]
