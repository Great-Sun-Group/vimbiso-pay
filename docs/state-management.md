# State Management

## Core Principles

1. **Single Source of Truth**
- Member ID accessed through get_member_id()
- Channel info accessed through get_channel_id()
- JWT token accessed through flow_data auth
- NO direct state access
- NO state passing
- NO transformation

2. **Simple Structure**
- Common configurations
- Clear boundaries
- Standard validation
- Flow metadata
- NO complex hierarchies
- NO redundant wrapping

3. **Pure Functions**
- Stateless operations
- Clear validation
- Standard updates
- NO stored state
- NO side effects
- NO manual handling

4. **Central Management**
- Single state manager
- Standard validation
- Clear boundaries
- Progress tracking
- NO manual updates
- NO local state

## State Structure

### 1. Core Identity
```python
{
    # Accessed through proper methods
    "member_id": str,     # Use get_member_id()
    "channel": {          # Use get_channel_id()
        "type": str,      # Use get_channel_type()
        "identifier": str
    },
    "jwt_token": str     # Accessed through flow_data auth
}
```

### 2. Flow State
```python
{
    "flow_data": {
        # Flow identification
        "flow_type": str,     # Type of flow
        "handler_type": str,  # Handler responsible
        "step": str,         # Current step
        "step_index": int,   # Current position
        "total_steps": int,  # Total steps

        # Validation tracking
        "active_component": {
            "type": str,     # Component type
            "validation": {
                "in_progress": bool,
                "error": Optional[Dict],
                "attempts": int,
                "last_attempt": Any
            }
        }
    }
}
```

## Access Patterns

### 1. State Access
```python
# CORRECT - Use proper accessor methods
channel_id = state_manager.get_channel_id()
member_id = state_manager.get_member_id()

# WRONG - Direct state access
channel = state_manager.get("channel")  # Don't access directly!
member_id = state_manager.get("member_id")  # Don't access directly!
```

### 2. Validation Updates
```python
# CORRECT - Update with validation tracking
state_manager.update_state({
    "flow_data": {
        "active_component": {
            "type": "input",
            "validation": {
                "in_progress": True,
                "attempts": current + 1,
                "last_attempt": datetime.utcnow()
            }
        }
    }
})

# WRONG - Update without tracking
state_manager.update_state({
    "value": new_value  # Don't update without validation!
})
```

## Best Practices

1. **State Access**
- Use proper accessor methods
- Validate through updates
- Track all attempts
- NO direct access
- NO assumptions
- NO default values

2. **State Updates**
- Include validation tracking
- Track all attempts
- Include error context
- NO manual updates
- NO transformation
- NO state fixing

3. **Flow State**
- Clear boundaries
- Standard structure
- Track progress
- Track validation
- NO mixed concerns
- NO manual handling

4. **Error Handling**
- Update state with errors
- Track validation failures
- Include error context
- NO manual handling
- NO local recovery
- NO state fixing

## Integration

The state system integrates with:
- Flow framework
- Component system
- Error handling
- Message handling
- API services
