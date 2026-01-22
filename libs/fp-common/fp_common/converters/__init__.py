"""Proto-to-Pydantic and dict-to-Pydantic converters for Farmer Power Platform.

This module provides centralized conversion functions:
- Plantation: Protocol Buffer messages to Pydantic models
- Collection: Protocol Buffer messages and MongoDB dicts to Pydantic models
- Cost: Protocol Buffer messages to Pydantic models (Story 13.6)

Usage:
    from fp_common.converters import farmer_from_proto, factory_from_proto
    from fp_common.converters import document_from_proto, document_from_dict
    from fp_common.converters import cost_summary_from_proto, budget_status_from_proto

    # Convert gRPC response to Pydantic model
    farmer = farmer_from_proto(grpc_response.farmer)
    factory = factory_from_proto(grpc_response.factory)
    doc = document_from_proto(grpc_response)  # Story 0.6.13
    cost_summary = cost_summary_from_proto(grpc_response)  # Story 13.6

    # Convert MongoDB document to Pydantic model
    doc = document_from_dict(mongo_doc)
    result = search_result_from_dict(search_doc)
"""

from fp_common.converters.collection_converters import (
    document_from_dict,
    document_from_proto,
    search_result_from_dict,
)

# Cost converters (Story 13.6)
from fp_common.converters.cost_converters import (
    agent_type_cost_to_proto,
    budget_status_from_proto,
    budget_threshold_config_from_proto,
    cost_summary_from_proto,
    cost_type_summary_to_proto,
    current_day_cost_from_proto,
    daily_cost_entry_to_proto,
    daily_cost_trend_from_proto,
    document_cost_summary_from_proto,
    domain_cost_to_proto,
    embedding_cost_by_domain_from_proto,
    llm_cost_by_agent_type_from_proto,
    llm_cost_by_model_from_proto,
    model_cost_to_proto,
)
from fp_common.converters.plantation_converters import (
    collection_point_from_proto,
    collection_point_to_proto,
    conditional_reject_from_proto,
    conditional_reject_to_proto,
    factory_from_proto,
    farmer_from_proto,
    farmer_summary_from_proto,
    grade_rules_from_proto,
    grade_rules_to_proto,
    grading_attribute_from_proto,
    grading_attribute_to_proto,
    grading_model_from_proto,
    grading_model_to_proto,
    grading_type_from_proto,
    grading_type_to_proto,
    region_from_proto,
)

# RAG converters (Story 0.75.23)
from fp_common.converters.rag_converters import (
    retrieval_match_from_proto,
    retrieval_match_to_proto,
    retrieval_query_from_proto,
    retrieval_query_to_proto,
    retrieval_result_from_proto,
    retrieval_result_to_proto,
)

__all__ = [
    # Cost converters (proto-to-pydantic)
    "agent_type_cost_to_proto",
    "budget_status_from_proto",
    "budget_threshold_config_from_proto",
    "collection_point_from_proto",
    "collection_point_to_proto",
    # Grading model converters (Story 9.6a)
    "conditional_reject_from_proto",
    "conditional_reject_to_proto",
    "cost_summary_from_proto",
    "cost_type_summary_to_proto",
    "current_day_cost_from_proto",
    "daily_cost_entry_to_proto",
    "daily_cost_trend_from_proto",
    "document_cost_summary_from_proto",
    "document_from_dict",
    "document_from_proto",
    "domain_cost_to_proto",
    "embedding_cost_by_domain_from_proto",
    "factory_from_proto",
    "farmer_from_proto",
    "farmer_summary_from_proto",
    "grade_rules_from_proto",
    "grade_rules_to_proto",
    "grading_attribute_from_proto",
    "grading_attribute_to_proto",
    "grading_model_from_proto",
    "grading_model_to_proto",
    "grading_type_from_proto",
    "grading_type_to_proto",
    "llm_cost_by_agent_type_from_proto",
    "llm_cost_by_model_from_proto",
    "model_cost_to_proto",
    "region_from_proto",
    # RAG converters (Story 0.75.23)
    "retrieval_match_from_proto",
    "retrieval_match_to_proto",
    "retrieval_query_from_proto",
    "retrieval_query_to_proto",
    "retrieval_result_from_proto",
    "retrieval_result_to_proto",
    "search_result_from_dict",
]
