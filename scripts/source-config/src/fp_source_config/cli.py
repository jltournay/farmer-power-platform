"""Farmer Power Source Configuration CLI.

Command-line interface for managing data source configurations
for the Collection Model service.
"""

import asyncio
from pathlib import Path

import typer
from rich.console import Console

from fp_source_config.deployer import (
    SourceConfigDeployer,
    load_source_configs,
    print_deployment_results,
)
from fp_source_config.settings import Environment, get_settings
from fp_source_config.validator import (
    get_source_config_files,
    print_validation_results,
    validate_source_configs,
)

app = typer.Typer(
    name="fp-source-config",
    help="Manage data source configurations for Farmer Power Collection Model",
    no_args_is_help=True,
)
console = Console()


@app.command()
def validate(
    file: str | None = typer.Option(
        None,
        "--file",
        "-f",
        help="Specific YAML file to validate (validates all if not specified)",
    ),
) -> None:
    """Validate source configuration YAML files against the schema."""
    settings = get_settings()

    if file:
        # Validate specific file
        file_path = Path(file)
        if not file_path.exists():
            console.print(f"[red]Error: File not found: {file}[/red]")
            raise typer.Exit(code=1)
        files = [file_path]
    else:
        # Validate all files in config directory
        files = get_source_config_files(settings.config_dir)
        if not files:
            console.print(
                f"[yellow]No YAML files found in {settings.config_dir}[/yellow]"
            )
            raise typer.Exit(code=0)

    console.print(f"Validating {len(files)} configuration file(s)...\n")

    results = validate_source_configs(files, console)
    all_valid = print_validation_results(results, console)

    raise typer.Exit(code=0 if all_valid else 1)


def _validate_environment(env: str) -> Environment:
    """Validate and return the environment value."""
    valid_envs: list[Environment] = ["dev", "staging", "prod"]
    if env not in valid_envs:
        raise typer.BadParameter(
            f"Invalid environment '{env}'. Must be one of: {', '.join(valid_envs)}"
        )
    return env  # type: ignore[return-value]


@app.command()
def deploy(
    env: str = typer.Option(
        ...,
        "--env",
        "-e",
        help="Target environment (dev, staging, prod)",
    ),
    file: str | None = typer.Option(
        None,
        "--file",
        "-f",
        help="Specific YAML file to deploy (deploys all if not specified)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be deployed without making changes",
    ),
) -> None:
    """Deploy source configurations to MongoDB."""
    environment = _validate_environment(env)
    settings = get_settings()

    # Get files to deploy
    if file:
        file_path = Path(file)
        if not file_path.exists():
            console.print(f"[red]Error: File not found: {file}[/red]")
            raise typer.Exit(code=1)
        files = [file_path]
    else:
        files = get_source_config_files(settings.config_dir)
        if not files:
            console.print(
                f"[yellow]No YAML files found in {settings.config_dir}[/yellow]"
            )
            raise typer.Exit(code=0)

    # Validate configs first
    console.print(f"Validating {len(files)} configuration file(s)...\n")
    results = validate_source_configs(files, console)
    all_valid = all(r.is_valid for r in results)

    if not all_valid:
        print_validation_results(results, console)
        console.print("\n[red]Cannot deploy: Fix validation errors first.[/red]")
        raise typer.Exit(code=1)

    console.print("[green]All configurations valid.[/green]\n")

    # Load configs for deployment
    try:
        configs = load_source_configs(files)
    except Exception as e:
        console.print(f"[red]Error loading configurations: {e}[/red]")
        raise typer.Exit(code=1)

    # Deploy to MongoDB
    async def run_deploy() -> None:
        deployer = SourceConfigDeployer(environment)
        try:
            await deployer.connect()
            console.print(f"[dim]Deploying to {environment} environment...[/dim]\n")
            actions = await deployer.deploy(configs, dry_run=dry_run)
            print_deployment_results(actions, dry_run=dry_run, console=console)
        finally:
            await deployer.disconnect()

    try:
        asyncio.run(run_deploy())
    except Exception as e:
        console.print(f"[red]Deployment failed: {e}[/red]")
        raise typer.Exit(code=1)

    raise typer.Exit(code=0)


