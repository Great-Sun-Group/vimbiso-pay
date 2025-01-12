# Vimbiso ChatServer Architecture

The Vimbiso ChatServer enables members to manage their credex ecosystem data through secure messaging channels, with all API calls requiring explicit member authorization through digital signatures.

## Core Architecture

```
core/flow/headquarters.py  <-- Central Flow Management
 ├── state/manager.py      <-- State Management
 ├── components/           <-- Component System
 ├── api/                  <-- API Integration
 └── messaging/            <-- Messaging System
```

### Message Flow Pattern

The system follows a specific message flow pattern:

1. **Message Initialization**
- Incoming messages flow through headquarters.py
- Headquarters initializes state (on greetings) and component context
- Messages processed through components in controlled flow

2. **Component Message Control**
- Components use stateless message sending while maintaining state
- Set awaiting_input flag to pause for user response
- Process responses while awaiting input
- Release flag after processing to allow flow progression
- Return optional component_result for flow control

3. **Flow Control**
- Headquarters manages flow transitions
- Flow advances only after awaiting_input flag releases (if used by component)
- Clear handoff between components
- Can branch path logic and next component initialized based on component_result
- Proper state management throughout

### State Management

The state manager provides:

1. **Full State Structure**
```python
# Core State Structure (all fields schema-validated except component_data.data which enables inter-component data sharing)
{
    "channel": {              # Channel info
        "type": str,         # Channel type (e.g., "whatsapp")
        "identifier": str    # Channel ID
    },
    "mock_testing": bool,     # Flag for mock testing mode
    "auth": {                # Auth state
        "token": str         # JWT token
    },
    "dashboard": {           # Dashboard state (API-sourced)
        "member": {          # Member info
            "memberID": str,
            "memberTier": int,
            "firstname": str,
            "lastname": str,
            "memberHandle": str,
            "defaultDenom": str,
            # Optional fields
            "remainingAvailableUSD": float
        },
        "accounts": [        # Account list
            {
                "accountID": str,
                "accountName": str,
                "accountHandle": str,
                "accountType": str,
                "defaultDenom": str,
                "isOwnedAccount": bool,
                # Additional account data...
            }
        ]
    },
    "action": {              # Action state (API-sourced)
        "id": str,
        "type": str,
        "timestamp": str,
        "actor": str,
        "details": dict
    },
    "active_account_id": str, # Currently selected account
    "component_data": {      # Flow state
        "path": str,         # Current flow path (schema-validated)
        "component": str,    # Current component (schema-validated)
        "component_result": str | None,  # Optional flow branching (schema-validated)
        "awaiting_input": bool,   # Input state flag (schema-validated)
        "data": dict,        # Shared data between components (unvalidated to enable flexible data sharing)
        "incoming_message": {  # Message passed to component
            "content": {
                "type": str,  # Message type
                "text": dict  # Message content (varies by type)
            }
        }
    },
}

# Operation Tracking (in memory only)
{
    "attempts": {},      # Track attempts per key
    "last_attempts": {}, # Track last attempt timestamps
    "errors": {}        # Track errors per key
}
```

2. **State Access Patterns**
- All state access through get_state_value()
- Schema validation for all fields except component_data.data
- Components share data through component_data.data
- Data persists until successfully consumed (e.g. by API call)

## Component System

Components are self-contained units with clear responsibilities:

### Display Components
- Format and present data
- Send messages while maintaining state
- don't use awaiting_input

### Input Components
- Set awaiting_input flag
- Send message requesting input
- Validate user input
- Store validated data in component_data.data for use by subsequent components
- Release flag after valid input processed

Example: Multi-step Registration Flow
```python
# FirstNameInput stores in component_data.data
{"firstname": "John"}

# LastNameInput adds to existing data
{"firstname": "John", "lastname": "Doe"}

# OnBoardMemberApiCall consumes the collected data
# Clears component_data.data after successful API call
```

### API Components
- Make external API calls
- Handle response processing
- Consume data collected by previous components
- Clear component_data.data after successful operation
- Inject fresh dashboard and action data into state using api_response.py
- Use injected action data for flow control
- Pass results with component_result

### Confirm Components
- Validate member intent and handle member authorizations
- Confirmation is considered a digital signature
- Maintain audit trail
- Not all flows require confirmation components (eg accept_credex), where the prior button click is considered the signature.

## Implementation Guidelines

1. **Flow Control**
- Components set awaiting_input before sending messages that need response
- Process responses while awaiting input
- Release flag after processing
- Let headquarters manage transitions

2. **State Management**
- Access state through get_state_value()
- Follow schema validation
- Use component_data.data for sharing between components
- Clear shared data after successful consumption
- Handle errors through ErrorHandler

3. **Message Sending**
- Use stateless message sending
- Maintain component state
- Handle channel-specific formatting in services
- Follow standard validation patterns

4. **Messaging Domains**
- Components handle WHAT to send (content only)
- MessagingService handles WHO to send to (recipient injection from state)
- Channel services handle HOW to send it (channel-specific formatting)
- Clear separation prevents components from needing channel details

## Example Flow

```python
# In headquarters.py
match (path, component):
    # Login path
    case ("login", "Greeting"):
        return "login", "LoginApiCall"  # Check if user exists
    case ("login", "LoginApiCall"):
        if component_result == "send_dashboard":
            return "account", "AccountDashboard"  # Send account dashboard
        if component_result == "start_onboarding":
            return "onboard", "Welcome"  # Send first message in onboarding path
```

## Core Principles

1. **Member Control**
- All critical operations require digital signatures
- Clear audit trail through action section
- Secure operation confirmation
- Explicit member authorization

2. **Clear Boundaries**
- Components handle specific operations
- State protected by schema validation
- Flow controlled through path logic, awaiting_input, and component_result
- Inter-component data sharing through component_data.data
- Standard error handling patterns

3. **Validation Patterns**
- Schema validation at state level
- Component-specific validation
- Business validation in services and components
- Standard validation results

## Mistakes to Avoid

1. DON'T bypass headquarters.py - all flow goes through it
2. DON'T access state directly - use get_state_value()
3. DON'T validate component_data.data in schema (it needs flexibility for data sharing)
4. DON'T mix component responsibilities
5. DON'T store sensitive data in component data
6. DON'T clear component_data.data until it's successfully consumed
