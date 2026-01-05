"""Farmer Power Prompt Configuration CLI.

Command-line interface for managing prompt configurations
for the AI Model service.
"""

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from fp_prompt_config.client import PromptClient
from fp_prompt_config.settings import Environment, get_settings
from fp_prompt_config.validator import validate_prompt_yaml

app = typer.Typer(
    name="fp-prompt-config",
    help="Manage prompt configurations for Farmer Power AI Model",
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
        help="Path to the prompt YAML file to validate",
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
    """Validate a prompt YAML file against the schema without deploying.

    Examples:
        fp-prompt-config validate -f prompts/disease-diagnosis.yaml
        fp-prompt-config validate -f prompts/disease-diagnosis.yaml --verbose
    """
    file_path = Path(file)
    if not file_path.exists():
        _print_error(f"File not found: {file}")
        raise typer.Exit(code=1)

    result = validate_prompt_yaml(file_path)

    if result.is_valid:
        if not quiet:
            console.print(f"[green]✓ Valid:[/green] {file}")
            if verbose and result.prompt:
                console.print(f"  [dim]prompt_id:[/dim] {result.prompt.prompt_id}")
                console.print(f"  [dim]agent_id:[/dim] {result.prompt.agent_id}")
                console.print(f"  [dim]version:[/dim] {result.prompt.version}")
                console.print(f"  [dim]status:[/dim] {result.prompt.status.value}")
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
        help="Path to the prompt YAML file to deploy",
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
    """Deploy a prompt YAML file to MongoDB.

    Validates the YAML file first, then uploads to the specified environment.
    For staged/active prompts, validates that the referenced agent_id exists.

    Examples:
        fp-prompt-config deploy -f prompts/diagnosis.yaml --env dev
        fp-prompt-config deploy -f prompts/diagnosis.yaml --env staging --dry-run
    """
    environment = _validate_environment(env)
    file_path = Path(file)

    if not file_path.exists():
        _print_error(f"File not found: {file}")
        raise typer.Exit(code=1)

    # First validate the YAML
    result = validate_prompt_yaml(file_path)
    if not result.is_valid:
        _print_error(f"Validation failed for {file}")
        for error in result.errors:
            err_console.print(f"  [red]• {error}[/red]")
        raise typer.Exit(code=1)

    prompt = result.prompt
    if prompt is None:
        _print_error("Prompt validation returned no prompt object")
        raise typer.Exit(code=1)

    if dry_run:
        console.print("[yellow]Dry run - no changes will be made[/yellow]")
        console.print(f"Would deploy to [cyan]{environment}[/cyan] environment:")
        console.print(f"  prompt_id: {prompt.prompt_id}")
        console.print(f"  version: {prompt.version}")
        console.print(f"  status: {prompt.status.value}")
        console.print(f"  agent_id: {prompt.agent_id}")
        raise typer.Exit(code=0)

    async def run_deploy() -> None:
        settings = get_settings()
        client = PromptClient(settings, environment)
        try:
            await client.connect()

            # Validate agent reference for staged/active prompts
            validation_error = await client.validate_agent_reference(prompt)
            if validation_error:
                _print_error(validation_error)
                raise typer.Exit(code=1)

            # Check if version already exists
            existing = await client.get_by_version(prompt.prompt_id, prompt.version)
            if existing:
                pid = prompt.prompt_id
                _print_error(f"Version {prompt.version} already exists for '{pid}'")
                raise typer.Exit(code=1)

            # Deploy the prompt
            await client.create(prompt)

            if not quiet:
                console.print(
                    f"[green]✓ Deployed:[/green] {prompt.prompt_id} v{prompt.version}"
                )
                if verbose:
                    console.print(f"  [dim]status:[/dim] {prompt.status.value}")
                    console.print(f"  [dim]agent_id:[/dim] {prompt.agent_id}")
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
def list_prompts(
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
    agent_id: str | None = typer.Option(
        None,
        "--agent-id",
        "-a",
        help="Filter by agent_id",
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
    """List all prompts in the specified environment.

    Examples:
        fp-prompt-config list --env dev
        fp-prompt-config list --env dev --status active
        fp-prompt-config list --env dev --agent-id diagnose-quality-issue
    """
    environment = _validate_environment(env)

    async def run_list() -> None:
        settings = get_settings()
        client = PromptClient(settings, environment)
        try:
            await client.connect()
            prompts = await client.list_prompts(status=status, agent_id=agent_id)

            if not prompts:
                if not quiet:
                    console.print(f"[yellow]No prompts found in {environment}[/yellow]")
                return

            table = Table(title=f"Prompts ({environment})")
            table.add_column("Prompt ID", style="cyan")
            table.add_column("Version", style="blue")
            table.add_column("Status", style="white")
            table.add_column("Agent ID", style="white")
            table.add_column("Updated At", style="dim")

            for prompt in prompts:
                status_style = {
                    "active": "[green]active[/green]",
                    "staged": "[yellow]staged[/yellow]",
                    "draft": "[dim]draft[/dim]",
                    "archived": "[dim]archived[/dim]",
                }.get(prompt.status.value, prompt.status.value)

                updated_at = prompt.metadata.updated_at.strftime("%Y-%m-%d %H:%M")
                table.add_row(
                    prompt.prompt_id,
                    prompt.version,
                    status_style,
                    prompt.agent_id,
                    updated_at,
                )

            console.print(table)
            console.print(f"\n[dim]Total: {len(prompts)} prompt(s)[/dim]")
        finally:
            await client.disconnect()

    try:
        asyncio.run(run_list())
    except typer.Exit:
        raise
    except Exception as e:
        _print_error(f"Error listing prompts: {e}")
        raise typer.Exit(code=1)


@app.command()
def get(
    prompt_id: str = typer.Option(
        ...,
        "--prompt-id",
        "-p",
        help="The prompt ID to retrieve",
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
    """Get a specific prompt by prompt_id.

    If no version specified, returns active version (or latest staged if none).

    Examples:
        fp-prompt-config get --prompt-id diagnosis --env dev
        fp-prompt-config get --prompt-id diagnosis --env dev --version 2.1.0
        fp-prompt-config get --prompt-id diagnosis --env dev --output out.yaml
    """
    environment = _validate_environment(env)

    async def run_get() -> None:
        import yaml

        settings = get_settings()
        client = PromptClient(settings, environment)
        try:
            await client.connect()

            if version:
                prompt = await client.get_by_version(prompt_id, version)
                if not prompt:
                    _print_error(f"Prompt '{prompt_id}' version {version} not found")
                    raise typer.Exit(code=1)
            else:
                # Try active first, then latest staged
                prompt = await client.get_active(prompt_id)
                if not prompt:
                    prompt = await client.get_latest_staged(prompt_id)
                if not prompt:
                    _print_error(f"No active or staged prompt found for '{prompt_id}'")
                    raise typer.Exit(code=1)

            # Convert to YAML-friendly dict
            prompt_dict = prompt.model_dump(mode="json")
            # Remove internal id field for export
            prompt_dict.pop("id", None)

            yaml_output = yaml.dump(
                prompt_dict,
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
        _print_error(f"Error getting prompt: {e}")
        raise typer.Exit(code=1)


@app.command()
def stage(
    file: str = typer.Option(
        ...,
        "--file",
        "-f",
        help="Path to the prompt YAML file to stage",
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
    """Stage a new prompt version with status=staged.

    Creates a new version of the prompt with staged status.
    Validates that the referenced agent_id exists.

    Examples:
        fp-prompt-config stage -f prompts/disease-diagnosis-v2.yaml --env dev
    """
    environment = _validate_environment(env)
    file_path = Path(file)

    if not file_path.exists():
        _print_error(f"File not found: {file}")
        raise typer.Exit(code=1)

    # Validate the YAML
    result = validate_prompt_yaml(file_path)
    if not result.is_valid:
        _print_error(f"Validation failed for {file}")
        for error in result.errors:
            err_console.print(f"  [red]• {error}[/red]")
        raise typer.Exit(code=1)

    prompt = result.prompt
    if prompt is None:
        _print_error("Prompt validation returned no prompt object")
        raise typer.Exit(code=1)

    # Override status to staged
    from fp_prompt_config.models import PromptStatus

    prompt = prompt.model_copy(update={"status": PromptStatus.STAGED})

    async def run_stage() -> None:
        settings = get_settings()
        client = PromptClient(settings, environment)
        try:
            await client.connect()

            # Validate agent reference (required for staged)
            validation_error = await client.validate_agent_reference(prompt)
            if validation_error:
                _print_error(validation_error)
                raise typer.Exit(code=1)

            # Check if version already exists
            existing = await client.get_by_version(prompt.prompt_id, prompt.version)
            if existing:
                pid = prompt.prompt_id
                _print_error(f"Version {prompt.version} already exists for '{pid}'")
                raise typer.Exit(code=1)

            # Stage the prompt
            await client.create(prompt)

            if not quiet:
                console.print(
                    f"[green]✓ Staged:[/green] {prompt.prompt_id} v{prompt.version}"
                )
                if verbose:
                    console.print(f"  [dim]agent_id:[/dim] {prompt.agent_id}")
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
    prompt_id: str = typer.Option(
        ...,
        "--prompt-id",
        "-p",
        help="The prompt ID to promote",
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
    """Promote a staged prompt to active.

    Archives the current active version (if exists) and promotes the staged version.

    Examples:
        fp-prompt-config promote --prompt-id disease-diagnosis --env dev
    """
    environment = _validate_environment(env)

    async def run_promote() -> None:
        settings = get_settings()
        client = PromptClient(settings, environment)
        try:
            await client.connect()

            result = await client.promote(prompt_id)

            if result.error:
                _print_error(result.error)
                raise typer.Exit(code=1)

            if not quiet:
                console.print(
                    f"[green]✓ Promoted:[/green] {prompt_id} v{result.promoted_version}"
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
    prompt_id: str = typer.Option(
        ...,
        "--prompt-id",
        "-p",
        help="The prompt ID to rollback",
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
    """Rollback to a previous version of a prompt.

    Archives current active version and creates new version from rollback target.

    Examples:
        fp-prompt-config rollback -p diagnosis --to-version 1.0.0 --env dev
    """
    environment = _validate_environment(env)

    async def run_rollback() -> None:
        settings = get_settings()
        client = PromptClient(settings, environment)
        try:
            await client.connect()

            result = await client.rollback(prompt_id, to_version)

            if result.error:
                _print_error(result.error)
                raise typer.Exit(code=1)

            if not quiet:
                console.print(
                    f"[green]✓ Rolled back:[/green] {prompt_id} to v{to_version}"
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
    prompt_id: str = typer.Option(
        ...,
        "--prompt-id",
        "-p",
        help="The prompt ID to list versions for",
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
    """List all versions of a prompt.

    Examples:
        fp-prompt-config versions --prompt-id disease-diagnosis --env dev
    """
    environment = _validate_environment(env)

    async def run_versions() -> None:
        settings = get_settings()
        client = PromptClient(settings, environment)
        try:
            await client.connect()
            prompts = await client.list_versions(prompt_id)

            if not prompts:
                if not quiet:
                    msg = f"No versions found for '{prompt_id}' in {environment}"
                    console.print(f"[yellow]{msg}[/yellow]")
                return

            table = Table(title=f"Versions of {prompt_id} ({environment})")
            table.add_column("Version", style="blue")
            table.add_column("Status", style="white")
            table.add_column("Updated At", style="dim")
            table.add_column("Author", style="dim")

            for prompt in prompts:
                status_style = {
                    "active": "[green]● active[/green]",
                    "staged": "[yellow]○ staged[/yellow]",
                    "draft": "[dim]○ draft[/dim]",
                    "archived": "[dim]· archived[/dim]",
                }.get(prompt.status.value, prompt.status.value)

                updated_at = prompt.metadata.updated_at.strftime("%Y-%m-%d %H:%M")
                table.add_row(
                    prompt.version,
                    status_style,
                    updated_at,
                    prompt.metadata.author,
                )

            console.print(table)
            console.print(f"\n[dim]Total: {len(prompts)} version(s)[/dim]")
        finally:
            await client.disconnect()

    try:
        asyncio.run(run_versions())
    except typer.Exit:
        raise
    except Exception as e:
        _print_error(f"Error listing versions: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
