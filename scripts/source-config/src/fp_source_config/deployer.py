"""Source configuration deployer.

Handles deployment of source configurations to MongoDB,
including versioning, history tracking, and rollback capabilities.
"""

import getpass
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, NamedTuple

import yaml
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

# Add fp-common to path for local development
sys.path.insert(0, str(Path(__file__).parents[4] / "libs" / "fp-common"))

from fp_common.models.source_config import SchemaDocument, SourceConfig

from fp_source_config.settings import Environment, get_settings


class DeploymentAction(NamedTuple):
    """Result of deploying a single source configuration."""

    source_id: str
    action: Literal["created", "updated", "unchanged"]
    version: int
    message: str | None = None


class SchemaDeploymentAction(NamedTuple):
    """Result of deploying a single schema."""

    schema_name: str
    action: Literal["created", "updated", "unchanged"]
    version: int


class DeployedConfig(BaseModel):
    """A deployed source configuration stored in MongoDB."""

    source_id: str
    display_name: str
    description: str
    enabled: bool
    config: dict
    version: int
    deployed_at: datetime
    deployed_by: str
    git_sha: str | None = None


class ConfigHistory(BaseModel):
    """Historical version of a source configuration."""

    source_id: str
    version: int
    config: dict
    deployed_at: datetime
    deployed_by: str
    git_sha: str | None = None


