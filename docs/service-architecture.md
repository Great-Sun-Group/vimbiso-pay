# Service & API Architecture

## Core Principles

1. **State-Based Design**
- All operations go through state_manager
- Credentials exist ONLY in state
- No direct passing of sensitive data
- State validation through updates

2. **Pure Functions**
- Services use stateless functions
- No stored instance variables
- No service-level state
- Clear input/output contracts

3. **Single Source of Truth**
- Member ID accessed through get_member_id()
- Channel info accessed through get_channel_id()
- JWT token accessed through flow_data auth
- No direct state access

## Common Anti-Patterns

### 1. Credential Access
```python
# WRONG - Store or pass credentials
token = state_manager.get("jwt_token")  # Don't store!
make_request(token)  # Don't pass credentials!

# CORRECT - Access through flow data
auth_data = state_manager.get_flow_data().get("auth", {})
if auth_data.get("token"):
    headers["Authorization"] = f"Bearer {auth_data['token']}"
```

### 2. State Management
```python
# WRONG - Direct state access
channel = state_manager.get("channel")  # Don't access directly!
phone = channel["identifier"]  # Don't access structure directly!

# CORRECT - Use proper accessor methods
channel_id = state_manager.get_channel_id()
member_id = state_manager.get_member_id()
```

### 3. Error Handling
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

## Implementation Guide

### Service Layer
1. Services must be stateless
2. Use proper accessor methods
3. Track all operations
4. Handle errors consistently

### API Integration
1. All API calls through state_manager
2. Extract credentials only when needed
3. Track validation attempts
4. Handle errors through ErrorHandler

### State Updates
1. Update through state_manager
2. Include validation tracking
3. Track operation attempts
4. Include error context

### Error Handling
1. Use ErrorHandler for all errors
2. Include operation details
3. Track validation failures
4. Update state with errors

## Code Reading Guide

Before modifying service-related functionality, read these files in order:

1. services/messaging/service.py - Core messaging service
2. services/whatsapp/service.py - Channel-specific handling
3. services/whatsapp/bot_service.py - Bot handling
4. services/whatsapp/types.py - Service types

Common mistakes to avoid:
1. DON'T modify services without understanding types
2. DON'T bypass service interfaces
3. DON'T mix service responsibilities
4. DON'T duplicate service functionality

For implementation details, see:
- [State Management](state-management.md) - State validation and flow control
- [Flow Framework](flow-framework.md) - Progressive interaction framework
