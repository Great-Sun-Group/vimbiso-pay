# State Management Debug Reference

## Architecture Overview

```
┌─────────────────────┐
│   WhatsApp Handler  │
└─────────┬───────────┘
          │
┌─────────▼───────────┐
│    Flow Handler     │
└─────────┬───────────┘
          │
┌─────────▼───────────┐     ┌─────────────────┐
│    Flow Instance    │◄────┤  State Service  │
└─────────┬───────────┘     └─────┬───────────┘
          │                       │
┌─────────▼───────────┐          │
│      Steps          │          │
└─────────┬───────────┘          │
          │                      │
          └──────────────────────┘
```

### Key Components

1. **State Service** (`app/services/state/service.py`)
   - Redis-based state storage
   - Session management with TTL
   - State transition validation
   - Concurrent access handling
   - JWT token preservation

2. **State Stages**
```python
INIT -> AUTH -> MENU -> [CREDEX, ACCOUNT, REGISTRATION]
```

## Common Issues & Solutions

### 1. State Corruption

**Symptoms:**
- Unexpected flow transitions
- Missing state data
- Invalid state values
- Flow getting stuck

**Debug Steps:**
1. Check Redis state:
```python
# Get current state
state = redis_client.get(f"user:{phone_number}:state")
print(f"Current state: {state}")

# Check state TTL
ttl = redis_client.ttl(f"user:{phone_number}:state")
print(f"State TTL: {ttl}")
```

2. Verify state structure:
```python
required_fields = {"stage", "option"}
if not all(field in state for field in required_fields):
    print(f"Missing required fields: {required_fields - set(state.keys())}")
```

3. Check state transitions:
```python
from_stage = current_state.get("stage")
to_stage = new_stage
if not StateTransition.is_valid_transition(from_stage, to_stage):
    print(f"Invalid transition: {from_stage} -> {to_stage}")
```

### 2. Concurrency Issues

**Symptoms:**
- Lost updates
- Inconsistent state
- Lock timeouts
- Stuck flows

**Debug Steps:**
1. Check locks:
```python
# Check if lock exists
lock = redis_client.get(f"{user_id}_lock")
print(f"Lock status: {lock}")

# Check lock TTL
lock_ttl = redis_client.ttl(f"{user_id}_lock")
print(f"Lock TTL: {lock_ttl}")
```

2. Monitor lock acquisition:
```python
# Add debug logging
logger.debug(f"Attempting to acquire lock for {user_id}")
if not self._acquire_lock(user_id):
    logger.error(f"Failed to acquire lock for {user_id}")
```

### 3. Memory Management

**Symptoms:**
- Redis OOM errors
- Slow state operations
- Missing states
- Expired states

**Debug Steps:**
1. Monitor Redis memory:
```bash
redis-cli info memory
```

2. Check key space:
```bash
redis-cli --scan --pattern "user_state:*"
```

3. Monitor TTLs:
```bash
# Get keys close to expiration
redis-cli --scan --pattern "user_state:*" | while read key; do
  ttl=$(redis-cli ttl "$key")
  if [ $ttl -lt 300 ]; then
    echo "Key $key expires in ${ttl}s"
  fi
done
```

## Improvement Recommendations

### 1. State Management

1. **Enhanced Validation**
```python
def _validate_state_data(self, state_data: Dict[str, Any]) -> None:
    """Enhanced state validation"""
    required_fields = {
        "stage": str,
        "option": str,
        "last_updated": float,
        "update_from": str
    }

    for field, field_type in required_fields.items():
        if field not in state_data:
            raise InvalidStateError(f"Missing required field: {field}")
        if not isinstance(state_data[field], field_type):
            raise InvalidStateError(f"Invalid type for {field}")
```

2. **State Recovery**
```python
def recover_state(self, user_id: str) -> None:
    """Attempt to recover corrupted state"""
    try:
        # Get current state
        current_state = self.get_state(user_id)

        # Validate structure
        self._validate_state_data(current_state)

        # Check transitions
        if not StateTransition.is_valid_transition(
            current_state.get("stage"),
            StateStage.MENU.value
        ):
            # Reset to safe state
            self.reset_state(user_id)

    except Exception as e:
        logger.error(f"State recovery failed: {str(e)}")
        self.reset_state(user_id)
```

### 2. Monitoring

1. **State Metrics**
```python
def collect_metrics(self) -> Dict[str, Any]:
    """Collect state service metrics"""
    metrics = {
        "total_states": 0,
        "expired_states": 0,
        "locked_states": 0,
        "stage_distribution": {},
        "average_ttl": 0
    }

    # Implement metric collection
    return metrics
```

2. **Health Checks**
```python
def health_check(self) -> Dict[str, bool]:
    """Check state service health"""
    checks = {
        "redis_connection": False,
        "lock_mechanism": False,
        "state_operations": False
    }

    try:
        # Test Redis connection
        self.redis.ping()
        checks["redis_connection"] = True

        # Test lock mechanism
        test_id = "health_check"
        if self._acquire_lock(test_id):
            self._release_lock(test_id)
            checks["lock_mechanism"] = True

        # Test state operations
        test_state = self.get_state(test_id)
        checks["state_operations"] = True

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")

    return checks
```

## Next Steps

1. **Immediate Actions**
   - Implement enhanced state validation
   - Add state recovery mechanism
   - Set up monitoring and alerts
   - Add health checks

2. **Long-term Improvements**
   - Consider implementing state versioning
   - Add state backup/restore functionality
   - Implement state migration tools
   - Add performance optimization

3. **Monitoring Setup**
   - Configure Redis monitoring
   - Set up state metrics collection
   - Implement alerting
   - Add debugging tools

## Testing Strategy

1. **Unit Tests**
```python
def test_state_transitions():
    """Test all possible state transitions"""
    service = StateService(redis_client)

    # Test valid transitions
    for from_stage in StateStage:
        for to_stage in StateStage:
            is_valid = StateTransition.is_valid_transition(
                from_stage.value,
                to_stage.value
            )
            print(f"{from_stage} -> {to_stage}: {'Valid' if is_valid else 'Invalid'}")
```

2. **Integration Tests**
```python
def test_concurrent_access():
    """Test concurrent state access"""
    service = StateService(redis_client)
    user_id = "test_user"

    # Simulate concurrent updates
    def update_state():
        service.update_state(
            user_id=user_id,
            new_state={"stage": "test", "option": "test"},
            stage="test",
            update_from="test"
        )

    # Run concurrent updates
    threads = [Thread(target=update_state) for _ in range(10)]
    [t.start() for t in threads]
    [t.join() for t in threads]
```

3. **Load Tests**
```python
def test_state_performance():
    """Test state service performance"""
    service = StateService(redis_client)

    # Measure operation times
    start = time.time()
    for i in range(1000):
        service.get_state(f"test_user_{i}")
    end = time.time()

    print(f"Average get_state time: {(end - start) / 1000}s")
