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
  volumes:
    - ./data:/app/data
    - .:/app
  ports:
    - "8000:8000"
  environment:
    - DJANGO_ENV=development
    - DEBUG=True
    - ALLOWED_HOSTS=*
    - DJANGO_SECRET=local-secret-key
    - REDIS_STATE_URL=redis://redis-state:6379/0
  depends_on:
    redis-state:
      condition: service_healthy
  healthcheck:
    test: ["CMD-SHELL", "curl -f http://localhost:8000/health/ || exit 1"]
    interval: 30s
    timeout: 10s
    retries: 3
```

### Redis Service
```yaml
redis-state:
  image: redis:7.0-alpine
  volumes:
    - ./data/redis/state:/data
  ports:
    - "6379:6379"
  command: >
    redis-server
    --maxmemory 512mb
    --maxmemory-policy allkeys-lru
    --appendonly yes
    --appendfsync everysec
    --save ""
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 5s
    timeout: 3s
    retries: 3
```

Key features:
- Memory limit: 512MB
- LRU eviction policy
- AOF persistence enabled
- Optimized fsync (everysec)
- No RDB persistence
- Regular health checks

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
  command: ["python3", "mock/server.py"]
  depends_on:
    - app
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
- Redis: redis://redis-state:6379
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

## Redis Configuration

### Memory Management
- Memory limit: 512MB
- LRU eviction policy
- AOF persistence
- No RDB persistence
- See [Redis Management](redis-memory-management.md)

### Persistence
- AOF enabled
- Fsync: everysec
- Auto-rewrite: 100%
- Min size: 64mb
- No RDB saves

### Health Checks
- Regular ping tests
- 5s intervals
- 3s timeout
- 3 retries

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
   - Review AOF status
   - Monitor eviction rates
   - See [Redis Management](redis-memory-management.md)

3. **Application Issues**
   - Check app logs
   - Verify Redis connection
   - Validate environment variables
   - Check health endpoints
