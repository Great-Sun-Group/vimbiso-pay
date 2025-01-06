# State Management

## Code Reading Guide
Before modifying state management, read these files in order:

1. core/config/state_manager.py - Understand central state management
   - Learn state access patterns
   - Understand state updates
   - Review state validation

2. core/utils/state_validator.py - Learn validation rules
   - Understand state validation
   - Learn validation patterns
   - Review validation rules

3. core/messaging/base.py - Understand state usage
   - Learn state integration
   - Understand state flow
   - Review state patterns

4. core/config/atomic_state.py - Learn atomic operations
   - Understand state atomicity
   - Learn transaction patterns
   - Review rollback handling

Common mistakes to avoid:
1. DON'T modify state without understanding validation
2. DON'T bypass state manager for direct access
3. DON'T mix state responsibilities
4. DON'T duplicate state across components

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

## Integration Points

The state system has specific integration points with other systems:

### Flow Integration
- Flow state managed centrally
- Flow progression updates state
- Flow validation through state
- Flow errors update state

### Component Integration
- Components access state properly
- Component validation through state
- Component state properly tracked
- State updates validated

### Error Integration
- Error state properly tracked
- Error history maintained
- Validation state updated
- Error context preserved

### Message Integration
- Message state properly tracked
- Message history maintained
- State updates validated
- Context preserved

### API Integration
- API state properly managed
- Credentials handled securely
- State updates atomic
- Context maintained

Common mistakes to avoid:
1. DON'T bypass state integration points
2. DON'T create new state paths
3. DON'T mix state responsibilities
4. DON'T lose state context

## Common Modifications

### Adding New State Types
1. Check state_manager.py for patterns
2. Add state structure
3. Update validation rules
4. Add access methods
5. Test state handling

Example:
```python
def add_new_state(self, new_state: Dict[str, Any]) -> None:
    """Add new state with validation"""
    # Validate new state
    if not self.validate_new_state(new_state):
        raise ValidationError("Invalid new state")

    # Update with atomic operation
    with self.atomic_update():
        self.state.update({
            "new_state": {
                "data": new_state,
                "timestamp": datetime.utcnow().isoformat(),
                "validation": {
                    "valid": True,
                    "last_check": datetime.utcnow().isoformat()
                }
            }
        })
```

### Modifying State Access
1. Check existing access patterns
2. Update access methods
3. Maintain validation
4. Test state access

### Adding State Validation
1. Check validation rules
2. Add validation logic
3. Update state handling
4. Test validation

Common mistakes to avoid:
1. DON'T create new patterns when existing ones exist
2. DON'T bypass state manager
3. DON'T mix validation responsibilities
4. DON'T duplicate validation logic

## Architecture Rules

Key principles that must be followed:

1. State Manager is Single Source of Truth
   - All state access through manager
   - No direct state modification
   - No state duplication

2. Proper State Validation
   - All updates validated
   - No invalid state
   - No validation bypass

3. Atomic State Updates
   - Use atomic operations
   - Handle rollbacks properly
   - Maintain consistency

4. Clear State Boundaries
   - State properly isolated
   - No mixed responsibilities
   - No cross-boundary access

5. Secure State Handling
   - Credentials properly managed
   - No sensitive data exposure
   - No security bypass

Common mistakes to avoid:
1. DON'T access state directly
2. DON'T bypass validation
3. DON'T break atomicity
4. DON'T mix state responsibilities

## State Management

### State Access
- Use proper accessor methods
- Validate all access
- Track access patterns

### State Updates
- Use atomic operations
- Include validation
- Track all updates

### Validation State
- Track all validation
- Include timestamps
- Maintain context

### State History
- Track state changes
- Maintain timestamps
- Record context

Common mistakes to avoid:
1. DON'T access state directly
2. DON'T update without validation
3. DON'T bypass atomicity
4. DON'T lose state history
