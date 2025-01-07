# Service & API Architecture

## Core Principles

1. **API Response Structure**
- All responses include two sections:
  * dashboard -> Member state after operation
  * action -> Operation results and details
- Each section handled by dedicated module
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

4. **Component Responsibilities**
- Make API calls with proper data
- Let handlers manage state updates
- Read from dashboard for member data
- Use action data for flow decisions
- Keep focused responsibilities

## Common Anti-Patterns

### 1. Credential Access
```python
# WRONG - Store or pass credentials
token = state_manager.get("jwt_token")  # Don't store!
make_request(token)  # Don't pass credentials!

# CORRECT - Access through flow data
auth_data = state_manager.get_flow_data().get("auth", {})
if auth_data.get("token"):
    headers["Authorization"] = f"Bearer {auth_data['token']}"
```

### 2. State Management
```python
# WRONG - Direct state access
channel = state_manager.get("channel")  # Don't access directly!
phone = channel["identifier"]  # Don't access structure directly!

# CORRECT - Use proper accessor methods
channel_id = state_manager.get_channel_id()
member_id = state_manager.get_member_id()
```

### 3. Error Handling
```python
# WRONG - Handle errors manually
if error:
    return {"error": str(error)}  # Don't handle directly!

# CORRECT - Use ErrorHandler with context
error_context = ErrorContext(
    error_type="api",
    message=str(error),
    details={"operation": operation}
)
ErrorHandler.handle_error(error, state_manager, error_context)
```

## Implementation Guide

### API Response Flow
1. Component makes API call
2. Response contains dashboard and action sections
3. base.handle_api_response routes to handlers:
   - dashboard.update_dashboard_from_response -> Updates member state
   - action.update_action_from_response -> Updates operation state
4. Component reads action data for flow control
5. Component uses dashboard data for future calls

### State Management
1. Dashboard State
   - Member core data
   - Account information
   - Balance details
   - Single source of truth

2. Action State
   - Operation ID
   - Operation type
   - Timestamps
   - Details/results
   - Flow metadata

3. Component State
   - Minimal local state
   - Reads from dashboard
   - Uses action data
   - Clear boundaries

### API Integration
1. All API calls through state_manager
2. Extract credentials only when needed
3. Track validation attempts
4. Handle errors through ErrorHandler

### State Updates
1. Update through state_manager
2. Include validation tracking
3. Track operation attempts
4. Include error context

### Error Handling
1. Use ErrorHandler for all errors
2. Include operation details
3. Track validation failures
4. Update state with errors

## Code Reading Guide

Before modifying service-related functionality, read these files in order:

1. services/messaging/service.py - Core messaging service
2. services/whatsapp/service.py - Channel-specific handling
3. services/whatsapp/bot_service.py - Bot handling
4. services/whatsapp/types.py - Service types

Common mistakes to avoid:
1. DON'T modify services without understanding types
2. DON'T bypass service interfaces
3. DON'T mix service responsibilities
4. DON'T duplicate service functionality

For implementation details, see:
- [State Management](state-management.md) - State validation and flow control
- [Flow Framework](flow-framework.md) - Progressive interaction framework
