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

## Component Patterns

### 1. Handler Components
```python
# CORRECT - Handler uses messaging service
class AuthHandler:
    """Handler for authentication operations"""

    def __init__(self, messaging_service: MessagingServiceInterface):
        self.messaging = messaging_service

    def handle_greeting(self, state_manager: Any) -> Message:
        """Handle initial greeting with login attempt"""
        try:
            # Validate and attempt login
            success, response = self.attempt_login(state_manager)

            if success:
                # Update state through manager
                state_manager.update_state({
                    "authenticated": True,
                    "member_data": response.get("member")
                })
                return self.messaging.send_dashboard(...)
            else:
                return self.messaging.send_text(...)

        except Exception as e:
            return self.messaging.send_error(...)

# WRONG - Direct message handling
def handle_greeting(state_manager: Any) -> Dict:
    try:
        response = make_api_call()  # Don't call API directly!
        state_manager.state["auth"] = True  # Don't modify state directly!
        return {"message": "Welcome!"}  # Don't format messages here!
    except:
        return {"error": "Failed"}  # Don't handle errors directly!
```

### 2. Input Validation
```python
# CORRECT - Component handles validation
class AmountDenomInput(InputComponent):
    def validate(self, value: Any) -> ValidationResult:
        """Validate through component"""
        try:
            amount = float(value)
            if amount <= 0:
                return ValidationResult(
                    valid=False,
                    error={
                        "type": "input",
                        "message": "Amount must be positive"
                    }
                )
            return ValidationResult(valid=True)
        except ValueError:
            return ValidationResult(
                valid=False,
                error={
                    "type": "input",
                    "message": "Invalid amount format"
                }
            )

# WRONG - Manual validation in flow
def handle_amount(state_manager: Any, value: str) -> None:
    try:
        amount = float(value)  # Don't validate here!
        if amount > 0:  # Don't check here!
            state_manager.update_state({"amount": amount})
    except ValueError:
        pass  # Don't handle errors here!
```

### 2. Data Conversion
```python
# CORRECT - Component converts to verified data
class HandleInput(InputComponent):
    def to_verified_data(self) -> Dict:
        """Convert to verified data"""
        return {
            "handle": self.value  # Clean handle value
        }

# WRONG - Flow transforms data
def process_handle(state_manager: Any, handle: str) -> None:
    cleaned = handle.strip()  # Don't transform here!
    state_manager.update_state({
        "handle": cleaned  # Don't store unverified!
    })
```

### 3. Component State
```python
# CORRECT - Component state in flow_data
state_manager.update_state({
    "flow_data": {
        "active_component": {
            "type": "amount_input",
            "value": "100.00",
            "validation": {
                "in_progress": True
            }
        }
    }
})

# WRONG - Component state outside flow_data
state_manager.update_state({
    "input_value": "100.00",  # Don't store outside!
    "validation": {...}       # Don't separate validation!
})
```

### 4. Error Boundaries
```python
# CORRECT - Clear error boundaries
# Component error (validation)
result = component.validate("invalid")
if not result.valid:
    state_manager.update_state({
        "flow_data": {
            "active_component": {
                "error": result.error  # Component-level error
            }
        }
    })

# Flow error (business logic)
try:
    if amount > balance:
        raise FlowException("Insufficient balance")
except FlowException as e:
    error_context = ErrorContext(
        error_type="flow",  # Flow-level error
        message=str(e),
        details={...}
    )
    ErrorHandler.handle_error(e, state_manager, error_context)

# System error (top level)
try:
    response = make_api_call()
except APIException as e:
    error_context = ErrorContext(
        error_type="system",  # System-level error
        message="Service unavailable",
        details={...}
    )
    ErrorHandler.handle_error(e, state_manager, error_context)

# WRONG - Mixed error handling
try:
    result = validate_input(value)  # Don't mix validation!
    if not result.valid:
        raise APIException(result.error)  # Don't mix error types!
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
