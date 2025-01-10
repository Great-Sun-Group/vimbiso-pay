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

```python
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

## Adding New Flows
1. Add pattern matching cases in get_next_component()
2. Create necessary components
3. Export components from core.components
4. Test flow progression
