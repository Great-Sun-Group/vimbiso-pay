# State Management

## Overview

VimbisoPay implements a Redis-based state management system to handle WhatsApp conversations and user sessions. The system provides:
- User context and conversation state persistence
- Session management with 5-minute timeouts
- JWT token management for API authentication
- Conversation flow control

## Core Components

### 1. CachedUser
Represents a user in the system:
```python
class CachedUser:
    def __init__(self, mobile_number):
        self.first_name = "Welcome"
        self.last_name = "Visitor"
        self.mobile_number = mobile_number
        self.registration_complete = False
        self.state = CachedUserState(self)
        self.jwt_token = self.state.jwt_token
```

### 2. CachedUserState
Manages user state in Redis:
```python
class CachedUserState:
    def __init__(self, user):
        self.direction = cache.get(f"{user.mobile_number}_direction", "OUT")
        self.stage = cache.get(f"{user.mobile_number}_stage", "handle_action_menu")
        self.option = cache.get(f"{user.mobile_number}_option")
        self.state = cache.get(f"{user.mobile_number}", {})
        self.jwt_token = cache.get(f"{user.mobile_number}_jwt_token")
```

### 3. StateManager
Handles state transitions and updates:
```python
class StateManager:
    def update_state(self, new_state, stage, update_from, option):
        self.user.state.update_state(
            state=new_state,
            stage=stage,
            update_from=update_from,
            option=option
        )
```

## Redis Cache Structure

### Keys and Values
```python
{
    "{mobile_number}": {
        # Main state object
        "profile": {},
        "current_account": {},
        "page_number": 0
    },
    "{mobile_number}_stage": "current_conversation_stage",
    "{mobile_number}_option": "selected_option",
    "{mobile_number}_direction": "message_direction",
    "{mobile_number}_jwt_token": "auth_token"
}
```

### Timeouts
- All keys expire after 5 minutes (300 seconds)
- JWT tokens are refreshed on expiry
- State is cleared on session timeout

## State Flow

### 1. Initialization
```python
# New user connection
state = {
    "stage": "handle_action_menu",
    "option": None,
    "direction": "OUT",
    "state": {}
}
```

### 2. Registration Flow
```python
# After successful registration
state = {
    "stage": "handle_action_register",
    "option": "handle_action_register",
    "state": {
        "profile": {
            "member": {
                "memberID": "uuid",
                "firstname": "string",
                "lastname": "string"
            }
        }
    }
}
```

### 3. Menu Navigation
```python
# Main menu state
state = {
    "stage": "handle_action_menu",
    "option": "handle_action_menu",
    "state": {
        "current_account": {
            "accountID": "string",
            "accountName": "string",
            "balanceData": {}
        }
    }
}
```

## State Management Functions

### 1. State Updates
```python
def update_state(self, state, update_from, stage=None, option=None):
    # Set main state with 5-minute timeout
    cache.set(f"{mobile_number}", state, timeout=60 * 5)

    # Update stage if provided
    if stage:
        cache.set(f"{mobile_number}_stage", stage, timeout=60 * 5)

    # Update option if provided
    if option:
        cache.set(f"{mobile_number}_option", option, timeout=60 * 5)
```

### 2. State Reset
```python
def reset_state(self):
    # Clear all state
    cache.set(f"{mobile_number}_stage", "handle_action_menu")
    cache.delete(f"{mobile_number}_option")
    cache.set(f"{mobile_number}", {}, timeout=60 * 5)
```

### 3. Token Management
```python
def set_jwt_token(self, jwt_token):
    cache.set(f"{mobile_number}_jwt_token", jwt_token, timeout=60 * 5)
```

## Menu Options

The system supports two levels of menu options:

### Basic Menu (Tier 1)
```python
MENU_OPTIONS_1 = {
    "1": "handle_action_offer_credex",
    "2": "handle_action_pending_offers_in",
    "3": "handle_action_pending_offers_out",
    "4": "handle_action_transactions",
    "5": "handle_action_switch_account"
}
```

### Advanced Menu (Tier 2)
```python
MENU_OPTIONS_2 = {
    # Includes all Tier 1 options plus:
    "5": "handle_action_authorize_member",
    "6": "handle_action_notifications",
    "7": "handle_action_switch_account"
}
```

## Error Handling

### 1. Session Expiry
- State is automatically cleared after 5 minutes
- Users are prompted to restart conversation
- JWT tokens are refreshed on expiry

### 2. State Validation
- Stage transitions are validated
- Options are checked against valid menu items
- State structure is verified before updates

### 3. Recovery
- Invalid states trigger reset to menu
- Failed operations maintain previous state
- Automatic retry on token expiry

## Logging

The system implements comprehensive logging:
```python
logger.info(f"Updating state: stage={stage}, update_from={update_from}")
logger.info("Resetting state")
logger.info(f"Setting current stage to: {stage}")
```

## Security Considerations

1. **Session Management**
   - 5-minute timeouts
   - Secure token storage
   - State isolation per user

2. **Data Protection**
   - No sensitive data in state
   - JWT tokens for API auth
   - Redis security configuration

3. **Input Validation**
   - Stage transition validation
   - Option validation
   - State structure verification
