FROM python:3.12-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy shared libs first (better caching)
COPY libs/fp-common /app/libs/fp-common
COPY libs/fp-proto /app/libs/fp-proto

# Copy BFF service
COPY services/bff /app/services/bff

# Install dependencies
RUN pip install --no-cache-dir \
    /app/libs/fp-common \
    /app/libs/fp-proto \
    /app/services/bff

EXPOSE 8080

CMD ["uvicorn", "bff.main:app", "--host", "0.0.0.0", "--port", "8080"]
