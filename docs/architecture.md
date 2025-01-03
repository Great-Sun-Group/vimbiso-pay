# Core Architecture

## Fundamental Principles

1. **State-Based Design**
- All operations go through state_manager
- Credentials exist ONLY in state
- No direct passing of sensitive data
- State validation through updates
- Progress tracking through state
- Validation tracking through state

2. **Pure Functions**
- Services use stateless functions
- No stored instance variables
- No service-level state
- Clear input/output contracts
- Standard validation patterns
- Standard error handling

3. **Single Source of Truth**
- Member ID ONLY at top level
- Channel info ONLY at top level
- JWT token ONLY in state
- No credential duplication
- No state duplication
- No manual transformation

4. **Flow Framework**
- Common flow configurations
- Clear flow types
- Standard components
- Flow type metadata
- Progress tracking
- Validation tracking

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

### 2. Credential Handling
```python
# WRONG - Store or pass credentials
token = state_manager.get("jwt_token")  # Don't store!
make_request(token)  # Don't pass credentials!

# CORRECT - Access through flow data
auth_data = state_manager.get_flow_data().get("auth", {})
if auth_data.get("token"):
    headers["Authorization"] = f"Bearer {auth_data['token']}"
```

### 3. State Updates
```python
# WRONG - Update without validation
state_manager.update_state({
    "value": new_value  # Don't update without validation!
})

# CORRECT - Update with validation tracking
state_manager.update_state({
    "flow_data": {
        "active_component": {
            "type": "input",
            "validation": {
                "in_progress": True,
                "attempts": current + 1,
                "last_attempt": datetime.utcnow()
            }
        }
    }
})
```

### 4. Error Handling
```python
# WRONG - Handle errors manually
if error:
    return {"error": str(error)}  # Don't handle directly!

# CORRECT - Use ErrorHandler with context
error_context = ErrorContext(
    error_type="api",
    message=str(error),
    details={"operation": operation}
)
ErrorHandler.handle_error(error, state_manager, error_context)
```

## Pre-Change Checklist

STOP and verify before ANY code change:

1. State Location
   - [ ] member_id ONLY at top level?
   - [ ] channel info ONLY at top level?
   - [ ] jwt_token ONLY in state?
   - [ ] NO new state duplication?

2. State Access
   - [ ] Using appropriate access patterns?
     * state.get() for core state
     * get_flow_state() for flow state
     * get_flow_type() for flow identification
     * get_current_step() for flow routing
     * get_channel_id() for channel operations
   - [ ] NO attribute access?
   - [ ] NO instance variables?

3. State Changes
   - [ ] NO state duplication?
   - [ ] NO state transformation?
   - [ ] NO state passing?
   - [ ] Proper progress tracking?
   - [ ] Proper validation tracking?

4. Handler Implementation
   - [ ] Using pure functions?
   - [ ] NO class state?
   - [ ] NO handler instantiation?
   - [ ] Clear module boundaries?
   - [ ] Proper progress tracking?

5. Validation
   - [ ] Validating through updates?
   - [ ] NO manual validation?
   - [ ] NO cleanup code?
   - [ ] Proper attempt tracking?
   - [ ] Proper error context?

6. Error Handling
   - [ ] Using ErrorHandler?
   - [ ] Clear error context?
   - [ ] Relevant details?
   - [ ] NO manual handling?
   - [ ] Proper validation state?

## Implementation Guide

For detailed implementation patterns, see:
- [Service Architecture](service-architecture.md) - Core service patterns and best practices
- [API Integration](api-integration.md) - API interaction patterns and state management
- [State Management](state-management.md) - State validation and flow control
- [Flow Framework](flow-framework.md) - Progressive interaction framework
- [Components](components.md) - UI components
- [Error Handling](error-handling.md) - Error handling patterns
- [Testing](testing.md) - Testing infrastructure and tools

## Deployment & Infrastructure

For deployment and infrastructure details, see:
- [Docker](docker.md) - Docker configuration and services
- [Deployment](deployment.md) - Deployment process and infrastructure
- [Redis Management](redis-memory-management.md) - Redis configuration and management
- [Security](security.md) - Security measures and best practices
