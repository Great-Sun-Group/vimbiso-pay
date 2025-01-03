# State Management Rules

## Core Principles

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

## Component Patterns

### 1. Handler Components
```python
# CORRECT - Handler uses messaging service with proper tracking
class CredexHandler:
    """Handler for credex operations"""

    def __init__(self, messaging_service: MessagingServiceInterface):
        self.messaging = messaging_service
        self.offer = OfferFlow(messaging_service)
        self.actions = {
            "accept": ActionFlow(messaging_service, "accept"),
            "decline": ActionFlow(messaging_service, "decline"),
            "cancel": ActionFlow(messaging_service, "cancel")
        }

    def handle_flow_step(self, state_manager: Any, flow_type: str, step: str, input_value: Any) -> Message:
        """Handle flow step with proper tracking"""
        try:
            # Get flow state for context
            flow_state = state_manager.get_flow_state()

            # Process through appropriate flow
            if flow_type == "credex_offer":
                result = self.offer.process_step(state_manager, step, input_value)
            elif flow_type.startswith("credex_"):
                action_type = flow_type.split("_", 1)[1]
                result = self.actions[action_type].process_step(state_manager, step, input_value)

            # Add progress to message
            if "message" in result:
                progress = f"Step {flow_state['step_index'] + 1} of {flow_state['total_steps']}"
                result["message"] = f"{result['message']}\n\n{progress}"

            return result

        except Exception as e:
            return self.messaging.send_error(...)

# WRONG - Direct message handling without tracking
def handle_flow_step(state_manager: Any, step: str, value: Any) -> Dict:
    try:
        result = process_step(value)  # Don't process directly!
        return {"message": result}  # Don't return without progress!
    except:
        return {"error": "Failed"}  # Don't handle errors directly!
```

### 2. Component Validation
```python
# CORRECT - Component with proper validation tracking
class TextInput(InputComponent):
    """Pure UI validation component"""

    def validate(self, value: Any) -> ValidationResult:
        """Validate input format with tracking"""
        # Track validation attempt
        self.validation_state["attempts"] += 1
        self.validation_state["last_attempt"] = value

        # Type validation
        if not isinstance(value, str):
            return ValidationResult.failure(
                message="Input must be text",
                field="value",
                details={
                    "expected_type": "text",
                    "actual_type": str(type(value)),
                    "attempts": self.validation_state["attempts"]
                }
            )

        # Basic format validation
        if not value.strip():
            return ValidationResult.failure(
                message="Input required",
                field="value",
                details={
                    "error": "empty_string",
                    "attempts": self.validation_state["attempts"]
                }
            )

        # Update component state
        self.update_state(value, ValidationResult.success(value))
        return ValidationResult.success(value)

# WRONG - Component without validation tracking
class TextInput(InputComponent):
    def validate(self, value: Any) -> ValidationResult:
        if not value.strip():  # Don't validate without tracking!
            return ValidationResult.failure("Required")  # Don't return without context!
        return ValidationResult.success(value)  # Don't update without tracking!
```

### 3. Component State
```python
# CORRECT - Component state with proper tracking
state_manager.update_state({
    "flow_data": {
        "active_component": {
            "type": "amount_input",
            "value": "100.00",
            "validation": {
                "in_progress": False,
                "error": None,
                "attempts": 1,
                "last_attempt": "100.00"
            }
        },
        "step_index": 1,
        "total_steps": 3
    }
})

# WRONG - Component state without tracking
state_manager.update_state({
    "input_value": "100.00",  # Don't store outside flow_data!
    "validation": {           # Don't store without tracking!
        "error": None
    }
})
```

### 4. Error Boundaries
```python
# CORRECT - Error handling with proper context
try:
    # Validate with tracking
    validation = component.validate(value)
    if not validation.valid:
        error_response = ErrorHandler.handle_component_error(
            component=component.type,
            field=validation.error["field"],
            value=value,
            message=validation.error["message"],
            validation_state=component.validation_state
        )
        return error_response

except FlowException as e:
    # Flow error with context
    error_response = ErrorHandler.handle_flow_error(
        step=e.step,
        action=e.action,
        data=e.data,
        message=str(e),
        flow_state=flow_state
    )
    return error_response

# WRONG - Mixed error handling without context
try:
    result = validate_input(value)  # Don't validate without tracking!
    if not result.valid:
        raise APIException(result.error)  # Don't mix error types!
except Exception as e:
    return {"error": str(e)}  # Don't handle without context!
```

## Common Anti-Patterns

### 1. Storing State
```python
# WRONG - Class with stored state
class MessageHandler:
    def __init__(self, state_manager):
        self.state = state_manager  # NO instance state!
        self.channel = state_manager.get("channel")  # NO stored state!

# CORRECT - Pure functions with tracking
def handle_message(state_manager: Any, message: str) -> Response:
    flow_state = state_manager.get_flow_state()  # Get current state
    return process_with_tracking(state_manager, message, flow_state)
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
            "data": response  # Raw response
        }
    })
```

### 3. State Passing
```python
# WRONG - Passing state between functions
def handle_action(state_manager: Any, stored_data: Dict) -> None:
    return process_action(state_manager, stored_data)  # Don't pass state!

# CORRECT - Only state_manager with tracking
def handle_action(state_manager: Any) -> None:
    flow_state = state_manager.get_flow_state()  # Get current state
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
            "step": "verify",
            "step_index": current_index + 1  # Track progress
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
- Progress tracking
- Validation tracking

For more details on:
- Service architecture: [Service Architecture](service-architecture.md)
- API integration: [API Integration](api-integration.md)
- Flow framework: [Flow Framework](flow-framework.md)
