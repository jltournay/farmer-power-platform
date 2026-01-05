"""Farmer Power Agent Configuration CLI.

Command-line interface for managing agent configurations
for the AI Model service.
"""

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from fp_agent_config.client import AgentConfigClient
from fp_agent_config.models import AgentConfigStatus
from fp_agent_config.settings import Environment, get_settings
from fp_agent_config.validator import validate_agent_config_yaml

app = typer.Typer(
    name="fp-agent-config",
    help="Manage agent configurations for Farmer Power AI Model",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)


def _validate_environment(env: str) -> Environment:
    """Validate and return the environment value."""
    valid_envs: list[Environment] = ["dev", "staging", "prod"]
    if env not in valid_envs:
        raise typer.BadParameter(
            f"Invalid environment '{env}'. Must be one of: {', '.join(valid_envs)}"
        )
    return env  # type: ignore[return-value]


def _print_error(message: str) -> None:
    """Print error message to stderr with Error: prefix."""
    err_console.print(f"[red]Error: {message}[/red]")


@app.command()
def validate(
    file: str = typer.Option(
        ...,
        "--file",
        "-f",
        help="Path to the agent config YAML file to validate",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed validation output",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Minimal output (errors only)",
    ),
) -> None:
    """Validate an agent config YAML file against the schema without deploying.

    Examples:
        fp-agent-config validate -f configs/disease-diagnosis.yaml
        fp-agent-config validate -f configs/disease-diagnosis.yaml --verbose
    """
    file_path = Path(file)
    if not file_path.exists():
        _print_error(f"File not found: {file}")
        raise typer.Exit(code=1)

    result = validate_agent_config_yaml(file_path)

    if result.is_valid:
        if not quiet:
            console.print(f"[green]✓ Valid:[/green] {file}")
            if verbose and result.config:
                console.print(f"  [dim]agent_id:[/dim] {result.config.agent_id}")
                console.print(f"  [dim]type:[/dim] {result.config.type}")
                console.print(f"  [dim]version:[/dim] {result.config.version}")
                console.print(f"  [dim]status:[/dim] {result.config.status.value}")
        raise typer.Exit(code=0)
    else:
        _print_error(f"Validation failed for {file}")
        for error in result.errors:
            err_console.print(f"  [red]• {error}[/red]")
        raise typer.Exit(code=1)


@app.command()
def deploy(
    file: str = typer.Option(
        ...,
        "--file",
        "-f",
        help="Path to the agent config YAML file to deploy",
    ),
    env: str = typer.Option(
        ...,
        "--env",
        "-e",
        help="Target environment (dev, staging, prod)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be deployed without making changes",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Minimal output (errors only)",
    ),
) -> None:
    """Deploy an agent config YAML file to MongoDB.

    Validates the YAML file first, then uploads to the specified environment.

    Examples:
        fp-agent-config deploy -f configs/diagnosis.yaml --env dev
        fp-agent-config deploy -f configs/diagnosis.yaml --env staging --dry-run
    """
    environment = _validate_environment(env)
    file_path = Path(file)

    if not file_path.exists():
        _print_error(f"File not found: {file}")
        raise typer.Exit(code=1)

    # First validate the YAML
    result = validate_agent_config_yaml(file_path)
    if not result.is_valid:
        _print_error(f"Validation failed for {file}")
        for error in result.errors:
            err_console.print(f"  [red]• {error}[/red]")
        raise typer.Exit(code=1)

    config = result.config
    if config is None:
        _print_error("Validation returned no config object")
        raise typer.Exit(code=1)

    if dry_run:
        console.print("[yellow]Dry run - no changes will be made[/yellow]")
        console.print(f"Would deploy to [cyan]{environment}[/cyan] environment:")
        console.print(f"  agent_id: {config.agent_id}")
        console.print(f"  type: {config.type}")
        console.print(f"  version: {config.version}")
        console.print(f"  status: {config.status.value}")
        raise typer.Exit(code=0)

    async def run_deploy() -> None:
        settings = get_settings()
        client = AgentConfigClient(settings, environment)
        try:
            await client.connect()

            # Check if version already exists
            existing = await client.get_by_version(config.agent_id, config.version)
            if existing:
                aid = config.agent_id
                _print_error(f"Version {config.version} already exists for '{aid}'")
                raise typer.Exit(code=1)

            # Deploy the config
            await client.create(config)

            if not quiet:
                console.print(
                    f"[green]✓ Deployed:[/green] {config.agent_id} v{config.version}"
                )
                if verbose:
                    console.print(f"  [dim]type:[/dim] {config.type}")
                    console.print(f"  [dim]status:[/dim] {config.status.value}")
                    console.print(f"  [dim]environment:[/dim] {environment}")
        finally:
            await client.disconnect()

    try:
        asyncio.run(run_deploy())
    except typer.Exit:
        raise
    except Exception as e:
        _print_error(f"Deployment failed: {e}")
        raise typer.Exit(code=1)


