"""Environment settings for the Agent Configuration CLI.

Handles configuration for different deployment environments (dev, staging, prod).
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings

Environment = Literal["dev", "staging", "prod"]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # MongoDB connection strings per environment
    mongodb_uri_dev: str = Field(
        default="mongodb://localhost:27017",
        alias="AI_MODEL_MONGODB_URI_DEV",
    )
    mongodb_uri_staging: str = Field(
        default="mongodb://localhost:27017",
        alias="AI_MODEL_MONGODB_URI_STAGING",
    )
    mongodb_uri_prod: str = Field(
        default="mongodb://localhost:27017",
        alias="AI_MODEL_MONGODB_URI_PROD",
    )

    # Database name
    database_name: str = Field(
        default="ai_model",
        alias="AI_MODEL_DATABASE_NAME",
    )

    # Collection name
    agent_configs_collection: str = Field(
        default="agent_configs",
        alias="AI_MODEL_AGENT_CONFIGS_COLLECTION",
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    def get_mongodb_uri(self, env: Environment) -> str:
        """Get MongoDB URI for the specified environment."""
        uri_map = {
            "dev": self.mongodb_uri_dev,
            "staging": self.mongodb_uri_staging,
            "prod": self.mongodb_uri_prod,
        }
        return uri_map[env]


@lru_cache
def get_settings() -> Settings:
    """Get application settings singleton."""
    return Settings()
