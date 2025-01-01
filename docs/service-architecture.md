# Service Architecture

## Core Principles

The service architecture follows these key principles:

1. **State-Based Design**
- All services operate through state_manager
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

## Service Layer

### Base Service
```python
def make_credex_request(
    group: str,
    action: str,
    method: str = "POST",
    payload: Dict[str, Any] = None,
    state_manager: Any = None
) -> requests.Response:
    """Make API request through state validation"""
    # Get endpoint info
    path = CredExEndpoints.get_path(group, action)

    # Let StateManager validate through flow state update
    state_manager.update_state({
        "flow_data": {
            "flow_type": group,
            "step": 1,
            "current_step": action,
            "data": {
                "request": {
                    "method": method,
                    "payload": payload
                }
            }
        }
    })

    # Extract credentials from state ONLY when needed
    jwt_token = state_manager.get("jwt_token")
    if jwt_token:
        headers["Authorization"] = f"Bearer {jwt_token}"

    # For auth endpoints, ensure phone from state
    if group == 'auth' and action == 'login':
        channel = state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            raise ConfigurationException("Missing channel identifier")
        payload = {"phone": channel["identifier"]}

    # Make request
    return requests.request(method, url, headers=headers, json=payload)
```

### Service Implementation
```python
def handle_login(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Handle login through state validation"""
    try:
        # Initial login just needs phone number
        success, result = auth_login(state_manager)
        if not success:
            return False, result

        # Extract auth data from response
        data = result.get("data", {})
        action = data.get("action", {})

        # Verify login succeeded
        if action.get("type") != "MEMBER_LOGIN":
            return False, {
                "message": "Invalid login response"
            }

        # Update complete member state
        update_member_state(state_manager, result)

        return True, result

    except StateException as e:
        logger.error(f"Login error: {str(e)}")
        return False, {"message": str(e)}
```

## Service Interactions

### 1. Flow Control
```python
# Flow makes API call through state
response = make_credex_request(
    'credex', 'create',
    payload=payload,
    state_manager=state_manager  # Provides credentials
)

# Update flow state with response
state_manager.update_state({
    "flow_data": {
        "next_step": "complete",
        "data": {
            "response": response.json()
        }
    }
})
```

### 2. State Updates
```python
def update_member_state(state_manager: Any, result: Dict[str, Any]) -> None:
    """Update member state from API response"""
    data = result.get("data", {})
    action = data.get("action", {})
    details = action.get("details", {})
    dashboard = data.get("dashboard", {})

    # Update complete state
    if dashboard.get("member") or dashboard.get("accounts"):
        state_manager.update_state({
            # Auth data
            "jwt_token": details.get("token"),
            "authenticated": True,
            "member_id": details.get("memberID"),
            # Member data
            "member_data": dashboard.get("member"),
            # Account data
            "accounts": dashboard.get("accounts", []),
            "active_account_id": next(
                (account["accountID"] for account in dashboard.get("accounts", [])
                 if account["accountType"] == "PERSONAL"),
                None
            )
        })
```

### 3. Error Handling
```python
try:
    # Make API request through state
    response = make_credex_request(
        'credex', 'create',
        payload=payload,
        state_manager=state_manager
    )
except Exception as e:
    # Create error context
    error_context = ErrorContext(
        error_type="api",
        message=str(e),
        details={
            "operation": "create_credex",
            "payload": payload
        }
    )
    # Let ErrorHandler handle error
    return ErrorHandler.handle_error(
        e,
        state_manager,
        error_context
    )
```

## Best Practices

1. **State Management**
- Let state_manager handle all state
- Extract credentials only when needed
- No storing credentials in variables
- No passing credentials between functions

2. **API Calls**
- Use make_credex_request for all calls
- Let state_manager provide credentials
- Handle errors through ErrorHandler
- Update state with responses

3. **Error Handling**
- Use ErrorHandler for all errors
- Provide clear error context
- Include operation details
- Let state_manager validate errors

4. **Flow Integration**
- Update state before API calls
- Validate through state updates
- Handle errors consistently
- Update state with responses

## Common Patterns

### 1. Credential Access
```python
# CORRECT - Extract from state only when needed
jwt_token = state_manager.get("jwt_token")
if jwt_token:
    headers["Authorization"] = f"Bearer {jwt_token}"

# WRONG - Store credentials in variables
token = state_manager.get("jwt_token")  # Don't store!
make_request(token)  # Don't pass credentials!
```

### 2. State Updates
```python
# CORRECT - Update through state_manager
state_manager.update_state({
    "flow_data": {
        "data": response.json()
    }
})

# WRONG - Transform state manually
data = transform_response(response)  # Don't transform!
state_manager.update_state({"data": data})
```

### 3. Error Handling
```python
# CORRECT - Use ErrorHandler with context
error_context = ErrorContext(
    error_type="api",
    message=str(error),
    details={"operation": operation}
)
ErrorHandler.handle_error(error, state_manager, error_context)

# WRONG - Handle errors manually
if error:
    return {"error": str(error)}  # Don't handle directly!
```

For more details on:
- State management: [State Management](state-management.md)
- Flow framework: [Flow Framework](flow-framework.md)
- API integration: [API Integration](api-integration.md)