@app.command("list")
def list_configs(
    env: str = typer.Option(
        ...,
        "--env",
        "-e",
        help="Target environment (dev, staging, prod)",
    ),
) -> None:
    """List all deployed source configurations."""
    from rich.table import Table

    environment = _validate_environment(env)

    async def run_list() -> None:
        deployer = SourceConfigDeployer(environment)
        try:
            await deployer.connect()
            configs = await deployer.list_configs()

            if not configs:
                console.print(
                    f"[yellow]No configurations deployed in {environment}[/yellow]"
                )
                return

            table = Table(title=f"Deployed Configurations ({environment})")
            table.add_column("Source ID", style="cyan")
            table.add_column("Display Name", style="white")
            table.add_column("Enabled", style="green")
            table.add_column("Version", style="blue")
            table.add_column("Deployed At", style="dim")
            table.add_column("Deployed By", style="dim")

            for config in configs:
                enabled = "[green]Yes[/green]" if config.enabled else "[red]No[/red]"
                deployed_at = config.deployed_at.strftime("%Y-%m-%d %H:%M")
                table.add_row(
                    config.source_id,
                    config.display_name,
                    enabled,
                    str(config.version),
                    deployed_at,
                    config.deployed_by,
                )

            console.print(table)
            console.print(f"\n[dim]Total: {len(configs)} configuration(s)[/dim]")
        finally:
            await deployer.disconnect()

    try:
        asyncio.run(run_list())
    except Exception as e:
        console.print(f"[red]Error listing configurations: {e}[/red]")
        raise typer.Exit(code=1)

    raise typer.Exit(code=0)


@app.command()
def diff(
    env: str = typer.Option(
        ...,
        "--env",
        "-e",
        help="Target environment (dev, staging, prod)",
    ),
    source: str | None = typer.Option(
        None,
        "--source",
        "-s",
        help="Specific source_id to diff (diffs all if not specified)",
    ),
) -> None:
    """Show differences between local configs and deployed MongoDB."""
    from deepdiff import DeepDiff
    from rich.panel import Panel

    environment = _validate_environment(env)
    settings = get_settings()

    # Load local configs
    files = get_source_config_files(settings.config_dir)
    if not files:
        console.print(f"[yellow]No YAML files found in {settings.config_dir}[/yellow]")
        raise typer.Exit(code=0)

    try:
        local_configs = load_source_configs(files)
    except Exception as e:
        console.print(f"[red]Error loading local configurations: {e}[/red]")
        raise typer.Exit(code=1)

    # Filter by source_id if specified
    if source:
        local_configs = [c for c in local_configs if c.source_id == source]
        if not local_configs:
            console.print(f"[red]Source ID '{source}' not found locally[/red]")
            raise typer.Exit(code=1)

    async def run_diff() -> None:
        deployer = SourceConfigDeployer(environment)
        try:
            await deployer.connect()
            has_diff = False

            for local_config in local_configs:
                deployed = await deployer.get_config(local_config.source_id)

                if deployed is None:
                    console.print(
                        Panel(
                            "[green]NEW[/green] - Not yet deployed",
                            title=f"[cyan]{local_config.source_id}[/cyan]",
                        )
                    )
                    has_diff = True
                    continue

                # Compare configs
                local_dict = {
                    "ingestion": local_config.model_dump()["ingestion"],
                    "validation": local_config.model_dump().get("validation"),
                    "transformation": local_config.model_dump()["transformation"],
                    "storage": local_config.model_dump()["storage"],
                }
                deployed_dict = deployed.config

                diff_result = DeepDiff(
                    deployed_dict, local_dict, ignore_order=True, verbose_level=2
                )

                if diff_result:
                    has_diff = True
                    src_id = local_config.source_id
                    title = f"[cyan]{src_id}[/cyan] (v{deployed.version})"
                    console.print(
                        Panel(
                            title=title,
                            renderable=_format_diff(diff_result),
                        )
                    )
                else:
                    console.print(f"[dim]{local_config.source_id}: No changes[/dim]")

            if not has_diff:
                sync_msg = "All configurations are in sync with deployed versions"
                console.print(f"\n[green]{sync_msg}[/green]")
        finally:
            await deployer.disconnect()

    try:
        asyncio.run(run_diff())
    except Exception as e:
        console.print(f"[red]Error comparing configurations: {e}[/red]")
        raise typer.Exit(code=1)

    raise typer.Exit(code=0)


