# Core Architecture

## Fundamental Principles

1. **State-Based Design**
- All operations go through state_manager
- Credentials exist ONLY in state
- No direct passing of sensitive data
- State validation through updates
- Progress tracking through state
- Validation tracking through state

2. **Component Responsibilities**
- Components handle their own operations:
  * API calls through make_api_request
  * Message sending through state_manager.messaging
  * Error handling through ErrorHandler
  * State updates with validation
- Clear boundaries between components:
  * Display components -> UI and messaging
  * Input components -> Validation and state updates
  * API components -> External calls and state updates
  * Confirm components -> User confirmation flows
- Standard patterns:
  * All operations wrapped in try/except
  * All errors handled through ErrorHandler
  * All results returned as ValidationResult

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
try:
    response = make_api_request(url, headers, payload)
    if response.status_code != 200:
        return {"error": str(response.text)}  # Don't handle directly!
except Exception as e:
    return {"error": str(e)}  # Don't handle directly!

# CORRECT - Use ErrorHandler with proper context
try:
    response = make_api_request(url, headers, payload)
    response_data, error = handle_api_response(response, state_manager)
    if error:
        return ValidationResult.failure(message=error)
    return ValidationResult.success({"action": response_data})
except Exception as e:
    error_response = ErrorHandler.handle_component_error(
        component=self.type,
        field="api_call",
        value=str(payload),
        message=str(e)
    )
    return ValidationResult.failure(message=error_response["error"]["message"])
```

### 5. Messaging Service Integration
```python
# WRONG - Access messaging service directly
messaging_service = WhatsAppMessagingService()
messaging_service.send_text(recipient, text)  # Don't access directly!

# CORRECT - Access through state manager
try:
    self.state_manager.messaging.send_text(
        recipient=recipient,
        text=message_text
    )
except Exception as e:
    error_response = ErrorHandler.handle_component_error(
        component=self.type,
        field="messaging",
        value=str(message_text),
        message=str(e)
    )
    return ValidationResult.failure(message=error_response["error"]["message"])
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

## Core Implementation
- [Service & API](docs/service-architecture.md) - Service and API integration patterns
- [State Management](docs/state-management.md) - State validation and flow control
- [Flow Framework](docs/flow-framework.md) - Progressive interaction framework

## Infrastructure
- [Security](docs/infrastructure/security.md) - Security measures and best practices
- [Docker](docs/infrastructure/docker.md) - Container configuration and services
- [Deployment](docs/infrastructure/deployment.md) - Deployment process and infrastructure
- [Redis](docs/infrastructure/redis-memory-management.md) - Redis configuration and management
