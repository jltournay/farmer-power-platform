"""Source configuration validator.

Validates YAML source configuration files against the SourceConfig Pydantic schema.
"""

import sys
from pathlib import Path
from typing import NamedTuple

import yaml
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add fp-common to path for local development
sys.path.insert(0, str(Path(__file__).parents[4] / "libs" / "fp-common"))

from fp_common.models.source_config import SourceConfig


class ValidationResult(NamedTuple):
    """Result of validating a single source configuration file."""

    file_path: Path
    source_id: str | None
    is_valid: bool
    errors: list[str]


def load_yaml_file(file_path: Path) -> dict | None:
    """Load and parse a YAML file.

    Args:
        file_path: Path to the YAML file.

    Returns:
        Parsed YAML content as a dict, or None if parsing failed.
    """
    try:
        with open(file_path) as f:
            return yaml.safe_load(f)
    except yaml.YAMLError:
        return None


def validate_source_config(file_path: Path) -> ValidationResult:
    """Validate a single source configuration file.

    Args:
        file_path: Path to the YAML file to validate.

    Returns:
        ValidationResult with validation status and any errors.
    """
    errors: list[str] = []
    source_id: str | None = None

    # Load YAML file
    data = load_yaml_file(file_path)
    if data is None:
        return ValidationResult(
            file_path=file_path,
            source_id=None,
            is_valid=False,
            errors=["Failed to parse YAML file"],
        )

    # Extract source_id for reporting
    source_id = data.get("source_id")

    # Validate against Pydantic schema
    try:
        SourceConfig.model_validate(data)
        return ValidationResult(
            file_path=file_path,
            source_id=source_id,
            is_valid=True,
            errors=[],
        )
    except ValidationError as e:
        for error in e.errors():
            location = " -> ".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            errors.append(f"{location}: {message}")

        return ValidationResult(
            file_path=file_path,
            source_id=source_id,
            is_valid=False,
            errors=errors,
        )


def validate_source_configs(
    files: list[Path],
    console: Console | None = None,
) -> list[ValidationResult]:
    """Validate multiple source configuration files.

    Args:
        files: List of YAML file paths to validate.
        console: Rich console for output (optional).

    Returns:
        List of ValidationResult for each file.
    """
    if console is None:
        console = Console()

    results: list[ValidationResult] = []

    for file_path in files:
        result = validate_source_config(file_path)
        results.append(result)

    return results


def get_source_config_files(config_dir: str | Path) -> list[Path]:
    """Get all YAML source configuration files from a directory.

    Args:
        config_dir: Path to the source configs directory.

    Returns:
        List of YAML file paths.
    """
    config_path = Path(config_dir)
    if not config_path.exists():
        return []

    return sorted(config_path.glob("*.yaml"))


def print_validation_results(
    results: list[ValidationResult],
    console: Console | None = None,
) -> bool:
    """Print validation results to the console.

    Args:
        results: List of validation results.
        console: Rich console for output.

    Returns:
        True if all files are valid, False otherwise.
    """
    if console is None:
        console = Console()

    all_valid = all(r.is_valid for r in results)
    valid_count = sum(1 for r in results if r.is_valid)
    invalid_count = len(results) - valid_count

    # Create summary table
    table = Table(title="Validation Results")
    table.add_column("File", style="cyan")
    table.add_column("Source ID", style="blue")
    table.add_column("Status", style="green")

    for result in results:
        status = "[green]Valid[/green]" if result.is_valid else "[red]Invalid[/red]"
        source_id = result.source_id or "[dim]unknown[/dim]"
        table.add_row(result.file_path.name, source_id, status)

    console.print(table)

    # Print summary
    if all_valid:
        console.print(
            Panel(
                f"[green]All {len(results)} configuration(s) are valid.[/green]",
                title="Summary",
            )
        )
    else:
        invalid_str = f"[red]{invalid_count} invalid[/red]"
        valid_str = f"[green]{valid_count} valid[/green]"
        msg = f"{invalid_str}, {valid_str} out of {len(results)} configuration(s)."
        console.print(Panel(msg, title="Summary"))

        # Print detailed errors for invalid files
        console.print("\n[bold red]Validation Errors:[/bold red]\n")
        for result in results:
            if not result.is_valid:
                console.print(f"[bold]{result.file_path.name}[/bold]:")
                for error in result.errors:
                    console.print(f"  [red]• {error}[/red]")
                console.print()

    return all_valid
