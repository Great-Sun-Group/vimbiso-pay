# API Integration

## Core Principles

1. **State-Based Integration**
- All API calls go through state_manager
- Credentials exist ONLY in state
- Extract credentials only when needed
- Validate through state updates

2. **Single Source of Truth**
- Member ID ONLY at top level
- Channel info ONLY at top level
- JWT token ONLY in state
- No credential duplication

3. **Pure Functions**
- Stateless service functions
- No stored credentials
- No instance variables
- Clear contracts

## Implementation

### 1. Base Request Handler
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

### 2. Service Implementation
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

### 3. State Updates
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

## Common Patterns

### 1. Credential Access
```python
# CORRECT - Extract from state only when needed
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

### 2. Phone Number Access
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

# WRONG - Store phone in variables
def handle_auth(state_manager: Any) -> None:
    phone = state_manager.get("channel")["identifier"]  # Don't store!
    make_auth_call(phone)  # Don't pass phone!
```

### 3. Response Handling
```python
# CORRECT - Update state with response
def handle_response(state_manager: Any, response: Dict[str, Any]) -> None:
    """Handle response through state validation"""
    # Let StateManager validate response data
    state_manager.update_state({
        "flow_data": {
            "response": response
        }
    })

# WRONG - Transform response manually
def handle_response(state_manager: Any, response: Dict[str, Any]) -> None:
    data = transform_response(response)  # Don't transform!
    state_manager.update_state({"data": data})
```

## Error Handling

### 1. API Errors
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

### 2. State Errors
```python
try:
    # Update state with response
    state_manager.update_state({
        "flow_data": {
            "response": response.json()
        }
    })
except Exception as e:
    # Create error context
    error_context = ErrorContext(
        error_type="state",
        message=str(e),
        details={
            "operation": "update_response",
            "response": response.json()
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

1. **Credential Management**
- Extract credentials only when needed
- No storing credentials in variables
- No passing credentials between functions
- Let state_manager handle all credentials

2. **State Updates**
- Update state before API calls
- Update state with responses
- No manual state transformation
- Let state_manager validate all updates

3. **Error Handling**
- Use ErrorHandler for all errors
- Provide clear error context
- Include operation details
- Let state_manager validate errors

4. **Response Processing**
- Update state with raw responses
- No manual response transformation
- Let state_manager validate responses
- Handle errors through ErrorHandler

For more details on:
- Service architecture: [Service Architecture](service-architecture.md)
- State management: [State Management](state-management.md)
- Flow framework: [Flow Framework](flow-framework.md)
