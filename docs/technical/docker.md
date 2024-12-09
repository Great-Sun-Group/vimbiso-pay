# Docker Configuration

## Overview

VimbisoPay uses Docker for:
- Application (Django)
- Redis (State management)
- Mock WhatsApp server (Testing)

## Services

### Application
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
```

### Redis
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
```

### Mock Server
```yaml
mock:
  build:
    context: ..
    target: development
  volumes:
    - ../mock:/app/mock
  ports:
    - "8001:8001"
```

## Development

### Quick Start
```bash
# Start services
make dev-build
make dev-up

# Access services
Application: http://localhost:8000
Mock WhatsApp: http://localhost:8001
Redis: localhost:6379
```

### Service Communication
Within Docker network:
- Application: http://app:8000
- Redis: redis://redis:6379
- Mock Server: http://mock:8001

## Production

### Security Features
```dockerfile
# Use non-root user
RUN adduser \
    --disabled-password \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "10001" \
    appuser

# Minimal dependencies
RUN apt-mark manual redis-tools curl gosu && \
    apt-get purge -y build-essential && \
    apt-get autoremove -y
```

### Health Checks
```yaml
healthcheck:
  test: curl -f http://localhost:${PORT}/health/
  interval: 30s
  timeout: 10s
  retries: 3
```

## Troubleshooting

Common issues:
1. **Connection Refused**
   ```bash
   # Check services
   docker-compose ps

   # Check logs
   docker-compose logs [service]
   ```

2. **Redis Issues**
   - Check memory usage
   - Verify configuration
   - See [Redis Management](../redis-memory-management.md)

For more details on:
- Testing: [Testing Guide](testing.md)
- Deployment: [Deployment](../deployment.md)
- Security: [Security](security.md)
