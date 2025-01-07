# Flow Framework

## Overview

The flow framework provides a context-based approach to managing user interactions and state transitions. It uses pattern matching for clear, maintainable flow logic and maintains strong validation throughout.

## Core Components

### Flow Management (core/messaging/flow.py)
- Context-based routing using pattern matching
- Simple component activation
- Pure functional approach
- No stored state

Example:
```python
def activate_component(component_type: str, input_data: Any = None) -> Any:
    """Create and activate a component"""
    component_class = getattr(components, component_type)
    return component_class().validate(input_data)

def handle_component_result(context: str, component: str, result: Any) -> Tuple[str, str]:
    """Handle component result and determine next component"""
    match (context, component):
        case ("login", "Greeting"):
            return "login", "LoginApiCall"
        case ("login", "LoginApiCall"):
            if result.get("not_found"):
                return "onboard", "Welcome"
            return "account", "AccountDashboard"
```

### Component System
The component system follows a clear inheritance hierarchy:

1. Base Components
- Component - Core interface with validation tracking
- DisplayComponent - Base for display components
- InputComponent - Base for input components
- ApiComponent - Base for API components
- ConfirmBase - Base for confirmation components

2. Display Components
- Handle UI presentation
- Access state through state_manager
- Format data for display
- Example: ViewLedger, OfferListDisplay

3. Input Components
- Handle user input validation
- Pure UI validation
- Business validation in services
- Example: AmountInput, HandleInput

4. API Components
- Handle external API calls
- Access state through state_manager
- Validate API responses
- Example: LoginApiCall, CreateCredexApiCall

5. Confirm Components
- Extend ConfirmBase
- Handle specific confirmation flows
- Context-aware messaging
- Example: ConfirmOfferSecured, ConfirmUpgrade

Example component:
```python
class ApiComponent(Component):
    """Base class for API components"""

    def __init__(self, component_type: str):
        super().__init__(component_type)
        self.state_manager = None
        self.bot_service = None

    def validate_api_call(self, value: Any) -> ValidationResult:
        """Component-specific API validation logic"""
        raise NotImplementedError

class CreateCredexApiCall(ApiComponent):
    """Handles creating a new Credex offer"""

    def validate_api_call(self, value: Any) -> ValidationResult:
        # Get offer data from state
        offer_data = self.state_manager.get_flow_data().get("data", {})

        # Validate and make API call
        success, message = create_credex(
            self.bot_service,
            offer_data.get("amount"),
            offer_data.get("handle")
        )

        if not success:
            return ValidationResult.failure(
                message=f"Failed to create Credex: {message}"
            )

        return ValidationResult.success({"credex_created": True})
```

### State Management
- Context tracking
- Component state
- Validation tracking
- Clear boundaries

Example state structure:
```python
{
    "flow_data": {
        "context": str,      # Current context
        "component": str,    # Active component
        "data": dict,       # Flow data
        "validation": {      # Validation tracking
            "in_progress": bool,
            "attempts": int,
            "last_attempt": dict
        }
    }
}
```

## Key Principles

1. **Context-Based Flows**
- Flows organized by context
- Clear state transitions
- Pattern matching for routing
- Pure functional approach

2. **Clear Boundaries**
- Components handle validation
- State manages persistence
- Flow handles routing
- No mixed responsibilities

3. **Strong Validation**
- Component-level validation
- State validation
- Flow validation
- Clear error handling

4. **Pure Functions**
- No stored state
- Clear inputs/outputs
- Predictable behavior
- Easy testing

## Common Patterns

### 1. Flow Progression
```python
# Process component
result = activate_component(component, input_data)

# Get next step
next_context, next_component = handle_component_result(
    context, component, result
)

# Update state
state_manager.update_flow_state(
    next_context,
    next_component,
    {"result": result}
)
```

### 2. Component Activation
```python
# Get and activate component
component_class = getattr(components, component_type)
result = component_class().validate(input_data)

# Handle validation
if isinstance(result, ValidationResult):
    if not result.valid:
        return result.error
```

### 3. State Updates
```python
# Update flow state
state_manager.update_flow_state(
    context="login",
    component="Greeting",
    data={"user_input": value}
)
```

## Best Practices

1. **Flow Management**
- Use pattern matching for clarity
- Keep context transitions explicit
- Handle errors uniformly
- Maintain pure functions

2. **State Management**
- Track validation state
- Maintain clear boundaries
- Use proper accessors
- Keep atomic updates

3. **Component Usage**
- Extend appropriate base component
- Focus on specific responsibility
- Maintain pure functions
- Track validation state
- Clear error handling

4. **Error Handling**
- Uniform error handling
- Clear error context
- Proper validation state
- Consistent patterns

## Common Modifications

### Adding New Components
1. Choose appropriate base component
2. Implement required methods
3. Add to core.components
4. Test thoroughly

### Adding New Flows
1. Add pattern matching cases in handle_component_result()
2. Create necessary components
3. Export components from core.components
4. Test flow progression

### Adding Validation
1. Add validation to components
2. Update state tracking
3. Handle errors properly
4. Test edge cases
