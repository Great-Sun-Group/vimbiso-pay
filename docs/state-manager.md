# State Management

## Overview

The state management system provides the data foundation for the central flow management system (headquarters.py):

```
headquarters.py  <-- Flow Management
      ↓
state_manager   <-- State Management
      ↓
RedisAtomic     <-- Persistence Layer
```

### State Management Layers
1. **StateManager**: High-level interface for state operations
   - Used by headquarters.py for flow state
   - Used by components for operation state
   - Maintains validation and boundaries

2. **AtomicStateManager**: Validation and transaction handling
   - Ensures atomic operations
   - Handles validation
   - Manages transactions

3. **RedisAtomic**: Low-level atomic Redis operations
   - Persistence layer
   - Atomic operations
   - Transaction safety

## Core Principles

1. **Flow State Management**
- headquarters.py manages flow through state
- Components update state with results
- Flow decisions based on state
- Clear state boundaries
- Standard validation

2. **Single Source of Truth**
- Channel info accessed through get_channel_id()
- JWT token accessed through flow_data auth
- Member data accessed through dashboard state
- Messaging service accessed through state_manager.messaging
- NO direct state access
- NO state passing
- NO transformation

3. **State Persistence**
- Redis as persistent storage
- Atomic operations for consistency
- AOF persistence for durability
- Transaction handling for safety
- NO direct Redis access
- NO manual persistence

4. **Component State Integration**
- Components handle their own state:
  * API calls through make_api_request
  * Message sending through state_manager.messaging
  * Error handling through ErrorHandler
  * State updates with validation
- Clear boundaries between components:
  * Display components -> Read-only state access
  * Input components -> Validated state updates
  * API components -> State updates through handlers
  * Confirm components -> Context-aware state updates

## State Structure

### 1. Flow State
```python
{
    "flow_data": {
        "path": str,     # Current flow context
        "component": str,   # Active component
        "data": dict,       # Flow-specific data
        "validation": {     # Validation state
            "in_progress": bool,
            "attempts": int,
            "last_attempt": dict
        }
    }
}
```

### 2. Core State
```python
{
    "channel": {
        "type": str,        # Channel type (e.g., "whatsapp")
        "identifier": str   # Channel ID
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

### 3. Redis Storage
- Key format: `channel:{channel_id}`
- TTL: 300 seconds (5 minutes)
- JSON serialization
- AOF persistence
- Atomic operations

## Common Anti-Patterns to Avoid

### 1. State Access
```python
# WRONG - Direct state access
channel = state_manager.get("channel")  # Don't access directly!
member_id = state_manager.get("member_id")  # Don't access directly!

# CORRECT - Use proper accessor methods
channel_id = state_manager.get_channel_id()
member_id = state_manager.get_member_id()
```

### 2. State Updates
```python
# WRONG - Update without validation
state_manager.update_state({
    "value": new_value  # Don't update without validation!
})

# CORRECT - Update with validation tracking
state_manager.update_state({
    "flow_data": {
        "path": path,
        "component": component,
        "data": data,
        "validation": {
            "in_progress": True,
            "attempts": current + 1,
            "last_attempt": datetime.utcnow()
        }
    }
})
```

### 3. Error Handling
```python
# WRONG - Handle errors directly
try:
    result = redis_client.get(key)  # Don't access directly!
except Exception as e:
    logger.error(str(e))  # Don't handle directly!

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
```

## Best Practices

1. **Flow State Management**
- Let headquarters.py manage flow state
- Components update results through state
- Use proper state accessors
- Maintain validation tracking

2. **Component State Access**
- Use appropriate patterns per component type:
  * Display -> Read-only access
  * Input -> Validated updates
  * API -> Handler updates
  * Confirm -> Context updates
- Follow component boundaries
- Maintain validation state

3. **Error Handling**
- Use ErrorHandler consistently
- Include proper context
- Track validation state
- Follow error patterns

4. **State Recovery**
- Initialize properly
- Handle failures gracefully
- Preserve core state
- Track cleanup

## Code Reading Guide

Before modifying state management, read these files in order:

1. core/flow/headquarters.py - Flow Management
   - How flow state is managed
   - How components interact with state
   - How state drives flow decisions

2. core/state/manager.py - State Management
   - How state is structured
   - How validation works
   - How components access state

3. core/state/atomic.py - Atomic Operations
   - How persistence works
   - How transactions are handled
   - How atomicity is maintained

4. core/state/validator.py - State Validation
   - How updates are validated
   - How boundaries are maintained
   - How errors are handled

Common mistakes to avoid:
1. DON'T bypass headquarters.py for flow control
2. DON'T access state directly
3. DON'T update without validation
4. DON'T break component boundaries
5. DON'T mix state responsibilities
