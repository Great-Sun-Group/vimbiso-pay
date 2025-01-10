# Flow Framework

## Overview

The flow framework, centered in `app/core/flow/headquarters.py`, provides the core logic that manages member flows through the application. It uses pattern matching for clear, maintainable flow logic and maintains strong validation throughout.

## Core Flow Management

### Flow Headquarters (flow/headquarters.py)
The central flow management module that:
1. Manages member flows through the application
2. Activates components at each step
3. Determines next steps through branching logic
4. Delegates data management to state manager
5. Delegates action management to components

Example:
```python
def get_next_component(path: str, component: str, state_manager: StateManagerInterface):
    """Determine next step based on current completion and component_result"""
    # Check if component is awaiting input
    flow_state = state_manager.get_flow_state()
    if flow_state.get("awaiting_input"):
        return path, component  # Stay at current step until input received

    # Branch based on current path/component and results
    match (path, component):
        case ("login", "Greeting"):
            return "login", "LoginApiCall"
        case ("login", "LoginApiCall"):
            if flow_state.get("component_result") == "send_dashboard":
                return "account", "AccountDashboard"
            if flow_state.get("component_result") == "start_onboarding":
                return "onboard", "Welcome"
```

## Component System

Components are self-contained with responsibility for their own:
- Business logic and validation
- Activation of shared utilities/helpers/services
- State access to communicate with other parts of the system
- State access for in-component loop management
- State writing to leave flow headquarters with results
- Error handling

### Component Types

1. **Display Components**
- Handle UI presentation
- Access state through state_manager
- Format data for display
- Example: ViewLedger, OfferListDisplay

2. **Input Components**
- Handle user input validation
- Pure UI validation
- Business validation in services
- Example: AmountInput, HandleInput

3. **API Components**
- Handle external API calls
- Access state through state_manager
- Validate API responses
- Example: LoginApiCall, CreateCredexApiCall

4. **Confirm Components**
- Extend ConfirmBase
- Handle specific confirmation flows
- Context-aware messaging
- Example: ConfirmOfferSecured, ConfirmUpgrade

## Common Anti-Patterns to Avoid

### 1. State Access
```python
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
1. Add pattern matching cases in get_next_component()
2. Create necessary components
3. Export components from core.components
4. Test flow progression

### Adding Validation
1. Add validation to components
2. Update state tracking
3. Handle errors properly
4. Test edge cases
