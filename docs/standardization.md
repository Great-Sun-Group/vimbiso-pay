# State Management Rules

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
- Member ID ONLY at top level
- Channel info ONLY at top level
- JWT token ONLY in state
- No credential duplication

## Implementation Patterns

### 1. API Calls
```python
# CORRECT - Extract credentials only when needed
def make_api_call(state_manager: Any) -> None:
    """Make API call through state validation"""
    # Let StateManager validate through update
    state_manager.update_state({
        "flow_data": {
            "step": "api_call"
        }
    })

    # Extract token ONLY when needed
    jwt_token = state_manager.get("jwt_token")
    if jwt_token:
        headers["Authorization"] = f"Bearer {jwt_token}"

    # Make request with validated token
    response = requests.post(url, headers=headers)

# WRONG - Store credentials in variables
def make_api_call(state_manager: Any) -> None:
    token = state_manager.get("jwt_token")  # Don't store!
    make_request(token)  # Don't pass credentials!
```

### 2. Channel Info
```python
# CORRECT - Extract from state only when needed
def handle_auth(state_manager: Any) -> None:
    """Handle auth through state validation"""
    # Let StateManager validate channel
    channel = state_manager.get("channel")
    if not channel or not channel.get("identifier"):
        raise ConfigurationException("Missing channel identifier")

    # Use phone ONLY for this request
    payload = {"phone": channel["identifier"]}
    response = make_request(payload)

# WRONG - Store channel info in variables
def handle_auth(state_manager: Any) -> None:
    phone = state_manager.get("channel")["identifier"]  # Don't store!
    make_auth_call(phone)  # Don't pass phone!
```

### 3. State Updates
```python
# CORRECT - Update through state_manager
def handle_response(state_manager: Any, response: Dict[str, Any]) -> None:
    """Handle response through state validation"""
    # Let StateManager validate response data
    state_manager.update_state({
        "flow_data": {
            "response": response
        }
    })

# WRONG - Transform state manually
def handle_response(state_manager: Any, response: Dict[str, Any]) -> None:
    data = transform_response(response)  # Don't transform!
    state_manager.update_state({"data": data})
```

### 4. Error Handling
```python
# CORRECT - Use ErrorHandler with context
try:
    response = make_credex_request(
        'credex', 'create',
        payload=payload,
        state_manager=state_manager
    )
except Exception as e:
    error_context = ErrorContext(
        error_type="api",
        message=str(e),
        details={
            "operation": "create_credex",
            "payload": payload
        }
    )
    return ErrorHandler.handle_error(
        e,
        state_manager,
        error_context
    )

# WRONG - Handle errors manually
try:
    response = make_request()
except Exception as e:
    return {"error": str(e)}  # Don't handle directly!
```

## Common Anti-Patterns

### 1. Storing State
```python
# WRONG - Class with stored state
class MessageHandler:
    def __init__(self, state_manager):
        self.state = state_manager  # NO instance state!
        self.channel = state_manager.get("channel")  # NO stored state!

# CORRECT - Pure functions
def handle_message(state_manager: Any, message: str) -> Response:
    return process(state_manager.get("data"))
```

### 2. State Transformation
```python
# WRONG - Manual state transformation
def process_response(state_manager: Any, response: Dict[str, Any]) -> None:
    data = transform_response(response)  # Don't transform!
    state_manager.update_state({"data": data})

# CORRECT - Let StateManager validate
def process_response(state_manager: Any, response: Dict[str, Any]) -> None:
    state_manager.update_state({
        "flow_data": {
            "response": response  # Raw response
        }
    })
```

### 3. State Passing
```python
# WRONG - Passing state between functions
def handle_action(state_manager: Any, stored_data: Dict) -> None:
    return process_action(state_manager, stored_data)  # Don't pass state!

# CORRECT - Only state_manager
def handle_action(state_manager: Any) -> None:
    return process_action(state_manager)  # Only state_manager
```

### 4. Manual Validation
```python
# WRONG - Manual state validation
def verify_state(state_manager: Any) -> None:
    state = state_manager.get("flow_data")
    if not state or "data" not in state:  # NO manual verification!
        raise StateException("Invalid state")

# CORRECT - Let StateManager validate
def process_state(state_manager: Any) -> None:
    state_manager.update_state({
        "flow_data": {
            "step": "verify"
        }
    })
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
     * state.get() for core state (member_id, channel, jwt_token)
     * get_flow_step_data() for flow state
     * get_flow_type() for flow identification
     * get_current_step() for flow routing
     * get_channel_id() for channel operations
   - [ ] NO attribute access?
   - [ ] NO instance variables?

3. State Changes
   - [ ] NO state duplication?
   - [ ] NO state transformation?
   - [ ] NO state passing?

4. Handler Implementation
   - [ ] Using pure functions?
   - [ ] NO class state?
   - [ ] NO handler instantiation?
   - [ ] Clear module boundaries?

5. Validation
   - [ ] Validating through updates?
   - [ ] NO manual validation?
   - [ ] NO cleanup code?

6. Error Handling
   - [ ] Using ErrorHandler?
   - [ ] Clear error context?
   - [ ] Relevant details?
   - [ ] NO manual handling?

## Validation

The system enforces these patterns through:
1. Code review - Catch violations early
2. Static analysis - Verify patterns automatically
3. Runtime validation - Catch violations at runtime
4. Logging/monitoring - Track state access patterns
5. Error tracking - Identify state-related issues

These patterns ensure:
- Consistent state access
- Proper validation
- Clear error handling
- Maintainable code

For more details on:
- Service architecture: [Service Architecture](service-architecture.md)
- API integration: [API Integration](api-integration.md)
- Flow framework: [Flow Framework](flow-framework.md)