@app.command("list")
def list_configs(
    env: str = typer.Option(
        ...,
        "--env",
        "-e",
        help="Target environment (dev, staging, prod)",
    ),
    status: str | None = typer.Option(
        None,
        "--status",
        "-s",
        help="Filter by status (draft, staged, active, archived)",
    ),
    agent_type: str | None = typer.Option(
        None,
        "--type",
        "-t",
        help="Filter by type (extractor, explorer, generator, etc.)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Minimal output (errors only)",
    ),
) -> None:
    """List all agent configs in the specified environment.

    Examples:
        fp-agent-config list --env dev
        fp-agent-config list --env dev --status active
        fp-agent-config list --env dev --type explorer
    """
    environment = _validate_environment(env)

    async def run_list() -> None:
        settings = get_settings()
        client = AgentConfigClient(settings, environment)
        try:
            await client.connect()
            configs = await client.list_configs(status=status, agent_type=agent_type)

            if not configs:
                if not quiet:
                    console.print(f"[yellow]No configs found in {environment}[/yellow]")
                return

            table = Table(title=f"Agent Configs ({environment})")
            table.add_column("Agent ID", style="cyan")
            table.add_column("Type", style="white")
            table.add_column("Version", style="blue")
            table.add_column("Status", style="white")
            table.add_column("Updated At", style="dim")

            for cfg in configs:
                status_style = {
                    "active": "[green]active[/green]",
                    "staged": "[yellow]staged[/yellow]",
                    "draft": "[dim]draft[/dim]",
                    "archived": "[dim]archived[/dim]",
                }.get(cfg.status.value, cfg.status.value)

                updated_at = cfg.metadata.updated_at.strftime("%Y-%m-%d %H:%M")
                table.add_row(
                    cfg.agent_id,
                    cfg.type,
                    cfg.version,
                    status_style,
                    updated_at,
                )

            console.print(table)
            console.print(f"\n[dim]Total: {len(configs)} config(s)[/dim]")
        finally:
            await client.disconnect()

    try:
        asyncio.run(run_list())
    except typer.Exit:
        raise
    except Exception as e:
        _print_error(f"Error listing configs: {e}")
        raise typer.Exit(code=1)


