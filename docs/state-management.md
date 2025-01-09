# State Management

## Overview

VimbisoPay uses a layered state management approach with Redis as the persistence layer:

1. **StateManager**: High-level interface for state operations
2. **AtomicStateManager**: Validation and transaction handling
3. **RedisAtomic**: Low-level atomic Redis operations

## Code Reading Guide

Before modifying state management, read these files in order:

1. core/config/interface.py - Understand state management interface
   - Learn interface methods
   - Understand type safety
   - Review state boundaries

2. core/config/state_utils.py - Understand state update preparation
   - Learn validation patterns
   - Understand state preparation
   - Review update flow

3. core/config/state_manager.py - Understand state management implementation
   - Learn state access patterns
   - Understand atomic updates
   - Review state validation

4. core/utils/state_validator.py - Learn validation rules
   - Understand state validation
   - Learn validation patterns
   - Review validation rules

5. core/messaging/base.py - Understand state usage
   - Learn state integration
   - Understand state flow
   - Review state patterns

6. core/config/atomic_state.py - Learn atomic operations
   - Understand state atomicity
   - Learn transaction patterns
   - Review rollback handling

Common mistakes to avoid:
1. DON'T modify state without understanding validation
2. DON'T bypass state manager for direct access
3. DON'T mix state responsibilities
4. DON'T duplicate state across components
5. DON'T access internal state directly (e.g., _state)
6. DON'T create circular dependencies between modules

## Core Principles

1. **Clear Module Boundaries**
- Interface defines state management contract
- Utils prepare state updates with validation
- Manager implements atomic state updates
- NO circular dependencies
- NO direct state access
- NO implementation leaks

2. **Single Source of Truth**
- Channel info accessed through get_channel_id()
- JWT token accessed through flow_data auth
- Member data accessed through dashboard state
- Messaging service accessed through state_manager.messaging
- NO direct state access
- NO state passing
- NO transformation

3. **State Persistence**
- Redis as persistent storage
- Atomic operations for consistency
- AOF persistence for durability
- Transaction handling for safety
- NO direct Redis access
- NO manual persistence

4. **Component Responsibilities**
- Components handle their own operations:
  * API calls through make_api_request
  * Message sending through state_manager.messaging
  * Error handling through ErrorHandler
  * State updates with validation
- Clear boundaries between components:
  * Display components -> UI and messaging
  * Input components -> Validation and state updates
  * API components -> External calls and state updates
  * Confirm components -> User confirmation flows
- Standard validation and error handling:
  * All operations wrapped in try/except
  * All errors handled through ErrorHandler
  * All results returned as ValidationResult

5. **Pure Functions**
- Stateless operations
- Clear validation
- Standard updates
- NO stored state
- NO side effects
- NO manual handling

6. **Central Management**
- Single state manager
- Standard validation
- Clear boundaries
- Context tracking
- NO manual updates
- NO local state

## State Structure

### 1. Core State
```python
{
    "channel": {
        "type": str,        # Channel type (e.g., "whatsapp")
        "identifier": str   # Channel ID
    },
    "flow_data": {
        "context": str,     # Current flow context
        "component": str,   # Active component
        "data": dict,       # Flow-specific data
        "validation": {     # Validation state
            "in_progress": bool,
            "attempts": int,
            "last_attempt": dict
        }
    },
    "_metadata": {
        "initialized_at": datetime,
        "updated_at": datetime
    },
    "_validation": {
        "in_progress": bool,
        "attempts": dict,
        "last_attempt": dict,
        "error": Optional[str]
    }
}
```

### 2. Redis Storage
- Key format: `channel:{channel_id}`
- TTL: 300 seconds (5 minutes)
- JSON serialization
- AOF persistence
- Atomic operations

### Component Integration

Each component type has specific state integration patterns:

1. **Display Components**
- Access state through state_manager
- Read-only state access
- Format state data for display
- No state modifications
- Example:
```python
class ViewLedger(DisplayComponent):
    def validate_display(self, value: Any) -> ValidationResult:
        active_account_id = self.state_manager.get("active_account_id")
        dashboard = self.state_manager.get("dashboard")
        # Format for display...
```

2. **Input Components**
- Validate input format
- Update state with validated input
- Track validation attempts
- No direct state reads
- Example:
```python
class AmountInput(InputComponent):
    def validate(self, value: Any) -> ValidationResult:
        # Validate format...
        self.update_state(str(amount), ValidationResult.success(amount))
```

3. **API Components**
- Get member data from dashboard
- Make API call with proper data
- Let handlers manage state updates:
  * dashboard.py -> Updates member state
  * action.py -> Updates operation state
