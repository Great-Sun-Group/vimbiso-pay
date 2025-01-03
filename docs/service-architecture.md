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

### Messaging Service
```python
class MessagingService:
    """Coordinates messaging operations with proper tracking"""

    def __init__(self, messaging_service: MessagingServiceInterface):
        """Initialize with channel-specific messaging service"""
        self.messaging = messaging_service
        self.member = MemberHandler(messaging_service)
        self.auth = AuthHandler(messaging_service)
        self.account = AccountHandler(messaging_service)
        self.credex = CredexHandler(messaging_service)

    def handle_message(self, state_manager: Any, message_type: str, message_text: str) -> Message:
        """Handle incoming message with proper tracking"""
        try:
            # Check if we're in a flow
            flow_data = state_manager.get_flow_state()
            if flow_data:
                flow_type = flow_data.get("flow_type")
                handler_type = flow_data.get("handler_type")
                current_step = flow_data.get("step")

                # Track message handling
                state_manager.update_state({
                    "flow_data": {
                        "active_component": {
                            "type": "message_handler",
                            "validation": {
                                "in_progress": True,
                                "attempts": flow_data.get("message_attempts", 0) + 1,
                                "last_attempt": datetime.utcnow().isoformat()
                            }
                        }
                    }
                })

                # Route to appropriate handler with progress
                if handler_type == "member":
                    result = self.member.handle_flow_step(
                        state_manager,
                        flow_type,
                        current_step,
                        message_text
                    )
                elif handler_type == "account":
                    result = self.account.handle_flow_step(
                        state_manager,
                        flow_type,
                        current_step,
                        message_text
                    )
                elif handler_type == "credex":
                    result = self.credex.handle_flow_step(
                        state_manager,
                        flow_type,
                        current_step,
                        message_text
                    )
                else:
                    error_response = ErrorHandler.handle_flow_error(
                        step=current_step,
                        action="route",
                        data={"handler_type": handler_type},
                        message=f"Invalid handler type: {handler_type}",
                        flow_state=flow_data
                    )
                    return self.messaging.send_text(
                        recipient=self._get_recipient(state_manager),
                        text=f"❌ {error_response['error']['message']}"
                    )

                # Update message handling state
                state_manager.update_state({
                    "flow_data": {
                        "active_component": {
                            "type": "message_handler",
                            "validation": {
                                "in_progress": False,
                                "error": None
                            }
                        }
                    }
                })

                return result

            # Not in flow - handle initial operations with tracking
            if not state_manager.get("authenticated"):
                # Track authentication attempt
                state_manager.update_state({
                    "auth_attempts": state_manager.get("auth_attempts", 0) + 1,
                    "last_auth_attempt": datetime.utcnow().isoformat()
                })

                # Attempt login first
                if message_text.lower() in ["hi", "hello"]:
                    return self.auth.handle_greeting(state_manager)
                # Otherwise start registration
                return self.member.start_registration(state_manager)

            # Route authenticated commands with tracking
            state_manager.update_state({
                "command_history": {
                    "last_command": message_text,
                    "timestamp": datetime.utcnow().isoformat()
                }
            })

            if message_text == "upgrade":
                return self.member.start_upgrade(state_manager)
            elif message_text == "ledger":
                return self.account.start_ledger(state_manager)
            elif message_text == "offer":
                return self.credex.start_offer(state_manager)
```

### Handler Implementation
```python
class AuthHandler:
    """Handler for authentication operations"""

    def __init__(self, messaging_service: MessagingServiceInterface):
        self.messaging = messaging_service

    def handle_greeting(self, state_manager: Any) -> Message:
        """Handle initial greeting with login attempt"""
        try:
            # Attempt login through messaging service
            success, response = self.attempt_login(state_manager)

            if success:
                # Update auth state
                state_manager.update_state({
                    "member_id": response["memberID"],
                    "jwt_token": response["token"],
                    "authenticated": True
                })

                # Update flow state
                state_manager.update_state({
                    "flow_data": {
                        "flow_type": "dashboard",
                        "handler_type": "member",
                        "step": "main",
                        "step_index": 0
                    }
                })

                return self.messaging.send_dashboard(
                    recipient=self._get_recipient(state_manager),
                    dashboard_data=response["dashboard"]
                )

            else:
                # Start registration for new users
                return self.messaging.send_text(
                    recipient=self._get_recipient(state_manager),
                    text="👋 Welcome! Let's get you registered."
                )

        except Exception as e:
            return self.messaging.send_error(
                recipient=self._get_recipient(state_manager),
                error=str(e)
            )
```

## Service Interactions

### 1. Handler Routing
```python
# Get flow state with handler type
flow_state = state_manager.get_flow_state()
handler_type = flow_state.get("handler_type")

# Route to appropriate handler
if handler_type == "member":
    handler = MemberHandler(messaging_service)
elif handler_type == "account":
    handler = AccountHandler(messaging_service)
elif handler_type == "credex":
    handler = CredexHandler(messaging_service)

# Process through handler
result = handler.handle_flow_step(
    state_manager,
    flow_state["flow_type"],
    flow_state["step"],
    input_value
)

# Update flow state with result
state_manager.update_state({
    "flow_data": {
        "data": result.data,
        "step_index": flow_state["step_index"] + 1,
        "active_component": {
            "type": result.next_component,
            "validation": {"in_progress": False}
        }
    }
})
```

### 2. Handler State Management
```python
class MemberHandler:
    """Handler for member operations"""

    def handle_flow_step(self, state_manager: Any, flow_type: str, step: str, input_value: Any) -> Message:
        """Handle flow step"""
        try:
            # Validate input through component
            component = self.get_component(flow_type, step)
            validation = component.validate(input_value)
            if not validation.valid:
                return self.messaging.send_error(
                    recipient=self._get_recipient(state_manager),
                    error=validation.error
                )

            # Update flow state with verified data
            state_manager.update_state({
                "flow_data": {
                    "data": component.to_verified_data(input_value),
                    "step_index": state_manager.get_flow_state()["step_index"] + 1
                }
            })

            # Get next step
            next_step = self.get_next_step(flow_type, step)
            if not next_step:
                return self.complete_flow(state_manager)

            # Update step state
            state_manager.update_state({
                "flow_data": {
                    "step": next_step,
                    "active_component": {
                        "type": self.get_component_type(flow_type, next_step),
                        "validation": {"in_progress": False}
                    }
                }
            })

            return self.get_step_message(next_step)

        except Exception as e:
            return self.messaging.send_error(
                recipient=self._get_recipient(state_manager),
                error=str(e)
            )
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
