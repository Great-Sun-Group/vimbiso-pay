# Service & API Architecture

## Core Principles

1. **API Response Structure**
- All responses include two sections:
  * dashboard -> Member state after operation
  * action -> Operation results and details
- Each section handled by dedicated module:
  * dashboard.py -> Updates member state
  * action.py -> Updates operation results
- Clear separation of concerns

2. **Dashboard as Source of Truth**
- dashboard.py handles member state
- All member data comes from dashboard
- Components read from dashboard
- No direct member state management
- Single source for member info

3. **Action Data Management**
- action.py handles operation results
- Components get action data for flow
- Operation details in action state
- Clear operation tracking
- Flow control through actions

4. **Component Patterns**

### API Component Pattern
```python
class ApiComponent(Component):
    def validate(self, value: Any) -> ValidationResult:
        try:
            # 1. Get member data from dashboard
            dashboard = self.state_manager.get("dashboard")
            member_id = dashboard.get("member", {}).get("memberID")

            # 2. Make API call directly
            url = f"endpoint/{member_id}"
            headers = {"x-client-api-key": config("CLIENT_API_KEY")}
            response = make_api_request(url, headers, payload)

            # 3. Let handlers update state
            response_data, error = handle_api_response(
                response=response,
                state_manager=self.state_manager
            )
            if error:
                return ValidationResult.failure(message=error)

            # 4. Use action data for flow
            flow_data = self.state_manager.get_flow_state()
            action_data = flow_data.get("action", {})
            return ValidationResult.success({"action": action_data})

        except Exception as e:
            # Handle errors through ErrorHandler
            error_response = ErrorHandler.handle_component_error(
                component=self.type,
                field="api_call",
                value=str(payload),
                message=str(e)
            )
            return ValidationResult.failure(message=error_response["error"]["message"])
```

### Display Component Pattern
```python
class DisplayComponent(Component):
    def validate_display(self, value: Any) -> ValidationResult:
        try:
            # 1. Get display data from state
            display_data = self.get_display_data()

            # 2. Send through messaging service
            recipient = get_recipient(self.state_manager)
            self.state_manager.messaging.send_text(
                recipient=recipient,
                text=display_data
            )

            # 3. Return success with sent data
            return ValidationResult.success({
                "sent": True,
                "message": display_data
            })

        except Exception as e:
            # Handle errors through ErrorHandler
            error_response = ErrorHandler.handle_component_error(
                component=self.type,
                field="display",
                value=str(value),
                message=str(e)
            )
            return ValidationResult.failure(message=error_response["error"]["message"])
```

## Implementation Guide

### API Response Flow
1. Component makes API call directly through base.make_api_request
2. Response contains dashboard and action sections:
```python
{
    "data": {
        "dashboard": {  # Member state after operation
            "member": { "memberID": "..." },
            "accounts": [...],
            ...
        },
        "action": {    # Operation results
            "id": "...",
            "type": "...",
            "details": {...}
        }
    }
}
```
3. base.handle_api_response routes to handlers:
   - dashboard.update_dashboard_from_response -> Updates member state
   - action.update_action_from_response -> Updates operation state
4. Component reads action data for flow control
5. Component uses dashboard data for future calls

### State Management
1. Dashboard State (Source of Truth)
   - Member core data
   - Account information
   - Balance details
   - Updated by dashboard.py

2. Action State (Operation Results)
   - Operation ID
   - Operation type
   - Timestamps
   - Details/results
   - Updated by action.py

3. Component State (Minimal)
   - Reads from dashboard
   - Uses action data
   - Clear boundaries
   - No state duplication

### Common Patterns

1. Direct API Calls with Error Handling
```python
try:
    # Make API call directly
    response = make_api_request(url, headers, payload)

    # Let handlers manage state and errors
    response_data, error = handle_api_response(response, state_manager)
    if error:
        return ValidationResult.failure(message=error)

    return ValidationResult.success({"action": response_data})

except Exception as e:
    # Use ErrorHandler for all errors
    error_response = ErrorHandler.handle_component_error(
        component=self.type,
        field="api_call",
        value=str(payload),
        message=str(e)
    )
    return ValidationResult.failure(message=error_response["error"]["message"])
```

2. Message Sending with Error Handling
```python
try:
    # Send through messaging service
    recipient = get_recipient(self.state_manager)
    self.state_manager.messaging.send_text(
        recipient=recipient,
        text=message_text
    )

    # Return success with sent data
    return ValidationResult.success({
        "sent": True,
        "message": message_text
    })

except Exception as e:
    # Use ErrorHandler for all errors
    error_response = ErrorHandler.handle_component_error(
        component=self.type,
        field="messaging",
        value=str(message_text),
        message=str(e)
    )
    return ValidationResult.failure(message=error_response["error"]["message"])
```

3. State Updates with Error Handling
```python
try:
    # Update state with validation
    self.state_manager.update_state({
        "flow_data": {
            "context": context,
            "component": component,
            "data": data,
            "validation": {
                "in_progress": False,
                "attempts": current_attempts + 1,
                "last_attempt": datetime.utcnow().isoformat()
            }
        }
    })

except Exception as e:
    # Use ErrorHandler for all errors
    error_response = ErrorHandler.handle_component_error(
        component=self.type,
        field="state_update",
        value=str(data),
        message=str(e)
    )
    return ValidationResult.failure(message=error_response["error"]["message"])
```

## Code Reading Guide

Before modifying service-related functionality, read these files in order:

1. core/api/base.py - API handling
   - How to make API calls
   - How responses are processed
   - How handlers are called

2. core/api/dashboard.py - Dashboard state
   - How member state is updated
   - How validation works
   - Single source of truth

3. core/api/action.py - Action state
   - How operation results are handled
   - How flow data is managed
   - Clear operation tracking

4. core/components/upgrade_membertier_api_call.py - Example component
   - How to make API calls directly
   - How to use dashboard data
   - How to handle responses

Common mistakes to avoid:
1. DON'T add extra API modules - make calls directly
2. DON'T add extra state validation - use handlers
3. DON'T duplicate error handling - use ValidationResult
4. DON'T mix component responsibilities

For implementation details, see:
- [State Management](state-management.md) - State validation and flow control
- [Flow Framework](flow-framework.md) - Progressive interaction framework