def _format_diff(diff_result: dict) -> str:
    """Format a DeepDiff result for display."""
    lines = []

    if "values_changed" in diff_result:
        lines.append("[yellow]Changed values:[/yellow]")
        for path, change in diff_result["values_changed"].items():
            old = change["old_value"]
            new = change["new_value"]
            lines.append(f"  {path}: [red]{old}[/red] → [green]{new}[/green]")

    if "dictionary_item_added" in diff_result:
        lines.append("[green]Added:[/green]")
        for item in diff_result["dictionary_item_added"]:
            lines.append(f"  [green]+ {item}[/green]")

    if "dictionary_item_removed" in diff_result:
        lines.append("[red]Removed:[/red]")
        for item in diff_result["dictionary_item_removed"]:
            lines.append(f"  [red]- {item}[/red]")

    if "type_changes" in diff_result:
        lines.append("[yellow]Type changes:[/yellow]")
        for path, change in diff_result["type_changes"].items():
            lines.append(f"  {path}: type changed")

    return "\n".join(lines) if lines else "[dim]No details available[/dim]"


@app.command()
def history(
    env: str = typer.Option(
        ...,
        "--env",
        "-e",
        help="Target environment (dev, staging, prod)",
    ),
    source: str = typer.Option(
        ...,
        "--source",
        "-s",
        help="Source ID to get history for",
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-l",
        help="Maximum number of history entries to show",
    ),
) -> None:
    """Show deployment history for a source configuration."""
    from rich.table import Table

    environment = _validate_environment(env)

    async def run_history() -> None:
        deployer = SourceConfigDeployer(environment)
        try:
            await deployer.connect()
            history_entries = await deployer.get_history(source, limit=limit)

            if not history_entries:
                console.print(
                    f"[yellow]No history found for '{source}' in {environment}[/yellow]"
                )
                return

            table = Table(title=f"Deployment History: {source} ({environment})")
            table.add_column("Version", style="blue")
            table.add_column("Deployed At", style="dim")
            table.add_column("Deployed By", style="dim")
            table.add_column("Git SHA", style="cyan")

            for entry in history_entries:
                deployed_at = entry.deployed_at.strftime("%Y-%m-%d %H:%M:%S")
                git_sha = entry.git_sha or "[dim]N/A[/dim]"
                table.add_row(
                    str(entry.version),
                    deployed_at,
                    entry.deployed_by,
                    git_sha,
                )

            console.print(table)
            console.print(
                f"\n[dim]Showing {len(history_entries)} of up to {limit} entries[/dim]"
            )
        finally:
            await deployer.disconnect()

    try:
        asyncio.run(run_history())
    except Exception as e:
        console.print(f"[red]Error fetching history: {e}[/red]")
        raise typer.Exit(code=1)

    raise typer.Exit(code=0)


@app.command()
def rollback(
    env: str = typer.Option(
        ...,
        "--env",
        "-e",
        help="Target environment (dev, staging, prod)",
    ),
    source: str = typer.Option(
        ...,
        "--source",
        "-s",
        help="Source ID to rollback",
    ),
    version: int = typer.Option(
        ...,
        "--version",
        "-v",
        help="Version number to rollback to",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-y",
        help="Skip confirmation prompt",
    ),
) -> None:
    """Rollback a source configuration to a previous version."""
    environment = _validate_environment(env)

    # Confirm rollback unless --force is used
    if not force:
        confirm = typer.confirm(
            f"Rollback '{source}' to version {version} in {environment}?"
        )
        if not confirm:
            console.print("[yellow]Rollback cancelled[/yellow]")
            raise typer.Exit(code=0)

    async def run_rollback() -> None:
        deployer = SourceConfigDeployer(environment)
        try:
            await deployer.connect()
            action = await deployer.rollback(source, version)

            if action is None:
                msg = f"Version {version} not found for '{source}'"
                console.print(f"[red]Rollback failed: {msg}[/red]")
                raise typer.Exit(code=1)

            msg = f"Successfully rolled back '{source}' to version {version}"
            console.print(f"[green]{msg}[/green]")
            console.print(
                f"[dim]New version: {action.version} ({action.message})[/dim]"
            )
        finally:
            await deployer.disconnect()

    try:
        asyncio.run(run_rollback())
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Rollback failed: {e}[/red]")
        raise typer.Exit(code=1)

    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
