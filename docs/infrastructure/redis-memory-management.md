# Redis Memory Management Solutions

This document outlines our multi-layered approach to handling Redis memory management and addressing the "Memory overcommit must be enabled" warning.

## The Warning

The warning we encounter:
```
WARNING Memory overcommit must be enabled! Without it, a background save or replication may fail under low memory condition. Being disabled, it can also cause failures without low memory condition, see https://github.com/jemalloc/jemalloc/issues/1328.
```

This warning indicates potential issues with Redis memory allocation and background save operations. Because of the challenges in solving this issue at the container level in both development and deployed environments, we have built in resilience at the app layer to decrease the potential for error.

## Solution Layers

### 1. Application Level (Django Settings)

We use two Redis instances with specialized configurations:

1. **Cache Redis** (`REDIS_CACHE_URL`):
```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_CACHE_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 30,
            "SOCKET_TIMEOUT": 30,
            "RETRY_ON_TIMEOUT": True,
            "MAX_CONNECTIONS": 20,
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 20,
                "retry_on_timeout": True,
                "health_check_interval": 30,
            },
            "IGNORE_EXCEPTIONS": True,
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "SERIALIZER": "django_redis.serializers.json.JSONSerializer",
        },
        "KEY_PREFIX": "vimbiso",
        "TIMEOUT": 300,  # 5 minutes default timeout
    }
}
```

2. **State Redis** (`REDIS_STATE_URL`):
Used for managing conversation state and session data with persistence enabled.

These settings:
- Disable Redis persistence to prevent background save operations
- Implement memory limits and eviction policies
- Use LRU (Least Recently Used) algorithm for key eviction

### 2. Container Level (Production ECS)

In our ECS task definition (`task_definition.tf`), we've implemented container-level optimizations:

```bash
exec gosu redis redis-server \
    --appendonly yes \
    --appendfsync everysec \
    --auto-aof-rewrite-percentage 100 \
    --auto-aof-rewrite-min-size 64mb \
    --maxmemory-policy allkeys-lru \
    --maxmemory ${floor(var.task_memory * 0.35 * 0.95)}mb \
    --save "" \
    --stop-writes-on-bgsave-error no
```

Key features:
- Dynamic memory limit based on container resources (35% of task memory)
- LRU eviction policy
- Disabled RDB persistence (`--save ""`)
- Configured AOF persistence with optimized settings
- Disabled write blocking on background save errors

### 3. Development Environment (Docker Compose)

In the development environment (`compose.yaml`), we use specialized Redis configurations:

```yaml
redis-cache:
  command: >
    redis-server
    --maxmemory 256mb
    --maxmemory-policy allkeys-lru
    --appendonly no
    --save ""

redis-state:
  command: >
    redis-server
    --maxmemory 256mb
    --maxmemory-policy allkeys-lru
    --appendonly yes
    --appendfsync everysec
    --save ""
```

Note: While the warning about memory overcommit will still appear in development, our configuration ensures:
- Memory usage is limited and managed through Redis configuration
- Automatic eviction of keys when memory limits are reached
- No background saves that could fail due to memory issues

## Impact Analysis

1. **Warning vs. Critical Issues**
   - The warning will still appear in environments without memory overcommit enabled
   - However, our configurations significantly reduce the risk of actual failures by:
     - Limiting memory usage
     - Implementing automatic eviction
     - Disabling or optimizing persistence operations

2. **Resilience Improvements**
   - Automatic memory management through LRU eviction
   - Graceful handling of memory pressure
   - Reduced risk of background save failures
   - Optimized persistence strategy

## Recommended Improvements

1. **Monitoring Enhancement**
   - Implement Redis memory usage metrics in CloudWatch
   - Add alerts for high memory utilization
   - Monitor eviction rates and cache hit ratios

2. **Performance Optimization**
   - Consider implementing Redis Cluster for better scalability
   - Add cache key expiration policies based on usage patterns
   - Implement circuit breakers for Redis operations

3. **Infrastructure Improvements**
   - Consider using ElastiCache instead of self-managed Redis
   - Implement Redis Sentinel for high availability
   - Add automatic backup solutions that don't rely on background saves

4. **Development Workflow**
   - Add Redis configuration validation in CI/CD pipeline
   - Create development tools for Redis monitoring and debugging
   - Document Redis usage patterns and best practices

## Conclusion

Our multi-layered approach provides robust Redis memory management while minimizing the risk of failures. While the warning may still appear in some environments, the actual risk of memory-related issues has been significantly reduced through careful configuration at multiple levels of the stack.
