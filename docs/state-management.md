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
- Minimal nesting
- Clear boundaries
- Standard validation
- NO complex hierarchies
- NO redundant wrapping
- NO state duplication

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
- NO manual updates
- NO local state
- NO mixed concerns

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

        # Component state
        "active_component": {
            "type": str,        # component type
            "value": Any,       # current value
            "validation": {     # validation state
                "in_progress": bool,
                "error": Optional[Dict]
            }
        },

        # Verified data by domain
        "data": {
            # Member data
            "firstname": str,    # Registration
            "lastname": str,     # Registration
            "confirmed": bool,   # Upgrade

            # Account data
            "period": str,      # Ledger period
            "transactions": List, # Transaction history

            # Credex data
            "amount": float,    # Offer amount
            "handle": str,      # Offer recipient
            "offer_id": str     # Selected offer
        }
    }
}
```

## Implementation

### 1. State Manager
```python
class StateManager:
    """Manages state updates and validation"""

    def __init__(self, key_prefix: str):
        self.key_prefix = key_prefix
        self._state = self._initialize()

    def update_state(self, updates: Dict) -> None:
        """Update state with validation"""
        # Validate updates
        if not self._validate_updates(updates):
            raise StateError("Invalid state update")

        # Apply updates
        self._state.update(updates)

        # Store state
        self._store_state()

    def get_state(self) -> Dict:
        """Get current state"""
        return self._state

    def get_flow_state(self) -> Dict:
        """Get flow state section"""
        return self._state.get("flow_data", {})

    def clear_flow_state(self) -> None:
        """Clear flow state"""
        self.update_state({
            "flow_data": None
        })
```

### 2. State Validation
```python
class StateValidator:
    """Validates state updates"""

    @classmethod
    def validate_updates(cls, current: Dict, updates: Dict) -> bool:
        """Validate state updates"""
        # Check core fields
        if not cls._validate_core_fields(current, updates):
            return False

        # Check flow state
        if "flow_data" in updates:
            if not cls._validate_flow_state(updates["flow_data"]):
                return False

        return True

    @classmethod
    def _validate_core_fields(cls, current: Dict, updates: Dict) -> bool:
        """Validate core field updates"""
        core_fields = ["member_id", "channel", "jwt_token"]

        for field in core_fields:
            if (
                field in updates and
                field in current and
                updates[field] != current[field]
            ):
                return False

        return True

    @classmethod
    def _validate_flow_state(cls, flow_data: Dict) -> bool:
        """Validate flow state structure"""
        if flow_data is None:
            return True

        # Validate required fields
        required = ["flow_type", "handler_type", "step", "step_index"]
        if not all(field in flow_data for field in required):
            return False

        # Validate handler type
        if flow_data["handler_type"] not in ["member", "account", "credex"]:
            return False

        # Validate component state if present
        if "active_component" in flow_data:
            component = flow_data["active_component"]
            if not all(field in component for field in ["type", "validation"]):
                return False

        return True
```

### 3. State Usage
```python
# Initialize state
state_manager = StateManager("channel:123")

# Update flow state with handler type
state_manager.update_state({
    "flow_data": {
        "flow_type": "registration",
        "handler_type": "member",
        "step": "firstname",
        "step_index": 0,
        "active_component": {
            "type": "TextInput",
            "validation": {"in_progress": False}
        }
    }
})

# Get flow state and route to handler
flow_state = state_manager.get_flow_state()
handler_type = flow_state["handler_type"]

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

# Clear flow state when complete
state_manager.clear_flow_state()
```

## Best Practices

1. **State Updates**
- Use StateManager
- Validate updates
- Clear structure
- NO manual updates
- NO state duplication
- NO transformation

2. **State Access**
- Use getter methods
- Check existence
- Handle missing data
- NO direct access
- NO assumptions
- NO default values

3. **Flow State**
- Clear boundaries
- Standard structure
- Minimal nesting
- NO mixed concerns
- NO redundant data
- NO manual handling

4. **Error Handling**
- Use ErrorHandler
- Clear boundaries
- Standard formats
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