@app.command()
def get(
    agent_id: str = typer.Option(
        ...,
        "--agent-id",
        "-a",
        help="The agent ID to retrieve",
    ),
    env: str = typer.Option(
        ...,
        "--env",
        "-e",
        help="Target environment (dev, staging, prod)",
    ),
    version: str | None = typer.Option(
        None,
        "--version",
        "-V",
        help="Specific version to retrieve (defaults to active, then latest staged)",
    ),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (prints to stdout if not specified)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Minimal output (errors only)",
    ),
) -> None:
    """Get a specific agent config by agent_id.

    If no version specified, returns active version (or latest staged if none).

    Examples:
        fp-agent-config get --agent-id diagnosis --env dev
        fp-agent-config get --agent-id diagnosis --env dev --version 2.1.0
        fp-agent-config get --agent-id diagnosis --env dev --output out.yaml
    """
    environment = _validate_environment(env)

    async def run_get() -> None:
        import yaml

        settings = get_settings()
        client = AgentConfigClient(settings, environment)
        try:
            await client.connect()

            if version:
                config = await client.get_by_version(agent_id, version)
                if not config:
                    _print_error(f"Agent '{agent_id}' version {version} not found")
                    raise typer.Exit(code=1)
            else:
                # Try active first, then latest staged
                config = await client.get_active(agent_id)
                if not config:
                    config = await client.get_latest_staged(agent_id)
                if not config:
                    _print_error(f"No active or staged config found for '{agent_id}'")
                    raise typer.Exit(code=1)

            # Convert to YAML-friendly dict
            config_dict = config.model_dump(mode="json")
            # Remove internal id field for export
            config_dict.pop("id", None)

            yaml_output = yaml.dump(
                config_dict,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

            if output:
                output_path = Path(output)
                output_path.write_text(yaml_output)
                if not quiet:
                    console.print(f"[green]✓ Saved to:[/green] {output}")
            else:
                console.print(yaml_output)
        finally:
            await client.disconnect()

    try:
        asyncio.run(run_get())
    except typer.Exit:
        raise
    except Exception as e:
        _print_error(f"Error getting config: {e}")
        raise typer.Exit(code=1)


@app.command()
def stage(
    file: str = typer.Option(
        ...,
        "--file",
        "-f",
        help="Path to the agent config YAML file to stage",
    ),
    env: str = typer.Option(
        ...,
        "--env",
        "-e",
        help="Target environment (dev, staging, prod)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Minimal output (errors only)",
    ),
) -> None:
    """Stage a new agent config version with status=staged.

    Creates a new version of the config with staged status.

    Examples:
        fp-agent-config stage -f configs/disease-diagnosis-v2.yaml --env dev
    """
    environment = _validate_environment(env)
    file_path = Path(file)

    if not file_path.exists():
        _print_error(f"File not found: {file}")
        raise typer.Exit(code=1)

    # Validate the YAML
    result = validate_agent_config_yaml(file_path)
    if not result.is_valid:
        _print_error(f"Validation failed for {file}")
        for error in result.errors:
            err_console.print(f"  [red]• {error}[/red]")
        raise typer.Exit(code=1)

    config = result.config
    if config is None:
        _print_error("Validation returned no config object")
        raise typer.Exit(code=1)

    # Override status to staged
    config = config.model_copy(update={"status": AgentConfigStatus.STAGED})

    async def run_stage() -> None:
        settings = get_settings()
        client = AgentConfigClient(settings, environment)
        try:
            await client.connect()

            # Check if version already exists
            existing = await client.get_by_version(config.agent_id, config.version)
            if existing:
                aid = config.agent_id
                _print_error(f"Version {config.version} already exists for '{aid}'")
                raise typer.Exit(code=1)

            # Stage the config
            await client.create(config)

            if not quiet:
                console.print(
                    f"[green]✓ Staged:[/green] {config.agent_id} v{config.version}"
                )
                if verbose:
                    console.print(f"  [dim]type:[/dim] {config.type}")
                    console.print(f"  [dim]environment:[/dim] {environment}")
        finally:
            await client.disconnect()

    try:
        asyncio.run(run_stage())
    except typer.Exit:
        raise
    except Exception as e:
        _print_error(f"Staging failed: {e}")
        raise typer.Exit(code=1)


@app.command()
def promote(
    agent_id: str = typer.Option(
        ...,
        "--agent-id",
        "-a",
        help="The agent ID to promote",
    ),
    env: str = typer.Option(
        ...,
        "--env",
        "-e",
        help="Target environment (dev, staging, prod)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Minimal output (errors only)",
    ),
) -> None:
    """Promote a staged agent config to active.

    Archives the current active version (if exists) and promotes the staged version.

    Examples:
        fp-agent-config promote --agent-id disease-diagnosis --env dev
    """
    environment = _validate_environment(env)

    async def run_promote() -> None:
        settings = get_settings()
        client = AgentConfigClient(settings, environment)
        try:
            await client.connect()

            result = await client.promote(agent_id)

            if result.error:
                _print_error(result.error)
                raise typer.Exit(code=1)

            if not quiet:
                console.print(
                    f"[green]✓ Promoted:[/green] {agent_id} v{result.promoted_version}"
                )
                if result.archived_version and verbose:
                    console.print(
                        f"  [dim]Archived previous:[/dim] v{result.archived_version}"
                    )
        finally:
            await client.disconnect()

    try:
        asyncio.run(run_promote())
    except typer.Exit:
        raise
    except Exception as e:
        _print_error(f"Promotion failed: {e}")
        raise typer.Exit(code=1)


@app.command()
def rollback(
    agent_id: str = typer.Option(
        ...,
        "--agent-id",
        "-a",
        help="The agent ID to rollback",
    ),
    to_version: str = typer.Option(
        ...,
        "--to-version",
        "-t",
        help="The version to rollback to",
    ),
    env: str = typer.Option(
        ...,
        "--env",
        "-e",
        help="Target environment (dev, staging, prod)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Minimal output (errors only)",
    ),
) -> None:
    """Rollback to a previous version of an agent config.

    Archives current active version and creates new version from rollback target.

    Examples:
        fp-agent-config rollback -a diagnosis --to-version 1.0.0 --env dev
    """
    environment = _validate_environment(env)

    async def run_rollback() -> None:
        settings = get_settings()
        client = AgentConfigClient(settings, environment)
        try:
            await client.connect()

            result = await client.rollback(agent_id, to_version)

            if result.error:
                _print_error(result.error)
                raise typer.Exit(code=1)

            if not quiet:
                console.print(
                    f"[green]✓ Rolled back:[/green] {agent_id} to v{to_version}"
                )
                console.print(f"  [dim]New version:[/dim] v{result.new_version}")
                if result.archived_version and verbose:
                    console.print(f"  [dim]Archived:[/dim] v{result.archived_version}")
        finally:
            await client.disconnect()

    try:
        asyncio.run(run_rollback())
    except typer.Exit:
        raise
    except Exception as e:
        _print_error(f"Rollback failed: {e}")
        raise typer.Exit(code=1)


@app.command()
def versions(
    agent_id: str = typer.Option(
        ...,
        "--agent-id",
        "-a",
        help="The agent ID to list versions for",
    ),
    env: str = typer.Option(
        ...,
        "--env",
        "-e",
        help="Target environment (dev, staging, prod)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Minimal output (errors only)",
    ),
) -> None:
    """List all versions of an agent config.

    Examples:
        fp-agent-config versions --agent-id disease-diagnosis --env dev
    """
    environment = _validate_environment(env)

    async def run_versions() -> None:
        settings = get_settings()
        client = AgentConfigClient(settings, environment)
        try:
            await client.connect()
            configs = await client.list_versions(agent_id)

            if not configs:
                if not quiet:
                    msg = f"No versions found for '{agent_id}' in {environment}"
                    console.print(f"[yellow]{msg}[/yellow]")
                return

            table = Table(title=f"Versions of {agent_id} ({environment})")
            table.add_column("Version", style="blue")
            table.add_column("Type", style="white")
            table.add_column("Status", style="white")
            table.add_column("Updated At", style="dim")
            table.add_column("Author", style="dim")

            for cfg in configs:
                status_style = {
                    "active": "[green]● active[/green]",
                    "staged": "[yellow]○ staged[/yellow]",
                    "draft": "[dim]○ draft[/dim]",
                    "archived": "[dim]· archived[/dim]",
                }.get(cfg.status.value, cfg.status.value)

                updated_at = cfg.metadata.updated_at.strftime("%Y-%m-%d %H:%M")
                table.add_row(
                    cfg.version,
                    cfg.type,
                    status_style,
                    updated_at,
                    cfg.metadata.author,
                )

            console.print(table)
            console.print(f"\n[dim]Total: {len(configs)} version(s)[/dim]")
        finally:
            await client.disconnect()

    try:
        asyncio.run(run_versions())
    except typer.Exit:
        raise
    except Exception as e:
        _print_error(f"Error listing versions: {e}")
        raise typer.Exit(code=1)


@app.command()
def enable(
    agent_id: str = typer.Option(
        ...,
        "--agent-id",
        "-a",
        help="The agent ID to enable",
    ),
    env: str = typer.Option(
        ...,
        "--env",
        "-e",
        help="Target environment (dev, staging, prod)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Minimal output (errors only)",
    ),
) -> None:
    """Enable an agent at runtime.

    Sets enabled=true on the active config for the agent_id.

    Examples:
        fp-agent-config enable --agent-id disease-diagnosis --env dev
    """
    environment = _validate_environment(env)

    async def run_enable() -> None:
        settings = get_settings()
        client = AgentConfigClient(settings, environment)
        try:
            await client.connect()

            success, error = await client.enable(agent_id)

            if error:
                _print_error(error)
                raise typer.Exit(code=1)

            if not quiet:
                console.print(f"[green]✓ Enabled:[/green] {agent_id}")
                if verbose:
                    console.print(f"  [dim]environment:[/dim] {environment}")
        finally:
            await client.disconnect()

    try:
        asyncio.run(run_enable())
    except typer.Exit:
        raise
    except Exception as e:
        _print_error(f"Enable failed: {e}")
        raise typer.Exit(code=1)


@app.command()
def disable(
    agent_id: str = typer.Option(
        ...,
        "--agent-id",
        "-a",
        help="The agent ID to disable",
    ),
    env: str = typer.Option(
        ...,
        "--env",
        "-e",
        help="Target environment (dev, staging, prod)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Minimal output (errors only)",
    ),
) -> None:
    """Disable an agent at runtime.

    Sets enabled=false on the active config for the agent_id.

    Examples:
        fp-agent-config disable --agent-id disease-diagnosis --env dev
    """
    environment = _validate_environment(env)

    async def run_disable() -> None:
        settings = get_settings()
        client = AgentConfigClient(settings, environment)
        try:
            await client.connect()

            success, error = await client.disable(agent_id)

            if error:
                _print_error(error)
                raise typer.Exit(code=1)

            if not quiet:
                console.print(f"[green]✓ Disabled:[/green] {agent_id}")
                if verbose:
                    console.print(f"  [dim]environment:[/dim] {environment}")
        finally:
            await client.disconnect()

    try:
        asyncio.run(run_disable())
    except typer.Exit:
        raise
    except Exception as e:
        _print_error(f"Disable failed: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
