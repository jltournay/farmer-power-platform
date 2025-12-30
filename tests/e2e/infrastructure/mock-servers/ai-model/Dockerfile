# Mock AI Model gRPC Server
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir grpcio grpcio-health-checking protobuf

# Copy fp-proto library (contains generated proto files)
COPY libs/fp-proto/src/fp_proto /app/fp_proto

# Copy server code
COPY tests/e2e/infrastructure/mock-servers/ai-model/server.py .

# Set Python path
ENV PYTHONPATH=/app

# Expose gRPC port
EXPOSE 50051

# Health check using grpc_health_probe pattern
# Note: Using Python-based health check since grpc_health_probe may not be available
HEALTHCHECK --interval=5s --timeout=5s --start-period=5s --retries=10 \
    CMD python -c "import grpc; channel = grpc.insecure_channel('localhost:50051'); grpc.channel_ready_future(channel).result(timeout=5)"

# Run server
CMD ["python", "server.py"]
