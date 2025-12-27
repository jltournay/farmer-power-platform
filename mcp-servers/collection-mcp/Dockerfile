# Collection MCP Server Dockerfile
FROM python:3.12-slim AS builder

WORKDIR /app

# Install poetry
RUN pip install poetry==1.7.0

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Copy local libraries (needed for dependency resolution)
COPY libs/fp-common /app/libs/fp-common
COPY libs/fp-proto /app/libs/fp-proto

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --only main

# Production stage
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/collection_mcp /app/collection_mcp

# Set Python path
ENV PYTHONPATH=/app

# Expose gRPC port
EXPOSE 50051

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import grpc; channel = grpc.insecure_channel('localhost:50051'); grpc.channel_ready_future(channel).result(timeout=5)"

# Run the server
CMD ["python", "-m", "collection_mcp.main"]
