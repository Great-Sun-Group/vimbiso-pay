# State Management

## Overview

VimbisoPay uses a simplified state management system that strictly enforces SINGLE SOURCE OF TRUTH:
- Member ID exists ONLY at top level
- Channel info exists ONLY at top level
- JWT token exists ONLY in state
- Minimal metadata and nesting

## Core Principles

1. **True SINGLE SOURCE OF TRUTH**
   - member_id ONLY at top level
   - channel info ONLY at top level
   - jwt_token ONLY in state
   - No duplication anywhere

2. **Minimal State Structure**
   - Only essential fields
   - No nested validation state
   - No previous state tracking
   - No redundant metadata

3. **Clear Responsibilities**
   - StateManager: Manages state operations
   - StateValidator: Validates structure
   - StateUtils: Defines core structure
   - No mixed concerns

4. **Simple Updates**
   - Direct state updates
   - Clear update paths
   - Minimal validation
   - No cleanup code

## State Structure

Core state includes:
```python
{
    # Core identity (SINGLE SOURCE OF TRUTH)
    "member_id": "unique_member_id",

    # Channel information (SINGLE SOURCE OF TRUTH)
    "channel": {
        "type": "whatsapp",
        "identifier": "channel_id"
    },

    # Authentication (SINGLE SOURCE OF TRUTH)
    "jwt_token": "token",

    # Flow state
    "flow_data": {
        "step": 0,
        "flow_type": "flow_type"
    }
}
```

Note: This is the COMPLETE structure. If you need more fields, question why.

## Implementation

### 1. State Utils
```python
def create_initial_state() -> Dict[str, Any]:
    """Create minimal initial state"""
    return {
        "member_id": None,
        "channel": {
            "type": "whatsapp",
            "identifier": None
        },
        "jwt_token": None,
        "flow_data": None
    }

def prepare_state_update(current_state: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update state preserving SINGLE SOURCE OF TRUTH"""
    new_state = current_state.copy()

    # Handle critical fields
    if "member_id" in updates:
        new_state["member_id"] = updates["member_id"]

    if "channel" in updates:
        if not isinstance(updates["channel"], dict):
            raise ValueError("Channel must be a dictionary")
        if "channel" not in new_state:
            new_state["channel"] = {"type": "whatsapp", "identifier": None}
        for field in ["type", "identifier"]:
            if field in updates["channel"]:
                new_state["channel"][field] = updates["channel"][field]

    # Handle jwt_token
    if "jwt_token" in updates:
        new_state["jwt_token"] = updates["jwt_token"]

    # Handle other updates
    for field, value in updates.items():
        if field not in ["member_id", "channel", "jwt_token"]:
            new_state[field] = value

    return new_state
```

### 2. State Manager
```python
class StateManager:
    """Manages state while enforcing SINGLE SOURCE OF TRUTH"""

    def __init__(self, key_prefix: str):
        self.key_prefix = key_prefix
        self.state = self._initialize_state()

    def update_state(self, updates: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Update state while maintaining SINGLE SOURCE OF TRUTH"""
        try:
            new_state = prepare_state_update(self.state, updates)
            success, error = atomic_state.atomic_update(
                self.key_prefix, new_state, ACTIVITY_TTL
            )
            if success:
                self.state = new_state
            return success, error
        except Exception as e:
            return False, str(e)
```

### 3. State Validator
```python
class StateValidator:
    """Validates core state structure"""

    @classmethod
    def validate_state(cls, state: Dict[str, Any]) -> ValidationResult:
        """Validate minimal state structure"""
        if not isinstance(state, dict):
            return ValidationResult(False, "State must be a dictionary")

        # Validate channel structure (required)
        if "channel" not in state or not isinstance(state["channel"], dict):
            return ValidationResult(False, "Channel info must be present")

        # Validate channel fields
        channel = state["channel"]
        for field in ["type", "identifier"]:
            if field not in channel:
                return ValidationResult(False, f"Channel missing {field}")
            if not isinstance(channel[field], (str, type(None))):
                return ValidationResult(False, f"Channel {field} must be string or None")

        # Validate flow_data if present
        if "flow_data" in state and not isinstance(state["flow_data"], (dict, type(None))):
            return ValidationResult(False, "Flow data must be dictionary or None")

        return ValidationResult(True)
```

## Best Practices

1. **State Access**
   - Always access member_id from top level
   - Always access channel info from top level
   - Always access jwt_token from state
   - Never duplicate these values

2. **State Updates**
   - Use StateManager for all updates
   - Validate before updating
   - Keep updates minimal
   - Follow update patterns

3. **Flow Integration**
   - Access state through StateManager
   - Keep flow state minimal
   - No validation state in flow_data
   - Clear state boundaries

4. **Error Handling**
   - Validate early
   - Clear error messages
   - Simple recovery
   - No cleanup code

For more details on:
- Service architecture: [Service Architecture](service-architecture.md)
- Flow framework: [Flow Framework](flow-framework.md)
- API integration: [API Integration](api-integration.md)
