# Flow Framework

The flow framework provides the core logic that manages member flows through the application. It uses pattern matching for clear, maintainable flow logic.

## Core Flow Management

### Flow Headquarters (flow/headquarters.py)
The central flow management module that:
1. Manages member flows through the application
2. Activates components at each step
3. Determines next steps through branching logic
4. Delegates data management to state manager
5. Delegates action management to components

### Example login

```python

    # Greeting like "hi" intercepted in earlier layer
    # and login/Greeting component was activated and greeting sent

    # Branch based on current path/component and results
    match (path, component):
        case ("login", "Greeting"):
            return "login", "LoginApiCall"  # Basic automatic flow advancement
        case ("login", "LoginApiCall"):
            if flow_state.get("component_result") == "send_dashboard":
                return "account", "AccountDashboard"  # Single-nested conditional flow advancement
            if flow_state.get("component_result") == "start_onboarding":
                return "onboard", "Welcome"  # Single-nested conditional flow advancement
```

## Adding New Flows
1. Add pattern matching cases in get_next_component() as above
2. Create and export components if they don't exist
