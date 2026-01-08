"""Farmer Power RAG Knowledge Document CLI.

Command-line interface for managing RAG knowledge documents
for the AI Model service.
"""

import asyncio
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from fp_knowledge.client import KnowledgeClient
from fp_knowledge.models import (
    DocumentStatus,
    JobStatus,
    KnowledgeDomain,
    VectorizationJobStatus,
)
from fp_knowledge.settings import Environment, get_settings
from fp_knowledge.validator import validate_document_yaml

app = typer.Typer(
    name="fp-knowledge",
    help="Manage RAG knowledge documents for Farmer Power AI Model",
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


def _status_style(status: DocumentStatus | str) -> str:
    """Get Rich style for document status."""
    status_val = status.value if isinstance(status, DocumentStatus) else status
    return {
        "active": "[green]● active[/green]",
        "staged": "[yellow]○ staged[/yellow]",
        "draft": "[dim]○ draft[/dim]",
        "archived": "[dim]· archived[/dim]",
    }.get(status_val, status_val)


@app.command()
def validate(
    file: str = typer.Option(
        ...,
        "--file",
        "-f",
        help="Path to the document YAML file to validate",
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
    """Validate a document YAML file against the schema without deploying.

    Examples:
        fp-knowledge validate -f documents/blister-blight.yaml
        fp-knowledge validate -f documents/blister-blight.yaml --verbose
    """
    file_path = Path(file)
    if not file_path.exists():
        _print_error(f"File not found: {file}")
        raise typer.Exit(code=1)

    result = validate_document_yaml(file_path)

    if result.is_valid:
        if not quiet:
            console.print(f"[green]✓ Valid:[/green] {file}")
            if verbose and result.document:
                doc_id = result.document.document_id
                console.print(f"  [dim]document_id:[/dim] {doc_id}")
                console.print(f"  [dim]title:[/dim] {result.document.title}")
                console.print(f"  [dim]domain:[/dim] {result.document.domain.value}")
                if result.document.content:
                    content_len = len(result.document.content)
                    console.print(f"  [dim]content:[/dim] {content_len} characters")
                if result.document.file:
                    console.print(f"  [dim]file:[/dim] {result.document.file}")
        if result.warnings:
            for warning in result.warnings:
                console.print(f"  [yellow]⚠ {warning}[/yellow]")
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
        help="Path to the document YAML file or source file (PDF/MD) to deploy",
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
    """Deploy a document YAML file to the AI Model service.

    Validates the YAML file first, then uploads via gRPC.
    For PDF/MD files referenced in YAML, triggers extraction after upload.

    Examples:
        fp-knowledge deploy -f documents/blister-blight.yaml --env dev
        fp-knowledge deploy -f documents/blister-blight.yaml --env staging --dry-run
    """
    environment = _validate_environment(env)
    file_path = Path(file)

    if not file_path.exists():
        _print_error(f"File not found: {file}")
        raise typer.Exit(code=1)

    # First validate the YAML
    result = validate_document_yaml(file_path)
    if not result.is_valid:
        _print_error(f"Validation failed for {file}")
        for error in result.errors:
            err_console.print(f"  [red]• {error}[/red]")
        raise typer.Exit(code=1)

    document = result.document
    if document is None:
        _print_error("Document validation returned no document object")
        raise typer.Exit(code=1)

    if dry_run:
        console.print("[yellow]Dry run - no changes will be made[/yellow]")
        console.print(f"Would deploy to [cyan]{environment}[/cyan] environment:")
        console.print(f"  document_id: {document.document_id}")
        console.print(f"  title: {document.title}")
        console.print(f"  domain: {document.domain.value}")
        if document.content:
            console.print(f"  content: {len(document.content)} characters")
        if document.file:
            console.print(f"  file: {document.file} (will trigger extraction)")
        raise typer.Exit(code=0)

    async def run_deploy() -> None:
        settings = get_settings()
        client = KnowledgeClient(settings, environment)
        try:
            await client.connect()

            # Create the document
            created_doc = await client.create(document)

            if not quiet:
                doc_id = created_doc.document_id
                version = created_doc.version
                console.print(f"[green]✓ Deployed:[/green] {doc_id} v{version}")
                if verbose:
                    console.print(f"  [dim]id:[/dim] {created_doc.id}")
                    console.print(f"  [dim]status:[/dim] {created_doc.status.value}")
                    console.print(f"  [dim]environment:[/dim] {environment}")

            # If file reference, trigger extraction
            if document.file:
                job_id = await client.extract(created_doc.document_id)
                console.print(f"  [dim]Extraction started:[/dim] {job_id}")
                msg = f"  Use: fp-knowledge job-status --job-id {job_id}"
                console.print(f"{msg} --env {environment}")
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
def list_documents(
    env: str = typer.Option(
        ...,
        "--env",
        "-e",
        help="Target environment (dev, staging, prod)",
    ),
    domain: str | None = typer.Option(
        None,
        "--domain",
        "-d",
        help="Filter by domain (plant_diseases, tea_cultivation, etc.)",
    ),
    status: str | None = typer.Option(
        None,
        "--status",
        "-s",
        help="Filter by status (draft, staged, active, archived)",
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
    """List all RAG documents in the specified environment.

    Examples:
        fp-knowledge list --env dev
        fp-knowledge list --env dev --domain plant_diseases
        fp-knowledge list --env dev --status active
    """
    environment = _validate_environment(env)

    # Validate domain if provided
    if domain:
        valid_domains = [d.value for d in KnowledgeDomain]
        if domain not in valid_domains:
            opts = ", ".join(valid_domains)
            _print_error(f"Invalid domain '{domain}'. Must be one of: {opts}")
            raise typer.Exit(code=1)

    # Validate status if provided
    if status:
        valid_statuses = [s.value for s in DocumentStatus]
        if status not in valid_statuses:
            opts = ", ".join(valid_statuses)
            _print_error(f"Invalid status '{status}'. Must be one of: {opts}")
            raise typer.Exit(code=1)

    async def run_list() -> None:
        settings = get_settings()
        client = KnowledgeClient(settings, environment)
        try:
            await client.connect()
            documents, total_count = await client.list_documents(
                domain=domain,
                status=status,
            )

            if not documents:
                if not quiet:
                    msg = f"No documents found in {environment}"
                    console.print(f"[yellow]{msg}[/yellow]")
                return

            table = Table(title=f"RAG Documents ({environment})")
            table.add_column("Document ID", style="cyan")
            table.add_column("Version", style="blue")
            table.add_column("Title", style="white", max_width=40)
            table.add_column("Domain", style="white")
            table.add_column("Status", style="white")
            if verbose:
                table.add_column("Updated At", style="dim")

            for doc in documents:
                row = [
                    doc.document_id,
                    str(doc.version),
                    doc.title,
                    doc.domain,
                    _status_style(doc.status),
                ]
                if verbose and doc.updated_at:
                    row.append(doc.updated_at.strftime("%Y-%m-%d %H:%M"))
                elif verbose:
                    row.append("-")
                table.add_row(*row)

            console.print(table)
            console.print(f"\n[dim]Total: {total_count} document(s)[/dim]")
        finally:
            await client.disconnect()

    try:
        asyncio.run(run_list())
    except typer.Exit:
        raise
    except Exception as e:
        _print_error(f"Error listing documents: {e}")
        raise typer.Exit(code=1)


@app.command()
def get(
    document_id: str = typer.Option(
        ...,
        "--document-id",
        "-d",
        help="The document ID to retrieve",
    ),
    env: str = typer.Option(
        ...,
        "--env",
        "-e",
        help="Target environment (dev, staging, prod)",
    ),
    version: int | None = typer.Option(
        None,
        "--version",
        "-V",
        help="Specific version to retrieve (defaults to active)",
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
    """Get a specific document by document_id.

    If no version specified, returns active version.

    Examples:
        fp-knowledge get --document-id blister-blight-guide --env dev
        fp-knowledge get --document-id blister-blight-guide --env dev --version 2
        fp-knowledge get --document-id blister-blight-guide --env dev --output doc.yaml
    """
    environment = _validate_environment(env)

    async def run_get() -> None:
        settings = get_settings()
        client = KnowledgeClient(settings, environment)
        try:
            await client.connect()

            if version:
                doc = await client.get_by_version(document_id, version)
                if not doc:
                    msg = f"Document '{document_id}' version {version} not found"
                    _print_error(msg)
                    raise typer.Exit(code=1)
            else:
                doc = await client.get_by_id(document_id)
                if not doc:
                    _print_error(f"No active document found for '{document_id}'")
                    raise typer.Exit(code=1)

            # Convert to YAML-friendly dict
            doc_dict = doc.model_dump(mode="json")
            # Remove internal id field for export
            doc_dict.pop("id", None)

            yaml_output = yaml.dump(
                doc_dict,
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
        _print_error(f"Error getting document: {e}")
        raise typer.Exit(code=1)


@app.command()
def stage(
    file: str = typer.Option(
        ...,
        "--file",
        "-f",
        help="Path to the document YAML file to stage",
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
    """Stage a new document version with status=staged.

    Creates a new version of the document with staged status.

    Examples:
        fp-knowledge stage -f documents/blister-blight-v2.yaml --env dev
    """
    environment = _validate_environment(env)
    file_path = Path(file)

    if not file_path.exists():
        _print_error(f"File not found: {file}")
        raise typer.Exit(code=1)

    # Validate the YAML
    result = validate_document_yaml(file_path)
    if not result.is_valid:
        _print_error(f"Validation failed for {file}")
        for error in result.errors:
            err_console.print(f"  [red]• {error}[/red]")
        raise typer.Exit(code=1)

    document = result.document
    if document is None:
        _print_error("Document validation returned no document object")
        raise typer.Exit(code=1)

    async def run_stage() -> None:
        settings = get_settings()
        client = KnowledgeClient(settings, environment)
        try:
            await client.connect()

            # Create and stage the document
            created_doc = await client.create(document)
            doc_id = created_doc.document_id
            staged_doc = await client.stage(doc_id, created_doc.version)

            if not quiet:
                version = staged_doc.version
                console.print(f"[green]✓ Staged:[/green] {doc_id} v{version}")
                if verbose:
                    console.print(f"  [dim]status:[/dim] {staged_doc.status.value}")
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
    document_id: str = typer.Option(
        ...,
        "--document-id",
        "-d",
        help="The document ID to promote",
    ),
    env: str = typer.Option(
        ...,
        "--env",
        "-e",
        help="Target environment (dev, staging, prod)",
    ),
    async_mode: bool = typer.Option(
        False,
        "--async",
        help="Return immediately with job_id (triggers chunking workflow)",
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
    """Promote a staged document to active.

    Archives the current active version (if exists) and activates the staged version.
    Triggers chunking workflow for the promoted document.

    Examples:
        fp-knowledge promote --document-id blister-blight-guide --env dev
        fp-knowledge promote --document-id blister-blight-guide --env dev --async
    """
    environment = _validate_environment(env)

    async def run_promote() -> None:
        settings = get_settings()
        client = KnowledgeClient(settings, environment)
        try:
            await client.connect()

            # Find latest staged version
            versions = await client.list_versions(document_id)
            staged_versions = [v for v in versions if v.status == DocumentStatus.STAGED]

            if not staged_versions:
                _print_error(f"No staged version found for '{document_id}'")
                raise typer.Exit(code=1)

            latest_staged = staged_versions[0]  # Already sorted by version desc

            # Activate the staged version
            activated_doc = await client.activate(document_id, latest_staged.version)

            if not quiet:
                console.print(
                    f"[green]✓ Promoted:[/green] {document_id} v{activated_doc.version}"
                )
                if verbose:
                    console.print(f"  [dim]status:[/dim] {activated_doc.status.value}")

            # Trigger chunking workflow
            chunk_result = await client.chunk(document_id, activated_doc.version)
            if not quiet:
                console.print(
                    f"  [dim]Chunks created:[/dim] {chunk_result.chunks_created}"
                )
                console.print(
                    f"  [dim]Total words:[/dim] {chunk_result.total_word_count}"
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
    document_id: str = typer.Option(
        ...,
        "--document-id",
        "-d",
        help="The document ID to rollback",
    ),
    to_version: int = typer.Option(
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
    """Rollback to a previous version of a document.

    Archives current active version and creates new version from rollback target.

    Examples:
        fp-knowledge rollback -d blister-blight-guide --to-version 1 --env dev
    """
    environment = _validate_environment(env)

    async def run_rollback() -> None:
        settings = get_settings()
        client = KnowledgeClient(settings, environment)
        try:
            await client.connect()

            new_doc = await client.rollback(document_id, to_version)

            if not quiet:
                console.print(
                    f"[green]✓ Rolled back:[/green] {document_id} to v{to_version}"
                )
                console.print(f"  [dim]New version:[/dim] v{new_doc.version}")
                if verbose:
                    console.print(f"  [dim]status:[/dim] {new_doc.status.value}")
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
    document_id: str = typer.Option(
        ...,
        "--document-id",
        "-d",
        help="The document ID to list versions for",
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
    """List all versions of a document.

    Examples:
        fp-knowledge versions --document-id blister-blight-guide --env dev
    """
    environment = _validate_environment(env)

    async def run_versions() -> None:
        settings = get_settings()
        client = KnowledgeClient(settings, environment)
        try:
            await client.connect()
            docs = await client.list_versions(document_id)

            if not docs:
                if not quiet:
                    msg = f"No versions found for '{document_id}' in {environment}"
                    console.print(f"[yellow]{msg}[/yellow]")
                return

            table = Table(title=f"Versions of {document_id} ({environment})")
            table.add_column("Version", style="blue")
            table.add_column("Status", style="white")
            table.add_column("Title", style="white", max_width=40)
            if verbose:
                table.add_column("Updated At", style="dim")
                table.add_column("Author", style="dim")

            for doc in docs:
                row = [
                    str(doc.version),
                    _status_style(doc.status),
                    doc.title,
                ]
                if verbose:
                    if doc.updated_at:
                        updated_at = doc.updated_at.strftime("%Y-%m-%d %H:%M")
                    else:
                        updated_at = "-"
                    row.append(updated_at)
                    row.append(doc.metadata.author)
                table.add_row(*row)

            console.print(table)
            console.print(f"\n[dim]Total: {len(docs)} version(s)[/dim]")
        finally:
            await client.disconnect()

    try:
        asyncio.run(run_versions())
    except typer.Exit:
        raise
    except Exception as e:
        _print_error(f"Error listing versions: {e}")
        raise typer.Exit(code=1)


@app.command("job-status")
def job_status(
    job_id: str = typer.Option(
        ...,
        "--job-id",
        "-j",
        help="The extraction job ID to track",
    ),
    env: str = typer.Option(
        ...,
        "--env",
        "-e",
        help="Target environment (dev, staging, prod)",
    ),
    stream: bool = typer.Option(
        True,
        "--stream/--poll",
        help="Use gRPC streaming (default) or polling mode",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output",
    ),
) -> None:
    """Track extraction job progress with real-time updates.

    Uses gRPC streaming by default for real-time progress.
    Use --poll for fallback polling mode (interval-based).

    Examples:
        fp-knowledge job-status --job-id abc-123 --env dev
        fp-knowledge job-status --job-id abc-123 --env dev --poll
    """
    environment = _validate_environment(env)

    async def run_streaming() -> None:
        settings = get_settings()
        client = KnowledgeClient(settings, environment)
        try:
            await client.connect()

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("| {task.fields[pages]}"),
                console=console,
            ) as progress:
                task = progress.add_task("Extracting...", total=100, pages="0/? pages")

                async for event in client.stream_progress(job_id):
                    pages_text = f"{event.pages_processed}/{event.total_pages} pages"
                    progress.update(
                        task,
                        completed=event.progress_percent,
                        pages=pages_text,
                    )

                    if event.status == JobStatus.COMPLETED:
                        progress.update(task, completed=100)
                        console.print("[green]✓ Extraction complete[/green]")
                        break
                    elif event.status == JobStatus.FAILED:
                        progress.update(task, completed=0)
                        _print_error(event.error_message or "Unknown error")
                        raise typer.Exit(code=1)
        finally:
            await client.disconnect()

    async def run_polling() -> None:
        settings = get_settings()
        client = KnowledgeClient(settings, environment)
        try:
            await client.connect()

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("| {task.fields[pages]}"),
                console=console,
            ) as progress:
                task = progress.add_task("Extracting...", total=100, pages="0/? pages")

                while True:
                    result = await client.get_job_status(job_id)
                    pages_text = f"{result.pages_processed}/{result.total_pages} pages"
                    progress.update(
                        task,
                        completed=result.progress_percent,
                        pages=pages_text,
                    )

                    if result.status == JobStatus.COMPLETED:
                        progress.update(task, completed=100)
                        console.print("[green]✓ Extraction complete[/green]")
                        if verbose:
                            doc_id = result.document_id
                            console.print(f"  [dim]document_id:[/dim] {doc_id}")
                            if result.completed_at:
                                console.print(
                                    f"  [dim]completed_at:[/dim] {result.completed_at}"
                                )
                        break
                    elif result.status == JobStatus.FAILED:
                        progress.update(task, completed=0)
                        _print_error(result.error_message or "Unknown error")
                        raise typer.Exit(code=1)

                    await asyncio.sleep(settings.poll_interval)
        finally:
            await client.disconnect()

    try:
        if stream:
            asyncio.run(run_streaming())
        else:
            asyncio.run(run_polling())
    except typer.Exit:
        raise
    except Exception as e:
        _print_error(f"Error tracking job: {e}")
        raise typer.Exit(code=1)


# ========================================
# Vectorization Commands (Story 0.75.13c)
# ========================================


def _vectorization_status_style(status: VectorizationJobStatus | str) -> str:
    """Get Rich style for vectorization job status."""
    status_val = status.value if isinstance(status, VectorizationJobStatus) else status
    return {
        "completed": "[green]● completed[/green]",
        "in_progress": "[yellow]○ in_progress[/yellow]",
        "pending": "[dim]○ pending[/dim]",
        "failed": "[red]✗ failed[/red]",
        "partial": "[yellow]⚠ partial[/yellow]",
    }.get(status_val, status_val)


@app.command()
def vectorize(
    document_id: str = typer.Option(
        ...,
        "--document-id",
        "-d",
        help="The document ID to vectorize",
    ),
    env: str = typer.Option(
        ...,
        "--env",
        "-e",
        help="Target environment (dev, staging, prod)",
    ),
    version: int = typer.Option(
        0,
        "--version",
        "-V",
        help="Specific version to vectorize (0 = latest active/staged)",
    ),
    async_mode: bool = typer.Option(
        False,
        "--async",
        help="Return immediately with job_id instead of waiting for completion",
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
    """Vectorize a document by generating embeddings and storing in Pinecone.

    Generates embeddings for document chunks and stores them in the
    Pinecone vector database for similarity search.

    Examples:
        fp-knowledge vectorize --document-id blister-blight-guide --env dev
        fp-knowledge vectorize --document-id blister-blight-guide --env dev --version 2
        fp-knowledge vectorize --document-id blister-blight-guide --env dev --async
    """
    environment = _validate_environment(env)

    async def run_vectorize() -> None:
        settings = get_settings()
        client = KnowledgeClient(settings, environment)
        try:
            await client.connect()

            if not quiet:
                console.print(
                    f"[dim]Vectorizing document {document_id}"
                    + (f" v{version}" if version > 0 else "")
                    + f" in {environment}...[/dim]"
                )

            result = await client.vectorize(
                document_id=document_id,
                version=version,
                async_mode=async_mode,
            )

            if async_mode:
                # Async mode - just print job_id and exit
                if not quiet:
                    console.print("[green]✓ Vectorization started[/green]")
                    console.print(f"  [dim]job_id:[/dim] {result.job_id}")
                    console.print(f"  [dim]status:[/dim] {result.status.value}")
                    console.print()
                    console.print(
                        f"Track progress with: [cyan]fp-knowledge vectorize-status "
                        f"--job-id {result.job_id} --env {environment}[/cyan]"
                    )
            else:
                # Sync mode - show full results
                if result.status == VectorizationJobStatus.COMPLETED:
                    console.print("[green]✓ Vectorization completed[/green]")
                elif result.status == VectorizationJobStatus.PARTIAL:
                    msg = "[yellow]⚠ Vectorization completed with errors[/yellow]"
                    console.print(msg)
                else:
                    console.print("[red]✗ Vectorization failed[/red]")
                    if result.error_message:
                        _print_error(result.error_message)
                    raise typer.Exit(code=1)

                console.print(f"  [dim]job_id:[/dim] {result.job_id}")
                console.print(f"  [dim]namespace:[/dim] {result.namespace or '-'}")
                console.print(f"  [dim]chunks_total:[/dim] {result.chunks_total}")
                chunks_emb = result.chunks_embedded
                console.print(f"  [dim]chunks_embedded:[/dim] {chunks_emb}")
                console.print(f"  [dim]chunks_stored:[/dim] {result.chunks_stored}")
                if result.failed_count > 0:
                    failed = result.failed_count
                    console.print(f"  [yellow]failed_count:[/yellow] {failed}")
                if verbose:
                    chash = result.content_hash or "-"
                    console.print(f"  [dim]content_hash:[/dim] {chash}")

        finally:
            await client.disconnect()

    try:
        asyncio.run(run_vectorize())
    except typer.Exit:
        raise
    except Exception as e:
        _print_error(f"Vectorization failed: {e}")
        raise typer.Exit(code=1)


@app.command("vectorize-status")
def vectorize_status(
    job_id: str = typer.Option(
        ...,
        "--job-id",
        "-j",
        help="The vectorization job ID to check",
    ),
    env: str = typer.Option(
        ...,
        "--env",
        "-e",
        help="Target environment (dev, staging, prod)",
    ),
    watch: bool = typer.Option(
        False,
        "--watch",
        "-w",
        help="Poll for updates until job completes",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output",
    ),
) -> None:
    """Get vectorization job status.

    Check the status of a vectorization job, optionally watching for completion.

    Examples:
        fp-knowledge vectorize-status --job-id abc-123 --env dev
        fp-knowledge vectorize-status --job-id abc-123 --env dev --watch
    """
    environment = _validate_environment(env)

    async def run_status() -> None:
        settings = get_settings()
        client = KnowledgeClient(settings, environment)
        try:
            await client.connect()

            if watch:
                # Watch mode - poll until complete
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TextColumn("| {task.fields[chunks]}"),
                    console=console,
                ) as progress:
                    task = progress.add_task(
                        "Vectorizing...",
                        total=100,
                        chunks="0/? chunks",
                    )

                    while True:
                        result = await client.get_vectorization_job_status(job_id)

                        if result is None:
                            progress.update(task, completed=0)
                            _print_error(f"Job not found: {job_id}")
                            raise typer.Exit(code=1)

                        # Calculate progress percentage
                        if result.chunks_total > 0:
                            pct = (result.chunks_stored / result.chunks_total) * 100
                        else:
                            pct = 0

                        stored = result.chunks_stored
                        total = result.chunks_total
                        chunks_text = f"{stored}/{total} chunks"
                        progress.update(task, completed=pct, chunks=chunks_text)

                        if result.status in (
                            VectorizationJobStatus.COMPLETED,
                            VectorizationJobStatus.PARTIAL,
                        ):
                            progress.update(task, completed=100)
                            console.print()
                            console.print(
                                f"[green]✓ Vectorization complete[/green] "
                                f"({stored} chunks stored)"
                            )
                            if result.failed_count > 0:
                                fc = result.failed_count
                                console.print(
                                    f"  [yellow]Warning: {fc} chunks failed[/yellow]"
                                )
                            break
                        elif result.status == VectorizationJobStatus.FAILED:
                            progress.update(task, completed=0)
                            _print_error(result.error_message or "Unknown error")
                            raise typer.Exit(code=1)

                        await asyncio.sleep(settings.poll_interval)
            else:
                # One-shot status check
                result = await client.get_vectorization_job_status(job_id)

                if result is None:
                    _print_error(f"Job not found: {job_id}")
                    raise typer.Exit(code=1)

                table = Table(title=f"Vectorization Job: {job_id}")
                table.add_column("Field", style="cyan")
                table.add_column("Value", style="white")

                table.add_row("Status", _vectorization_status_style(result.status))
                table.add_row("Document ID", result.document_id)
                table.add_row("Document Version", str(result.document_version))
                table.add_row("Namespace", result.namespace or "-")
                table.add_row("Chunks Total", str(result.chunks_total))
                table.add_row("Chunks Embedded", str(result.chunks_embedded))
                table.add_row("Chunks Stored", str(result.chunks_stored))
                if result.failed_count > 0:
                    fc = result.failed_count
                    table.add_row("Failed Count", f"[yellow]{fc}[/yellow]")

                if verbose:
                    table.add_row("Content Hash", result.content_hash or "-")
                    if result.started_at:
                        table.add_row(
                            "Started At",
                            result.started_at.strftime("%Y-%m-%d %H:%M:%S"),
                        )
                    if result.completed_at:
                        table.add_row(
                            "Completed At",
                            result.completed_at.strftime("%Y-%m-%d %H:%M:%S"),
                        )

                if result.error_message:
                    table.add_row("Error", f"[red]{result.error_message}[/red]")

                console.print(table)

        finally:
            await client.disconnect()

    try:
        asyncio.run(run_status())
    except typer.Exit:
        raise
    except Exception as e:
        _print_error(f"Error getting job status: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
