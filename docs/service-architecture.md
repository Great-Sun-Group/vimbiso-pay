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

4. **Component Pattern**
```python
class ApiComponent(Component):
    def validate(self, value: Any) -> ValidationResult:
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

### Common Anti-Patterns

1. Using API Modules
```python
# WRONG - Extra layer through module
from core.api.credex import create_credex
success, message = create_credex(bot_service, member_id, amount)

# CORRECT - Direct API call
response = make_api_request(url, headers, payload)
response_data, error = handle_api_response(response, state_manager)
```

2. Extra State Validation
```python
# WRONG - Extra validation layer
state_manager.update_state({
    "api_request": {"type": "credex_offer"}
})

# CORRECT - Let handlers manage state
response_data, error = handle_api_response(response, state_manager)
```

3. Duplicate Error Handling
```python
# WRONG - Custom error handling
if response.status_code == 200:
    return {"success": True, "data": response.json()}
return handle_error_response(...)

# CORRECT - Use ValidationResult
if error:
    return ValidationResult.failure(message=error)
return ValidationResult.success({"action": action_data})
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
