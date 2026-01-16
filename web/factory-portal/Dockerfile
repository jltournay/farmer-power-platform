# Factory Portal Docker Build
# Multi-stage build - outputs built static files for NGINX to serve

# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Build args for Vite (available at BUILD time only)
ARG VITE_BASE_URL=/factory/
ARG VITE_MOCK_JWT_SECRET=default-test-secret-for-development-32-chars
ARG VITE_AUTH_PROVIDER=mock

# Make build args available as env vars for Vite build
ENV VITE_BASE_URL=${VITE_BASE_URL}
ENV VITE_MOCK_JWT_SECRET=${VITE_MOCK_JWT_SECRET}
ENV VITE_AUTH_PROVIDER=${VITE_AUTH_PROVIDER}

# Copy root package files for workspace setup
COPY package*.json ./

# Copy workspace package.json files
COPY libs/ui-components/package.json ./libs/ui-components/
COPY libs/auth/package.json ./libs/auth/
COPY web/factory-portal/package.json ./web/factory-portal/

# Install all dependencies
RUN npm ci

# Copy source files for shared libraries
COPY libs/ui-components/ ./libs/ui-components/
COPY libs/auth/ ./libs/auth/

# Build shared libraries first
WORKDIR /app/libs/ui-components
RUN npm run build

WORKDIR /app/libs/auth
RUN npm run build

# Copy factory portal source
WORKDIR /app
COPY web/factory-portal/ ./web/factory-portal/

# Build factory portal
WORKDIR /app/web/factory-portal
RUN npm run build

# Stage 2: Final image with just the built files
# This stage just provides the built files - NGINX copies them via volume
FROM alpine:latest

WORKDIR /app/web/factory-portal

# Copy built assets from builder stage
COPY --from=builder /app/web/factory-portal/dist ./dist

# Container exits immediately after copying - used as volume source
CMD ["echo", "Factory Portal build complete"]
