# API Integration

## Core Principles

1. **State-Based Integration**
- All API calls go through state_manager
- Credentials exist ONLY in state
- Extract credentials through proper validation
- Track all validation attempts

2. **Single Source of Truth**
- Member ID accessed through get_member_id()
- Channel info accessed through get_channel_id()
- JWT token accessed through flow_data auth
- No direct state access

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
    try:
        # Update state with request attempt
        state_manager.update_state({
            "flow_data": {
                "active_component": {
                    "type": "api_request",
                    "validation": {
                        "in_progress": True,
                        "attempts": state_manager.get_flow_data().get("api_attempts", 0) + 1,
                        "last_attempt": datetime.utcnow().isoformat()
                    }
                }
            }
        })

        # Get endpoint info
        path = CredExEndpoints.get_path(group, action)
        config = CredExConfig.from_env()
        url = config.get_url(path)
        headers = config.get_headers()

        # Get auth token through flow data
        auth_data = state_manager.get_flow_data().get("auth", {})
        if auth_data.get("token"):
            headers["Authorization"] = f"Bearer {auth_data['token']}"

        # For auth endpoints, get channel through proper method
        if group == 'auth' and action == 'login':
            try:
                channel_id = state_manager.get_channel_id()
                payload = {"phone": channel_id}
            except ComponentException as e:
                raise ConfigurationException("Missing channel identifier")

        # Make request (implementation details stay in service layer)
        return requests.request(method, url, headers=headers, json=payload)

    except Exception as e:
        # Update state with error
        state_manager.update_state({
            "flow_data": {
                "active_component": {
                    "type": "api_request",
                    "validation": {
                        "in_progress": False,
                        "error": {
                            "message": str(e),
                            "details": {
                                "group": group,
                                "action": action
                            }
                        }
                    }
                }
            }
        })
        raise
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
        flow_data = state_manager.get_flow_data()
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
                "flow_data": {
                    "auth": {
                        "token": details.get("token"),
                        "authenticated": True,
                        "member_id": details.get("memberID")
                    },
                    "member": dashboard.get("member"),
                    "accounts": dashboard.get("accounts", []),
                    "active_account": next(
                        (account for account in dashboard.get("accounts", [])
                         if account["accountType"] == "PERSONAL"),
                        None
                    ),
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
# CORRECT - Access through flow data with validation
def make_api_call(state_manager: Any) -> None:
    """Make API call through state validation"""
    # Update state with request attempt
    state_manager.update_state({
        "flow_data": {
            "active_component": {
                "type": "api_request",
                "validation": {
                    "in_progress": True,
                    "attempts": state_manager.get_flow_data().get("api_attempts", 0) + 1,
                    "last_attempt": datetime.utcnow().isoformat()
                }
            }
        }
    })

    # Get auth token through flow data
    auth_data = state_manager.get_flow_data().get("auth", {})
    if auth_data.get("token"):
        headers["Authorization"] = f"Bearer {auth_data['token']}"

    # Make request with validated token
    response = requests.post(url, headers=headers)

# WRONG - Direct state access
def make_api_call(state_manager: Any) -> None:
    token = state_manager.get("jwt_token")  # Don't access directly!
    make_request(token)  # Don't pass credentials!
```

### 2. Channel Access
```python
# CORRECT - Use proper accessor method
def handle_auth(state_manager: Any) -> None:
    """Handle auth through state validation"""
    try:
        # Get channel through proper method
        channel_id = state_manager.get_channel_id()
        payload = {"phone": channel_id}
        response = make_request(payload)
    except ComponentException as e:
        # Handle validation error
        error_response = ErrorHandler.handle_component_error(
            component="auth_handler",
            field="channel_id",
            value=None,
            message=str(e)
        )
        return error_response

# WRONG - Direct state access
def handle_auth(state_manager: Any) -> None:
    channel = state_manager.get("channel")  # Don't access directly!
    phone = channel["identifier"]  # Don't access structure directly!
    make_auth_call(phone)  # Don't pass raw data!
```

### 3. Response Handling
```python
# CORRECT - Update flow state with business data and validation
def handle_offer_response(state_manager: Any, response: Dict[str, Any]) -> None:
    """Handle offer response through state validation"""
    # Extract business data from response
    offer_data = response.get("data", {}).get("offer", {})

    # Update flow state with business data and validation
    state_manager.update_state({
        "flow_data": {
            "active_component": {
                "type": "api_response",
                "validation": {
                    "in_progress": False,
                    "error": None,
                    "attempts": state_manager.get_flow_data().get("response_attempts", 0) + 1,
                    "last_attempt": datetime.utcnow().isoformat()
                }
            },
            "data": {
                "offer_id": offer_data.get("id"),
                "status": offer_data.get("status")
            }
        }
    })

# WRONG - Store raw response without validation
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
    # Update state with error
    state_manager.update_state({
        "flow_data": {
            "active_component": {
                "type": "api_request",
                "validation": {
                    "in_progress": False,
                    "error": {
                        "message": str(e),
                        "details": {
                            "operation": "create_credex",
                            "payload": payload
                        }
                    }
                }
            }
        }
    })

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

    # Update flow state with business data and validation
    state_manager.update_state({
        "flow_data": {
            "active_component": {
                "type": "api_response",
                "validation": {
                    "in_progress": False,
                    "error": None,
                    "attempts": state_manager.get_flow_data().get("response_attempts", 0) + 1,
                    "last_attempt": datetime.utcnow().isoformat()
                }
            },
            "data": {
                "offer_id": offer_data.get("id"),
                "status": offer_data.get("status")
            }
        }
    })
except Exception as e:
    # Update state with error
    state_manager.update_state({
        "flow_data": {
            "active_component": {
                "type": "api_response",
                "validation": {
                    "in_progress": False,
                    "error": {
                        "message": str(e),
                        "details": {
                            "operation": "update_offer_state",
                            "offer_id": offer_data.get("id")
                        }
                    }
                }
            }
        }
    })

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

1. **State Access**
- Use proper accessor methods (get_channel_id, get_member_id)
- Access auth data through flow_data
- Track all validation attempts
- Handle validation errors properly

2. **State Updates**
- Update state with validation tracking
- Track all operation attempts
- Include proper error context
- Let state_manager validate all updates

3. **Error Handling**
- Update state with error context
- Track validation failures
- Include operation details
- Let ErrorHandler handle errors

4. **Response Processing**
- Track response processing attempts
- Include validation state
- Store only business data
- Handle errors with context

For more details on:
- Service architecture: [Service Architecture](service-architecture.md)
- State management: [State Management](state-management.md)
- Flow framework: [Flow Framework](flow-framework.md)
