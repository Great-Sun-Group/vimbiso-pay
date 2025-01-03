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
    config = CredExConfig.from_env()
    url = config.get_url(path)
    headers = config.get_headers()

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

    # Make request (implementation details stay in service layer)
    return requests.request(method, url, headers=headers, json=payload)
```

### 2. Service Implementation
```python
def handle_offer(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Handle offer creation through state validation"""
    try:
        # Get flow state for context
        flow_state = state_manager.get_flow_state()
        if not flow_state:
            raise StateException("No active flow")

        # Get validated business data
        flow_data = flow_state.get("data", {})
        amount_data = flow_data.get("amount", {})
        handle = flow_data.get("handle")

        # Track API attempt
        state_manager.update_state({
            "flow_data": {
                "active_component": {
                    "type": "api_call",
                    "validation": {
                        "in_progress": True,
                        "attempts": flow_state.get("api_attempts", 0) + 1,
                        "last_attempt": datetime.utcnow().isoformat()
                    }
                }
            }
        })

        # Make API call (service layer handles implementation details)
        success, result = create_credex_offer(state_manager, amount_data, handle)
        if not success:
            error_response = ErrorHandler.handle_flow_error(
                step="api_call",
                action="create_offer",
                data={"amount": amount_data, "handle": handle},
                message=result.get("message", "API error"),
                flow_state=flow_state
            )
            return False, error_response

        # Update flow state with business response data and progress
        state_manager.update_state({
            "flow_data": {
                "step": "complete",
                "step_index": flow_state["total_steps"],
                "active_component": {
                    "type": "api_call",
                    "validation": {
                        "in_progress": False,
                        "error": None
                    }
                },
                "data": {
                    "offer_id": result.get("data", {}).get("offer", {}).get("id")
                }
            }
        })

        return True, result

    except StateException as e:
        logger.error(f"Offer error: {str(e)}")
        return False, {"message": str(e)}
```

### 3. State Updates
```python
def update_member_state(state_manager: Any, result: Dict[str, Any]) -> None:
    """Update member state from API response with validation tracking"""
    try:
        # Get flow state for context
        flow_state = state_manager.get_flow_state()
        if not flow_state:
            raise StateException("No active flow")

        # Extract response data
        data = result.get("data", {})
        action = data.get("action", {})
        details = action.get("details", {})
        dashboard = data.get("dashboard", {})

        # Track API response processing
        state_manager.update_state({
            "flow_data": {
                "active_component": {
                    "type": "api_response",
                    "validation": {
                        "in_progress": True,
                        "attempts": flow_state.get("api_attempts", 0) + 1,
                        "last_attempt": datetime.utcnow().isoformat()
                    }
                }
            }
        })

        # Update complete state with validation
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
                ),
                # Flow state
                "flow_data": {
                    "step": "complete",
                    "step_index": flow_state["total_steps"],
                    "active_component": {
                        "type": "api_response",
                        "validation": {
                            "in_progress": False,
                            "error": None
                        }
                    }
                }
            })

    except Exception as e:
        error_response = ErrorHandler.handle_system_error(
            code="STATE_UPDATE_ERROR",
            service="member",
            action="update_state",
            message="Failed to update member state",
            error=e
        )
        raise StateException(error_response["error"]["message"])
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
# CORRECT - Update flow state with business data
def handle_offer_response(state_manager: Any, response: Dict[str, Any]) -> None:
    """Handle offer response through state validation"""
    # Extract business data from response
    offer_data = response.get("data", {}).get("offer", {})

    # Update flow state with business data only
    state_manager.update_state({
        "flow_data": {
            "data": {
                "offer_id": offer_data.get("id"),
                "status": offer_data.get("status")
            }
        }
    })

# WRONG - Store raw response in flow state
def handle_offer_response(state_manager: Any, response: Dict[str, Any]) -> None:
    state_manager.update_state({
        "flow_data": {
            "response": response  # Don't store raw response!
        }
    })
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
    # Extract business data from response
    offer_data = response.json().get("data", {}).get("offer", {})

    # Update flow state with business data only
    state_manager.update_state({
        "flow_data": {
            "data": {
                "offer_id": offer_data.get("id"),
                "status": offer_data.get("status")
            }
        }
    })
except Exception as e:
    # Create error context with business data
    error_context = ErrorContext(
        error_type="state",
        message=str(e),
        details={
            "operation": "update_offer_state",
            "offer_id": offer_data.get("id")  # Only business data
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
- Extract business data from responses
- Store only business data in flow state
- Keep implementation details in service layer
- Handle errors through ErrorHandler

For more details on:
- Service architecture: [Service Architecture](service-architecture.md)
- State management: [State Management](state-management.md)
- Flow framework: [Flow Framework](flow-framework.md)
