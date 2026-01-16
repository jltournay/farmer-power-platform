# Unified NGINX Reverse Proxy for E2E Testing
# Serves both portals at /admin and /factory, proxies /api to BFF

FROM nginx:alpine

# Copy unified nginx configuration
COPY deploy/docker/nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD wget -q --spider http://localhost/health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
