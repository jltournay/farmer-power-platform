"""Farmer Power Platform test utilities.

Provides test fixtures, mocks, and utilities for testing services.
"""

__version__ = "0.1.0"

# MongoDB test utilities
from fp_testing.mongodb import (
    DEFAULT_MONGODB_URI,
    MongoTestClient,
    create_test_database,
    wait_for_mongodb,
)

__all__ = [
    "DEFAULT_MONGODB_URI",
    "MongoTestClient",
    "create_test_database",
    "wait_for_mongodb",
]
