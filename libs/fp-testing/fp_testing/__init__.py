"""Farmer Power Platform test utilities.

Provides test fixtures, mocks, and utilities for testing services.
"""

__version__ = "0.1.0"

# MongoDB test utilities
from fp_testing.mongodb import (
    MongoTestClient,
    create_test_database,
    wait_for_mongodb,
    DEFAULT_MONGODB_URI,
)

__all__ = [
    "MongoTestClient",
    "create_test_database",
    "wait_for_mongodb",
    "DEFAULT_MONGODB_URI",
]
