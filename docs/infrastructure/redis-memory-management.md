# Redis Architecture & Memory Management

## Overview

VimbisoPay uses Redis as a centralized state store with the following key features:
- Atomic operations for state management
- AOF persistence for durability
- Memory limits with LRU eviction
- Validation tracking
- Error handling

## State Management Architecture

### 1. Core Components

#### RedisAtomic
Low-level atomic Redis operations:
- Pipeline-based transactions
- Watch/multi for atomicity
- Automatic retries
- Error handling
- JSON serialization

```python
# Example atomic operation
pipe = redis.pipeline()
pipe.watch(key)
pipe.multi()
pipe.setex(key, ttl, json.dumps(value))
pipe.execute()
```

#### AtomicStateManager
Wraps Redis operations with validation:
- Attempt tracking
- Error tracking
- Validation state
- Clear boundaries

```python
# Example validation state
validation_state = {
    "in_progress": bool,
    "attempts": int,
    "last_attempt": datetime,
    "error": Optional[str]
}
```

#### StateManager
High-level state management:
- Single source of truth
- Clear boundaries
- Flow state management
- Channel management
- Authentication

### 2. State Structure

```python
{
    "channel": {
        "type": str,
        "identifier": str
    },
    "flow_data": {
        "context": str,
        "component": str,
        "data": dict,
        "validation": {
            "in_progress": bool,
            "attempts": int,
            "last_attempt": dict
        }
    },
    "_metadata": {
        "initialized_at": datetime,
        "updated_at": datetime
    },
    "_validation": {
        "in_progress": bool,
        "attempts": dict,
        "last_attempt": dict,
        "error": Optional[str]
    }
}
```

## Redis Configuration

### 1. Development Environment

Docker Compose configuration:
```yaml
redis-state:
  image: redis:7.0-alpine
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

### 2. Production Environment (ECS)

Redis server configuration:
```bash
redis-server \
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
- Dynamic memory limit (35% of task memory)
- LRU eviction policy
- AOF persistence with optimized settings
- No RDB persistence
- Error resilience

### 3. Client Configuration

Redis client settings:
```python
redis_client = redis.from_url(
    REDIS_STATE_URL,
    decode_responses=True,
    health_check_interval=30,
    retry_on_timeout=True
)
```

## Memory Overcommit Warning

The warning we encounter:
```
WARNING Memory overcommit must be enabled! Without it, a background save or replication may fail under low memory condition.
```

Our solution layers:

1. **Application Layer**
   - Atomic operations with retries
   - Validation tracking
   - Error handling
   - Clear boundaries

2. **Container Layer**
   - Memory limits
   - LRU eviction
   - AOF optimization
   - Error resilience

3. **Infrastructure Layer**
   - Health checks
   - Monitoring
   - Alerts
   - Backups

## Best Practices

### 1. State Access
```python
# CORRECT - Use proper accessor methods
channel_id = state_manager.get_channel_id()
member_id = state_manager.get_member_id()

# WRONG - Direct state access
channel = state_manager.get("channel")  # Don't access directly!
member_id = state_manager.get("member_id")  # Don't access directly!
```

### 2. State Updates
```python
# CORRECT - Update with validation tracking
state_manager.update_state({
    "flow_data": {
        "context": context,
        "component": component,
        "data": data,
        "validation": {
            "in_progress": True,
            "attempts": current + 1,
            "last_attempt": datetime.utcnow()
        }
    }
})

# WRONG - Update without validation
state_manager.update_state({
    "value": new_value  # Don't update without validation!
})
```

### 3. Error Handling
```python
# CORRECT - Use ErrorHandler
try:
    result = state_manager.atomic_state.atomic_get(key)
except Exception as e:
    error_context = ErrorContext(
        error_type="system",
        message=str(e),
        details={
            "code": "STATE_GET_ERROR",
            "service": "state_manager",
            "action": "get"
        }
    )
    ErrorHandler.handle_error(e, state_manager, error_context)

# WRONG - Handle errors directly
try:
    result = redis_client.get(key)  # Don't access directly!
except Exception as e:
    logger.error(str(e))  # Don't handle directly!
```

## Monitoring & Maintenance

### 1. Key Metrics
- Memory usage
- Eviction rates
- Operation latency
- Error rates
- Connection counts

### 2. Health Checks
- Redis server status
- Connection pool health
- Memory pressure
- Persistence status
- Error patterns

### 3. Maintenance Tasks
- Monitor memory usage
- Track eviction rates
- Review error logs
- Validate configurations
- Update documentation

## Recommended Improvements

1. **Monitoring**
   - Redis memory metrics in CloudWatch
   - High memory utilization alerts
   - Eviction rate monitoring
   - Error pattern detection

2. **Performance**
   - Redis Cluster for scalability
   - Key expiration policies
   - Circuit breakers
   - Connection pooling

3. **Infrastructure**
   - ElastiCache evaluation
   - Redis Sentinel
   - Automated backups
   - Configuration validation

4. **Development**
   - Redis monitoring tools
   - Debugging utilities
   - Documentation updates
   - Best practices guides

## Conclusion

Our Redis architecture provides:
- Robust state management through atomic operations
- Strong validation and error handling
- Memory optimization with LRU eviction
- Data durability through AOF persistence
- Clear patterns and best practices

While the memory overcommit warning may appear in some environments, our configuration significantly reduces the risk of failures through:
- Memory limits and eviction policies
- Optimized persistence settings
- Error resilience mechanisms
- Comprehensive monitoring
