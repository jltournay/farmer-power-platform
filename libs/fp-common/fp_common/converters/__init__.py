"""Proto-to-Pydantic and dict-to-Pydantic converters for Farmer Power Platform.

This module provides centralized conversion functions:
- Plantation: Protocol Buffer messages to Pydantic models
- Collection: MongoDB dicts to Pydantic models

Usage:
    from fp_common.converters import farmer_from_proto, factory_from_proto
    from fp_common.converters import document_from_dict, search_result_from_dict

    # Convert gRPC response to Pydantic model
    farmer = farmer_from_proto(grpc_response.farmer)
    factory = factory_from_proto(grpc_response.factory)

    # Convert MongoDB document to Pydantic model
    doc = document_from_dict(mongo_doc)
    result = search_result_from_dict(search_doc)
"""

from fp_common.converters.collection_converters import (
    document_from_dict,
    search_result_from_dict,
)
from fp_common.converters.plantation_converters import (
    collection_point_from_proto,
    factory_from_proto,
    farmer_from_proto,
    farmer_summary_from_proto,
    region_from_proto,
)

__all__ = [
    "collection_point_from_proto",
    "document_from_dict",
    "factory_from_proto",
    "farmer_from_proto",
    "farmer_summary_from_proto",
    "region_from_proto",
    "search_result_from_dict",
]
