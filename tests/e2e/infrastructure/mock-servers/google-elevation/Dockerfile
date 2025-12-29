# Google Elevation API Mock Server
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn pydantic

# Copy server code
COPY server.py .

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=5s --timeout=5s --start-period=3s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

# Run server
CMD ["python", "server.py"]