- Use action data for flow control
- Example:
```python
class UpgradeMemberApiCall(ApiComponent):
    def validate(self, value: Any) -> ValidationResult:
        # Get member data from dashboard
        dashboard = self.state_manager.get("dashboard")
        member_id = dashboard.get("member", {}).get("memberID")

        # Make API call
        response = make_api_request(url, headers, payload)

        # Let handlers update state
        response_data, error = handle_api_response(
            response=response,
            state_manager=self.state_manager
        )

        # Use action data for flow
        flow_data = self.state_manager.get_flow_state()
        action_data = flow_data.get("action", {})
        return ValidationResult.success({"action": action_data})
```

4. **Confirm Components**
- Access state for confirmation context
- Update state with confirmation result
- Context-aware validation
- Track confirmation attempts
- Example:
```python
class ConfirmUpgrade(ConfirmBase):
    def handle_confirmation(self, value: bool) -> ValidationResult:
        # Get member data from dashboard
        dashboard = self.state_manager.get("dashboard")
        member_id = dashboard.get("member", {}).get("memberID")

        # Get confirmation data from flow
        flow_data = self.state_manager.get_flow_state()
        confirm_data = flow_data.get("data", {})

        # Validate and update state...
        return ValidationResult.success({
            "confirmed": value,
            "member_id": member_id,
            "data": confirm_data
        })
```

Common mistakes to avoid:
1. DON'T mix component responsibilities
   - Display components shouldn't modify state
   - Input components shouldn't read unrelated state
   - API components shouldn't format for display
   - Confirm components shouldn't make API calls

2. DON'T bypass component boundaries
   - Use proper base component
   - Implement required methods
   - Follow component patterns
   - Maintain clear responsibilities

3. DON'T duplicate state access
   - Use base component methods
   - Follow standard patterns
   - Maintain single source of truth
   - Keep state access focused

4. DON'T lose validation context
   - Track all attempts
   - Include error details
   - Maintain validation state
   - Follow validation patterns

## Architecture Rules

Key principles that must be followed:

1. **State Manager is Single Source of Truth**
   - All state access through manager
   - No direct state modification
   - No state duplication

2. **Proper State Validation**
   - All updates validated
   - No invalid state
   - No validation bypass

3. **Atomic State Updates**
   - Use atomic operations
   - Handle rollbacks properly
   - Maintain consistency

4. **Clear State Boundaries**
   - State properly isolated
   - No mixed responsibilities
   - No cross-boundary access

5. **Secure State Handling**
   - Credentials properly managed
   - No sensitive data exposure
   - No security bypass

Common mistakes to avoid:
1. DON'T access state directly
2. DON'T bypass validation
3. DON'T break atomicity
4. DON'T mix state responsibilities

## State Operations

### 1. State Access
```python
# CORRECT - Use proper accessor methods
channel_id = state_manager.get_channel_id()
member_id = state_manager.get_member_id()

# WRONG - Direct state access
channel = state_manager.get("channel")  # Don't access directly!
member_id = state_manager.get("member_id")  # Don't access directly!
```

### 2. State Updates
```python
# CORRECT - Update with validation tracking
state_manager.update_state({
    "flow_data": {
        "context": context,
        "component": component,
        "data": data,
        "validation": {
            "in_progress": True,
            "attempts": current + 1,
            "last_attempt": datetime.utcnow()
        }
    }
})

# WRONG - Update without validation
state_manager.update_state({
    "value": new_value  # Don't update without validation!
})
```

### 3. Error Handling
```python
# CORRECT - Use ErrorHandler
try:
    result = state_manager.atomic_state.atomic_get(key)
except Exception as e:
    error_context = ErrorContext(
        error_type="system",
        message=str(e),
        details={
            "code": "STATE_GET_ERROR",
            "service": "state_manager",
            "action": "get"
        }
    )
    ErrorHandler.handle_error(e, state_manager, error_context)

# WRONG - Handle errors directly
try:
    result = redis_client.get(key)  # Don't access directly!
except Exception as e:
    logger.error(str(e))  # Don't handle directly!
```

### 4. Atomic Operations
```python
# CORRECT - Use atomic operations
success, data, error = atomic_state.execute_atomic(
    key=key,
    operation='set',
    value=value,
    ttl=300
)

# WRONG - Direct Redis operations
redis_client.set(key, value)  # Don't use Redis directly!
```

## State Recovery

1. **Initialization**
- Check existing state
- Create initial state if needed
- Preserve channel info
- Track initialization

2. **Error Recovery**
- Handle operation failures
- Maintain validation state
- Track error context
- Follow recovery patterns

3. **State Cleanup**
- Clear flow state
- Preserve core state
- Track cleanup
- Handle errors

Common mistakes to avoid:
1. DON'T access state directly
2. DON'T update without validation
3. DON'T bypass atomicity
4. DON'T lose state history
