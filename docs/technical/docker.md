# Docker Configuration

## Overview

VimbisoPay uses a multi-stage Docker build process with separate development and production configurations. The system runs three main services:
- Application (Django)
- Redis (State management)
- Mock WhatsApp server (Testing)

## Build Stages

### Base Stage
Common configuration for all builds:
```dockerfile
FROM python:3.13.0-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
    PYTHONUNBUFFERED=1
    LANG=en_US.UTF-8
    PORT=8000

# System dependencies
- curl
- redis-tools
- netcat-traditional
- gosu
- dnsutils
```

### Development Stage
Additional tools for development:
```dockerfile
FROM base AS development

# Development dependencies
- git
- build-essential
- procps

# Install dev requirements
RUN pip install -r requirements/dev.txt
```

### Production Stage
Optimized for security and performance:
```dockerfile
FROM base AS production

# Security features
- Non-privileged user (UID 10001)
- Minimal dependencies
- No build tools in final image

# Production requirements
RUN pip install --no-cache-dir -r requirements/prod.txt
```

## Service Configuration

### Application Service
```yaml
app:
  build:
    context: ..
    target: development  # or production
  ports:
    - "8000:8000"
  environment:
    - DJANGO_ENV=development
    - REDIS_URL=redis://redis:6379/0
  volumes:
    - ./data:/app/data
    - .:/app
  networks:
    - app-network
```

### Redis Service
```yaml
redis:
  image: redis:7.0-alpine
  command: >
    redis-server
    --maxmemory 256mb
    --maxmemory-policy allkeys-lru
  volumes:
    - ./data/redis:/data
  ports:
    - "6379:6379"
  networks:
    - app-network
```

### Mock Service
```yaml
mock:
  build:
    context: ..
    target: development
  volumes:
    - ../mock:/app/mock
  ports:
    - "8001:8001"
  networks:
    - app-network
```

## Network Architecture

```
Docker Network (app-network)
├── app service
│   ├── Internal: app:8000
│   └── External: localhost:8000
├── redis service
│   ├── Internal: redis:6379
│   └── External: localhost:6379
└── mock service
    ├── Internal: mock:8001
    └── External: localhost:8001
```

## Volume Management

### Development Volumes
```yaml
volumes:
  - ./data:/app/data  # Persistent data
  - .:/app           # Live code changes
```

### Production Volumes
```yaml
volumes:
  - ./data/redis:/data  # Redis persistence
```

## Health Checks

### Application
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health/ || exit 1
```

### Redis
```yaml
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 5s
  timeout: 3s
  retries: 3
```

## Security Considerations

### Production Hardening
1. **User Management**
   ```dockerfile
   RUN adduser \
       --disabled-password \
       --shell "/sbin/nologin" \
       --no-create-home \
       --uid "${UID}" \
       appuser
   ```

2. **Permissions**
   ```dockerfile
   RUN chown -R appuser:appuser /app \
       && chmod -R 755 /app/data \
       && find /app/data -type d -exec chmod 755 {} \; \
       && find /app/data -type f -exec chmod 644 {} \;
   ```

3. **Dependency Management**
   ```dockerfile
   # Keep only runtime dependencies
   RUN apt-mark manual redis-tools curl gosu dnsutils netcat-traditional && \
       apt-get purge -y build-essential && \
       apt-get autoremove -y
   ```

## Development Workflow

### Starting Services
```bash
# Development mode
make dev-build
make dev-up

# Production mode
make prod-build
make prod-up
```

### Accessing Services
- Application: http://localhost:8000
- Mock Server: http://localhost:8001
- Redis: localhost:6379

### Service Communication
- Internal DNS: Use service names (app, redis, mock)
- External access: Use localhost and mapped ports

## Troubleshooting

### Common Issues
1. **Connection Refused**
   - Check if service is running: `docker-compose ps`
   - Verify network: `docker network inspect app-network`
   - Check logs: `docker-compose logs [service]`

2. **Permission Issues**
   - Verify volume permissions
   - Check user/group mappings
   - Review service logs

3. **Resource Issues**
   - Monitor Redis memory usage
   - Check container resources
   - Review application logs
