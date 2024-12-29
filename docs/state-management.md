# State Management

## Overview

VimbisoPay uses a centralized state management system that strictly enforces SINGLE SOURCE OF TRUTH:
- Member ID exists ONLY at top level
- Channel info exists ONLY at top level
- JWT token exists ONLY in state
- Minimal metadata and nesting

## Core Principles

1. **SINGLE SOURCE OF TRUTH**
   - Member ID ONLY at top level
   - Channel info ONLY at top level
   - JWT token ONLY in state
   - NO duplication anywhere
   - NO state passing
   - NO state transformation

2. **Validation Through State**
   - ALL validation through state updates
   - NO manual validation
   - NO validation helpers
   - NO validation state
   - NO error recovery
   - NO state fixing

3. **Clear Responsibilities**
   - StateManager: Validates all updates
   - StateValidator: Defines valid structure
   - StateUtils: Provides core structure
   - NO mixed concerns
   - NO manual validation
   - NO error handling

4. **Simple Updates**
   - Update state to validate
   - Let StateManager validate
   - NO manual validation
   - NO cleanup code
   - NO error recovery
   - NO state fixing

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
    "authenticated": True,

    # Account state (SINGLE SOURCE OF TRUTH)
    "accounts": [  # All available accounts
        {
            "accountID": "account_id",
            "accountName": "Account Name",
            "accountHandle": "@handle",
            "accountType": "PERSONAL",  # or other types
            "balances": {...},
            "offerData": {...}
        }
    ],
    "active_account_id": "current_account_id",  # Currently active account

    # Flow state
    "flow_data": {
        # Framework-level step tracking (required for validation)
        "step": 0,  # Integer for progression tracking

        # Flow-specific routing
        "current_step": "amount",  # String for step identification

        # Flow type identifier
        "flow_type": "flow_type"
    }
}
```

### Account State Rules

1. **Registration**
- Creates single personal account
- Sets as active account
- Stores in accounts array
- NO manual account access

2. **Login**
- May return multiple accounts
- Sets personal account as active
- Stores all accounts
- NO manual account access

3. **Account Access**
- Use active_account_id to find current account
- Get accounts from top level state
- Let StateManager validate account existence
- NO manual account validation

Note: This is the COMPLETE structure. If you need more fields, question why.

## Implementation

### 1. State Utils
```python
def create_initial_state() -> Dict[str, Any]:
    """Create minimal initial state"""
    return {
        "member_id": None,  # ONLY at top level
        "channel": {        # ONLY at top level
            "type": "whatsapp",
            "identifier": None
        },
        "jwt_token": None,  # ONLY in state
        "flow_data": None   # NO validation state
    }

def prepare_state_update(state_manager: Any, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update state through StateManager validation

    Args:
        state_manager: State manager instance
        updates: State updates to validate

    Returns:
        Validated state data

    Raises:
        StateException: If validation fails
    """
    # Let StateManager validate updates
    state_manager.update_state(updates)

    # Get validated state
    return state_manager.get("flow_data")
```

### 2. State Manager
```python
class StateManager:
    """Manages state while enforcing SINGLE SOURCE OF TRUTH"""

    def __init__(self, key_prefix: str):
        """Initialize state manager

        Args:
            key_prefix: Redis key prefix

        Raises:
            StateException: If initialization fails
        """
        self.key_prefix = key_prefix
        self._initialize_state()  # Raises StateException if invalid

    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update state through validation

        Args:
            updates: State updates to validate

        Raises:
            StateException: If validation fails
        """
        # Let StateValidator validate updates
        StateValidator.validate_state(updates)

        # Store validated state (raises StateException if fails)
        success, error = atomic_state.atomic_update(
            self.key_prefix,
            updates,
            ACTIVITY_TTL
        )
        if not success:
            raise StateException(f"Failed to update state: {error}")
```

### 3. State Validator
```python
class StateValidator:
    """Validates state through updates"""

    @classmethod
    def validate_state(cls, updates: Dict[str, Any]) -> None:
        """Validate state through update structure

        Args:
            updates: State updates to validate

        Raises:
            StateException: If validation fails
        """
        # Validate member_id at top level
        if "member_id" in updates and not isinstance(updates["member_id"], (str, type(None))):
            raise StateException("member_id must be string or None")

        # Validate channel at top level
        if "channel" in updates:
            if not isinstance(updates["channel"], dict):
                raise StateException("channel must be dictionary")
            if "type" not in updates["channel"]:
                raise StateException("channel missing type")
            if "identifier" not in updates["channel"]:
                raise StateException("channel missing identifier")

        # Validate jwt_token in state
        if "jwt_token" in updates and not isinstance(updates["jwt_token"], (str, type(None))):
            raise StateException("jwt_token must be string or None")

        # Validate flow_data structure
        if "flow_data" in updates and not isinstance(updates["flow_data"], (dict, type(None))):
            raise StateException("flow_data must be dictionary or None")
```

## Best Practices

1. **State Access**
   - Member ID ONLY at top level
   - Channel info ONLY at top level
   - JWT token ONLY in state
   - NO state duplication
   - NO state passing
   - NO state transformation

2. **State Updates**
   - Let StateManager validate
   - NO manual validation
   - NO state duplication
   - NO error recovery
   - NO state fixing
   - NO cleanup code

3. **Flow Integration**
   - Access through StateManager
   - NO validation state
   - NO state duplication
   - NO state passing
   - NO state transformation
   - NO error recovery

4. **Error Handling**
   - Let StateManager validate
   - NO manual validation
   - NO error recovery
   - NO state fixing
   - NO cleanup code
   - Clear error messages

For more details on:
- Service architecture: [Service Architecture](service-architecture.md)
- Flow framework: [Flow Framework](flow-framework.md)
- API integration: [API Integration](api-integration.md)
