"""Proto-to-Pydantic converters for Farmer Power Platform.

This module provides centralized conversion functions from Protocol Buffer
messages to Pydantic models, eliminating duplicate _to_dict() methods
across services and MCP clients.

Usage:
    from fp_common.converters import farmer_from_proto, factory_from_proto

    # Convert gRPC response to Pydantic model
    farmer = farmer_from_proto(grpc_response.farmer)
    factory = factory_from_proto(grpc_response.factory)
"""

from fp_common.converters.plantation_converters import (
    collection_point_from_proto,
    factory_from_proto,
    farmer_from_proto,
    farmer_summary_from_proto,
    region_from_proto,
)

__all__ = [
    "collection_point_from_proto",
    "factory_from_proto",
    "farmer_from_proto",
    "farmer_summary_from_proto",
    "region_from_proto",
]
