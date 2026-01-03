# Factory Portal Docker Build
# Multi-stage build with nginx for serving static files

# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

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

# Stage 2: Production
FROM nginx:alpine

# Copy built assets from builder stage
COPY --from=builder /app/web/factory-portal/dist /usr/share/nginx/html

# Copy nginx configuration for SPA routing
COPY web/factory-portal/nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
