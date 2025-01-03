# State Management

## Core Principles

1. **Single Source of Truth**
- Member ID at top level
- Channel info at top level
- JWT token in state
- NO duplication
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

```python
{
    # Core identity (SINGLE SOURCE OF TRUTH)
    "member_id": str,
    "channel": {
        "type": str,      # whatsapp, etc
        "identifier": str # channel-specific id
    },
    "jwt_token": str,

    # Flow state
    "flow_data": {
        # Flow identification
        "flow_type": str,        # registration, upgrade, ledger, offer, accept
        "handler_type": str,     # member, account, credex
        "step": str,            # current step id
        "step_index": int,      # current step index
        "total_steps": int,     # total steps in flow

        # Flow metadata
        "started_at": str,      # ISO timestamp
        "action_type": str,     # For action flows

        # Component state
        "active_component": {
            "type": str,        # component type
            "value": Any,       # current value
            "validation": {     # validation state
                "in_progress": bool,
                "error": Optional[Dict],
                "attempts": int,
                "last_attempt": Any
            }
        },

        # Business data
        "data": Dict           # Flow-specific data
    }
}
```

## Implementation

### 1. State Manager
```python
class StateManager:
    """Manages state updates and validation"""

    def update_state(self, updates: Dict) -> None:
        """Update state with validation"""
        # Validate updates
        validation = StateValidator.validate_updates(self._state, updates)
        if not validation.is_valid:
            raise StateError(validation.error_message)

        # Apply updates
        self._state.update(updates)

        # Store state
        self._store_state()

    def get_flow_state(self) -> Dict:
        """Get flow state with validation"""
        flow_data = self._state.get("flow_data", {})
        if flow_data:
            validation = StateValidator.validate_flow_state(flow_data)
            if not validation.is_valid:
                raise StateError(validation.error_message)
        return flow_data
```

### 2. State Validation
```python
class StateValidator:
    """Validates state updates"""

    # Flow validation rules
    FLOW_RULES = {
        # Required fields in flow_data
        "required_fields": {
            "flow_type": str,
            "handler_type": str,
            "step": str,
            "step_index": int,
            "total_steps": int
        },

        # Required fields in active_component
        "component_fields": {
            "type": str,
            "validation": {
                "in_progress": bool,
                "error": (type(None), dict),
                "attempts": int,
                "last_attempt": (type(None), str, int, float, bool, dict, list)
            }
        },

        # Valid handler types
        "handler_types": {"member", "account", "credex"}
    }

    @classmethod
    def validate_flow_state(cls, flow_data: Dict) -> ValidationResult:
        """Validate flow state structure"""
        # Validate required fields
        for field, field_type in cls.FLOW_RULES["required_fields"].items():
            if field not in flow_data:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing required field: {field}"
                )

        # Validate component state
        component = flow_data.get("active_component")
        if component:
            for field, field_type in cls.FLOW_RULES["component_fields"].items():
                if field not in component:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Missing component field: {field}"
                    )

        return ValidationResult(is_valid=True)
```

### 3. State Usage
```python
# Initialize flow with metadata
initialize_flow(
    state_manager=state_manager,
    flow_type="credex_accept",
    initial_data={
        "started_at": datetime.utcnow().isoformat(),
        "action_type": "accept"
    }
)

# Update component state with tracking
state_manager.update_state({
    "flow_data": {
        "active_component": {
            "type": "SelectInput",
            "value": "123",
            "validation": {
                "in_progress": False,
                "error": None,
                "attempts": 1,
                "last_attempt": "123"
            }
        }
    }
})

# Update progress
state_manager.update_state({
    "flow_data": {
        "step_index": current_index + 1,
        "step": next_step
    }
})
```

## Best Practices

1. **State Updates**
- Use StateManager
- Validate updates
- Track progress
- Track validation
- NO manual updates
- NO transformation

2. **State Access**
- Use getter methods
- Check existence
- Validate state
- NO direct access
- NO assumptions
- NO default values

3. **Flow State**
- Clear boundaries
- Standard structure
- Track progress
- Track validation
- NO mixed concerns
- NO manual handling

4. **Error Handling**
- Use ErrorHandler
- Clear boundaries
- Track attempts
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

For more details on:
- Flow Framework: [Flow Framework](flow-framework.md)
- Components: [Components](components.md)
- Error Handling: [Error Handling](error-handling.md)
