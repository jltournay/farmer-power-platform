# Collection MCP Server Dockerfile
# Python 3.12 with multi-stage build for minimal image size
# MUST be built from repository root: docker build -f mcp-servers/collection-mcp/Dockerfile .

# ============================================================================
# BASE STAGE
# ============================================================================
FROM python:3.12-slim as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.0

# Configure Poetry to not create virtualenvs
RUN poetry config virtualenvs.create false

# ============================================================================
# BUILDER STAGE
# ============================================================================
FROM base as builder

# Maintain repository structure for relative path resolution
WORKDIR /app

# Copy shared libs first (for caching) - maintain structure for poetry paths
COPY libs/ /app/libs/

# Copy MCP server files maintaining directory structure
COPY mcp-servers/collection-mcp/ /app/mcp-servers/collection-mcp/

# Change to MCP server directory where pyproject.toml expects relative paths to work
WORKDIR /app/mcp-servers/collection-mcp

# Install dependencies (without dev dependencies)
# The relative path ../../libs/fp-proto will now resolve correctly
RUN poetry install --no-interaction --no-ansi --no-root --only main 2>/dev/null || \
    poetry install --no-interaction --no-ansi --no-root

# ============================================================================
# RUNTIME STAGE
# ============================================================================
FROM python:3.12-slim as runtime

WORKDIR /app

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash appuser

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code and set ownership
COPY --from=builder --chown=appuser:appgroup /app/mcp-servers/collection-mcp/src/ ./src/
COPY --from=builder --chown=appuser:appgroup /app/libs/fp-proto/src/ ./libs/fp-proto/src/
COPY --from=builder --chown=appuser:appgroup /app/libs/fp-common/fp_common/ ./libs/fp-common/fp_common/

# Set Python path
ENV PYTHONPATH=/app/src:/app/libs/fp-proto/src:/app/libs/fp-common
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER appuser

# Expose gRPC port
EXPOSE 50051

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import grpc; channel = grpc.insecure_channel('localhost:50051'); grpc.channel_ready_future(channel).result(timeout=5)"

# Run the server
CMD ["python", "-m", "collection_mcp.main"]