def get_git_sha() -> str | None:
    """Get the current git commit SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()[:12]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_current_user() -> str:
    """Get the current username for deployment tracking."""
    try:
        return getpass.getuser()
    except Exception:
        return "unknown"


class SourceConfigDeployer:
    """Deploys source configurations to MongoDB."""

    CONFIGS_COLLECTION = "source_configs"
    HISTORY_COLLECTION = "source_config_history"
    SCHEMAS_COLLECTION = "validation_schemas"

    def __init__(self, env: Environment) -> None:
        """Initialize the deployer for a specific environment.

        Args:
            env: Target environment (dev, staging, prod).
        """
        self.env = env
        self.settings = get_settings()
        self._client: AsyncIOMotorClient | None = None
        self._db: AsyncIOMotorDatabase | None = None

    async def connect(self) -> None:
        """Connect to MongoDB."""
        uri = self.settings.get_mongodb_uri(self.env)
        self._client = AsyncIOMotorClient(uri)
        self._db = self._client[self.settings.database_name]

    async def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None

    @property
    def db(self) -> AsyncIOMotorDatabase:
        """Get the database instance."""
        if self._db is None:
            raise RuntimeError("Not connected to MongoDB. Call connect() first.")
        return self._db

    async def deploy(
        self,
        configs: list[SourceConfig],
        dry_run: bool = False,
    ) -> list[DeploymentAction]:
        """Deploy source configurations to MongoDB.

        Args:
            configs: List of source configurations to deploy.
            dry_run: If True, show what would be deployed without making changes.

        Returns:
            List of deployment actions taken.
        """
        actions: list[DeploymentAction] = []
        git_sha = get_git_sha()
        deployed_by = get_current_user()
        deployed_at = datetime.now(timezone.utc)

        for config in configs:
            # Get existing config if any
            existing = await self.db[self.CONFIGS_COLLECTION].find_one(
                {"source_id": config.source_id}
            )

            config_dict = config.model_dump()

            if existing is None:
                # Create new config
                if not dry_run:
                    doc = {
                        "_id": config.source_id,
                        "source_id": config.source_id,
                        "display_name": config.display_name,
                        "description": config.description,
                        "enabled": config.enabled,
                        "config": {
                            "ingestion": config_dict["ingestion"],
                            "validation": config_dict.get("validation"),
                            "transformation": config_dict["transformation"],
                            "storage": config_dict["storage"],
                        },
                        "version": 1,
                        "deployed_at": deployed_at,
                        "deployed_by": deployed_by,
                        "git_sha": git_sha,
                    }
                    await self.db[self.CONFIGS_COLLECTION].insert_one(doc)

                    # Also add to history
                    history_doc = {
                        "source_id": config.source_id,
                        "version": 1,
                        "config": doc["config"],
                        "deployed_at": deployed_at,
                        "deployed_by": deployed_by,
                        "git_sha": git_sha,
                    }
                    await self.db[self.HISTORY_COLLECTION].insert_one(history_doc)

                actions.append(
                    DeploymentAction(
                        source_id=config.source_id,
                        action="created",
                        version=1,
                    )
                )
            else:
                # Check if config changed
                new_config = {
                    "ingestion": config_dict["ingestion"],
                    "validation": config_dict.get("validation"),
                    "transformation": config_dict["transformation"],
                    "storage": config_dict["storage"],
                }

                # Simple equality check (deep comparison would be better)
                existing_config = existing.get("config", {})
                if new_config == existing_config:
                    actions.append(
                        DeploymentAction(
                            source_id=config.source_id,
                            action="unchanged",
                            version=existing.get("version", 1),
                        )
                    )
                else:
                    # Update config
                    new_version = existing.get("version", 0) + 1

                    if not dry_run:
                        await self.db[self.CONFIGS_COLLECTION].update_one(
                            {"source_id": config.source_id},
                            {
                                "$set": {
                                    "display_name": config.display_name,
                                    "description": config.description,
                                    "enabled": config.enabled,
                                    "config": new_config,
                                    "version": new_version,
                                    "deployed_at": deployed_at,
                                    "deployed_by": deployed_by,
                                    "git_sha": git_sha,
                                }
                            },
                        )

                        # Add to history
                        history_doc = {
                            "source_id": config.source_id,
                            "version": new_version,
                            "config": new_config,
                            "deployed_at": deployed_at,
                            "deployed_by": deployed_by,
                            "git_sha": git_sha,
                        }
                        await self.db[self.HISTORY_COLLECTION].insert_one(history_doc)

                    actions.append(
                        DeploymentAction(
                            source_id=config.source_id,
                            action="updated",
                            version=new_version,
                        )
                    )

        return actions

    async def list_configs(self) -> list[DeployedConfig]:
        """List all deployed source configurations.

        Returns:
            List of deployed configurations.
        """
        configs: list[DeployedConfig] = []
        cursor = self.db[self.CONFIGS_COLLECTION].find({})

        async for doc in cursor:
            configs.append(
                DeployedConfig(
                    source_id=doc["source_id"],
                    display_name=doc.get("display_name", ""),
                    description=doc.get("description", ""),
                    enabled=doc.get("enabled", True),
                    config=doc.get("config", {}),
                    version=doc.get("version", 1),
                    deployed_at=doc.get("deployed_at", datetime.now(timezone.utc)),
                    deployed_by=doc.get("deployed_by", "unknown"),
                    git_sha=doc.get("git_sha"),
                )
            )

        return sorted(configs, key=lambda c: c.source_id)

    async def get_config(self, source_id: str) -> DeployedConfig | None:
        """Get a specific deployed source configuration.

        Args:
            source_id: The source ID to retrieve.

        Returns:
            The deployed configuration, or None if not found.
        """
        doc = await self.db[self.CONFIGS_COLLECTION].find_one({"source_id": source_id})
        if doc is None:
            return None

        return DeployedConfig(
            source_id=doc["source_id"],
            display_name=doc.get("display_name", ""),
            description=doc.get("description", ""),
            enabled=doc.get("enabled", True),
            config=doc.get("config", {}),
            version=doc.get("version", 1),
            deployed_at=doc.get("deployed_at", datetime.now(timezone.utc)),
            deployed_by=doc.get("deployed_by", "unknown"),
            git_sha=doc.get("git_sha"),
        )

    async def get_history(
        self,
        source_id: str,
        limit: int = 10,
    ) -> list[ConfigHistory]:
        """Get deployment history for a source configuration.

        Args:
            source_id: The source ID to get history for.
            limit: Maximum number of history entries to return.

        Returns:
            List of historical versions, newest first.
        """
        history: list[ConfigHistory] = []
        cursor = (
            self.db[self.HISTORY_COLLECTION]
            .find({"source_id": source_id})
            .sort("version", -1)
            .limit(limit)
        )

        async for doc in cursor:
            history.append(
                ConfigHistory(
                    source_id=doc["source_id"],
                    version=doc["version"],
                    config=doc.get("config", {}),
                    deployed_at=doc.get("deployed_at", datetime.now(timezone.utc)),
                    deployed_by=doc.get("deployed_by", "unknown"),
                    git_sha=doc.get("git_sha"),
                )
            )

        return history

    async def rollback(
        self,
        source_id: str,
        target_version: int,
    ) -> DeploymentAction | None:
        """Rollback a source configuration to a previous version.

        Args:
            source_id: The source ID to rollback.
            target_version: The version number to rollback to.

        Returns:
            The deployment action, or None if rollback failed.
        """
        # Find the historical version
        history_doc = await self.db[self.HISTORY_COLLECTION].find_one(
            {"source_id": source_id, "version": target_version}
        )

        if history_doc is None:
            return None

        # Get current config to determine new version
        current = await self.db[self.CONFIGS_COLLECTION].find_one(
            {"source_id": source_id}
        )

        if current is None:
            return None

        new_version = current.get("version", 0) + 1
        deployed_at = datetime.now(timezone.utc)
        deployed_by = get_current_user()
        git_sha = get_git_sha()

        # Update to the historical config
        await self.db[self.CONFIGS_COLLECTION].update_one(
            {"source_id": source_id},
            {
                "$set": {
                    "config": history_doc["config"],
                    "version": new_version,
                    "deployed_at": deployed_at,
                    "deployed_by": deployed_by,
                    "git_sha": git_sha,
                }
            },
        )

        # Add rollback to history
        history_entry = {
            "source_id": source_id,
            "version": new_version,
            "config": history_doc["config"],
            "deployed_at": deployed_at,
            "deployed_by": deployed_by,
            "git_sha": git_sha,
        }
        await self.db[self.HISTORY_COLLECTION].insert_one(history_entry)

        return DeploymentAction(
            source_id=source_id,
            action="updated",
            version=new_version,
            message=f"Rolled back to version {target_version}",
        )

    async def deploy_schemas(
        self,
        schemas: list[tuple[str, dict]],
        dry_run: bool = False,
    ) -> list[SchemaDeploymentAction]:
        """Deploy validation schemas to MongoDB.

        Args:
            schemas: List of (schema_name, schema_content) tuples.
            dry_run: If True, show what would be deployed without making changes.

        Returns:
            List of schema deployment actions taken.
        """
        actions: list[SchemaDeploymentAction] = []
        git_sha = get_git_sha()
        deployed_by = get_current_user()
        deployed_at = datetime.now(timezone.utc)

        for schema_name, schema_content in schemas:
            existing = await self.db[self.SCHEMAS_COLLECTION].find_one(
                {"name": schema_name}
            )

            if existing is None:
                # Create new schema
                if not dry_run:
                    doc = {
                        "_id": schema_name,
                        "name": schema_name,
                        "content": schema_content,
                        "version": 1,
                        "deployed_at": deployed_at,
                        "deployed_by": deployed_by,
                        "git_sha": git_sha,
                    }
                    await self.db[self.SCHEMAS_COLLECTION].insert_one(doc)

                actions.append(
                    SchemaDeploymentAction(
                        schema_name=schema_name,
                        action="created",
                        version=1,
                    )
                )
            else:
                # Check if schema changed
                if schema_content == existing.get("content"):
                    actions.append(
                        SchemaDeploymentAction(
                            schema_name=schema_name,
                            action="unchanged",
                            version=existing.get("version", 1),
                        )
                    )
                else:
                    # Update schema
                    new_version = existing.get("version", 0) + 1

                    if not dry_run:
                        await self.db[self.SCHEMAS_COLLECTION].update_one(
                            {"name": schema_name},
                            {
                                "$set": {
                                    "content": schema_content,
                                    "version": new_version,
                                    "deployed_at": deployed_at,
                                    "deployed_by": deployed_by,
                                    "git_sha": git_sha,
                                }
                            },
                        )

                    actions.append(
                        SchemaDeploymentAction(
                            schema_name=schema_name,
                            action="updated",
                            version=new_version,
                        )
                    )

        return actions

    async def get_schema(self, schema_name: str) -> SchemaDocument | None:
        """Get a validation schema by name.

        Args:
            schema_name: The schema name to retrieve.

        Returns:
            The schema document, or None if not found.
        """
        doc = await self.db[self.SCHEMAS_COLLECTION].find_one({"name": schema_name})
        if doc is None:
            return None

        return SchemaDocument(
            name=doc["name"],
            content=doc["content"],
            version=doc.get("version", 1),
            deployed_at=doc.get("deployed_at", datetime.now(timezone.utc)),
            deployed_by=doc.get("deployed_by", "unknown"),
            git_sha=doc.get("git_sha"),
        )

    async def list_schemas(self) -> list[SchemaDocument]:
        """List all deployed validation schemas.

        Returns:
            List of schema documents.
        """
        schemas: list[SchemaDocument] = []
        cursor = self.db[self.SCHEMAS_COLLECTION].find({})

        async for doc in cursor:
            schemas.append(
                SchemaDocument(
                    name=doc["name"],
                    content=doc["content"],
                    version=doc.get("version", 1),
                    deployed_at=doc.get("deployed_at", datetime.now(timezone.utc)),
                    deployed_by=doc.get("deployed_by", "unknown"),
                    git_sha=doc.get("git_sha"),
                )
            )

        return sorted(schemas, key=lambda s: s.name)

    async def validate_schema_references(
        self,
        configs: list[SourceConfig],
        schemas_being_deployed: list[tuple[str, dict]] | None = None,
    ) -> list[str]:
        """Validate that all schema references in configs can be resolved.

        Checks that each referenced schema exists either:
        - In MongoDB (already deployed)
        - In the schemas_being_deployed list (will be deployed in same batch)

        Args:
            configs: List of source configurations to validate.
            schemas_being_deployed: Optional list of schemas being deployed
                in the same batch.

        Returns:
            List of error messages for missing/invalid schema references.
        """
        errors: list[str] = []
        schemas_in_batch = {name for name, _ in (schemas_being_deployed or [])}

        for config in configs:
            if config.validation is None:
                continue

            schema_name = config.validation.schema_name
            schema_version = config.validation.schema_version

            # Check if schema exists in MongoDB
            existing = await self.db[self.SCHEMAS_COLLECTION].find_one(
                {"name": schema_name}
            )

            if existing is None:
                # Schema not in MongoDB, check if it's being deployed
                if schema_name not in schemas_in_batch:
                    errors.append(
                        f"Source '{config.source_id}' references schema "
                        f"'{schema_name}' which is not deployed and not in "
                        f"current deployment batch"
                    )
            elif schema_version is not None:
                # Schema exists, check version if specified
                deployed_version = existing.get("version", 1)
                if schema_version > deployed_version:
                    errors.append(
                        f"Source '{config.source_id}' references schema "
                        f"'{schema_name}' version {schema_version}, but only "
                        f"version {deployed_version} is deployed"
                    )

        return errors


def load_source_configs(files: list[Path]) -> list[SourceConfig]:
    """Load and parse source configuration files.

    Args:
        files: List of YAML file paths.

    Returns:
        List of validated SourceConfig objects.
    """
    configs: list[SourceConfig] = []

    for file_path in files:
        with open(file_path) as f:
            data = yaml.safe_load(f)
            config = SourceConfig.model_validate(data)
            configs.append(config)

    return configs


def load_schemas_for_configs(
    configs: list[SourceConfig],
    schemas_base_path: Path,
) -> list[tuple[str, dict]]:
    """Load validation schemas referenced by source configs.

    Args:
        configs: List of source configurations.
        schemas_base_path: Base path where schema files are located.

    Returns:
        List of (schema_name, schema_content) tuples.
    """
    schemas: list[tuple[str, dict]] = []
    seen_schemas: set[str] = set()

    for config in configs:
        if config.validation is None:
            continue

        schema_name = config.validation.schema_name
        if schema_name in seen_schemas:
            continue

        schema_path = schemas_base_path / schema_name
        if not schema_path.exists():
            raise FileNotFoundError(
                f"Schema file not found: {schema_path} "
                f"(referenced by {config.source_id})"
            )

        with open(schema_path) as f:
            schema_content = json.load(f)

        schemas.append((schema_name, schema_content))
        seen_schemas.add(schema_name)

    return schemas


def print_deployment_results(
    actions: list[DeploymentAction],
    dry_run: bool = False,
    console: Console | None = None,
) -> None:
    """Print deployment results to the console.

    Args:
        actions: List of deployment actions.
        dry_run: Whether this was a dry run.
        console: Rich console for output.
    """
    if console is None:
        console = Console()

    title = "Deployment Preview" if dry_run else "Deployment Results"
    table = Table(title=title)
    table.add_column("Source ID", style="cyan")
    table.add_column("Action", style="green")
    table.add_column("Version", style="blue")

    for action in actions:
        action_style = {
            "created": "[green]created[/green]",
            "updated": "[yellow]updated[/yellow]",
            "unchanged": "[dim]unchanged[/dim]",
        }
        table.add_row(
            action.source_id,
            action_style.get(action.action, action.action),
            str(action.version),
        )

    console.print(table)

    # Summary
    created = sum(1 for a in actions if a.action == "created")
    updated = sum(1 for a in actions if a.action == "updated")
    unchanged = sum(1 for a in actions if a.action == "unchanged")

    created_str = f"[green]{created} created[/green]"
    updated_str = f"[yellow]{updated} updated[/yellow]"
    unchanged_str = f"[dim]{unchanged} unchanged[/dim]"
    summary = f"{created_str}, {updated_str}, {unchanged_str}"
    if dry_run:
        console.print(f"\n[bold]Dry run:[/bold] {summary}")
    else:
        console.print(f"\n[bold]Summary:[/bold] {summary}")


def print_schema_deployment_results(
    actions: list[SchemaDeploymentAction],
    dry_run: bool = False,
    console: Console | None = None,
) -> None:
    """Print schema deployment results to the console.

    Args:
        actions: List of schema deployment actions.
        dry_run: Whether this was a dry run.
        console: Rich console for output.
    """
    if not actions:
        return

    if console is None:
        console = Console()

    title = "Schema Deployment Preview" if dry_run else "Schema Deployment Results"
    table = Table(title=title)
    table.add_column("Schema Name", style="cyan")
    table.add_column("Action", style="green")
    table.add_column("Version", style="blue")

    for action in actions:
        action_style = {
            "created": "[green]created[/green]",
            "updated": "[yellow]updated[/yellow]",
            "unchanged": "[dim]unchanged[/dim]",
        }
        table.add_row(
            action.schema_name,
            action_style.get(action.action, action.action),
            str(action.version),
        )

    console.print(table)

    # Summary
    created = sum(1 for a in actions if a.action == "created")
    updated = sum(1 for a in actions if a.action == "updated")
    unchanged = sum(1 for a in actions if a.action == "unchanged")

    created_str = f"[green]{created} created[/green]"
    updated_str = f"[yellow]{updated} updated[/yellow]"
    unchanged_str = f"[dim]{unchanged} unchanged[/dim]"
    summary = f"{created_str}, {updated_str}, {unchanged_str}"
    if dry_run:
        console.print(f"\n[bold]Schemas dry run:[/bold] {summary}")
    else:
        console.print(f"\n[bold]Schemas summary:[/bold] {summary}")
