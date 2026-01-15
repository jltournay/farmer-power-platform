"""Admin services for platform admin portal.

Provides service layer for admin CRUD operations:
- RegionService: Region management
- FactoryService: Factory management
- CollectionPointService: Collection point management
- FarmerService: Farmer management (admin context)

All services extend BaseService for bounded parallel execution.
"""

from bff.services.admin.collection_point_service import AdminCollectionPointService
from bff.services.admin.factory_service import AdminFactoryService
from bff.services.admin.farmer_service import AdminFarmerService
from bff.services.admin.region_service import AdminRegionService

__all__ = [
    "AdminCollectionPointService",
    "AdminFactoryService",
    "AdminFarmerService",
    "AdminRegionService",
]
