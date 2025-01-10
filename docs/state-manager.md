# State Management

The state manager provides the data foundation for the central flow management system:

```
core
  ├── flow/headquarters.py     <-- Flow Management
  ├──components/              <-- Component Management
         ↓
  ├── state/                    <-- State Management
      ├── manager.py              <-- High-level Interface
      ├── atomic_manager.py       <-- Transaction Handling
      └── persistence/            <-- Storage Layer
          ├── redis_operations.py   <-- Atomic Operations
          └── redis_client.py       <-- Connection Management
```

### Implementation Layers
1. **StateManager** (manager.py)
   - High-level interface through get_state_value()
   - Schema validation for all fields except component_data.data
   - Component state coordination

2. **AtomicStateManager** (atomic_manager.py)
   - Transaction handling
   - Redis interface
   - Operation tracking (in memory only)

3. **Redis Layer** (persistence/)
   - Atomic operations (redis_operations.py)
   - Connection management (redis_client.py)
   - Retry and durability handling

## Core Principles

1. **Schema-Based Validation**
- All state fields protected by schema validation
- Only component_data.data is unvalidated
- Components have freedom in their data dict
- Protection through validation, not access control

2. **State Access Pattern**
- All state access through get_state_value():
  * Channel info: get_state_value("channel")
  * Dashboard data: get_state_value("dashboard")
  * Action data: get_state_value("action")
  * Component data: get_state_value("component_data")
- Messaging service accessed through state_manager.messaging
- NO direct state access or get_component_data()

3. **State Persistence**
- Redis as persistent storage
- Atomic operations for consistency
- Transaction handling for safety
- NO direct Redis access
- NO debug state persistence (validation, metadata)

4. **Component Responsibilities**
- Schema validation protects core state structure
- Components validate their specific needs:
  * Display components -> Validate display requirements
  * Input components -> Validate user input
  * API components -> Validate API operations
  * Confirm components -> Validate user confirmations
- Components handle their operations:
  * API calls through make_api_request
  * Message sending through state_manager.messaging
  * Error handling through ErrorHandler
  * Free to store any data in component_data.data

## State Structure

```python
# Core State Structure (all fields schema-validated except component_data.data)
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
        "component_result": str,  # Optional flow branching (schema-validated)
        "awaiting_input": bool,   # Optional input state (schema-validated)
        "data": dict,        # Component-specific data (unvalidated)
    },
}

# Operation Tracking (in memory only)
{
    "attempts": {},      # Track attempts per key
    "last_attempts": {}, # Track last attempt timestamps
    "errors": {}        # Track errors per key
}
```

### State Access and Updates

1. **Schema Validation**
   - All state fields protected by schema validation
   - Only component_data.data is unvalidated
   - Components validate their own data needs
   - Schema defines required fields and types

2. **Component State**
   - Access: get_state_value("component_data")
   - Components free to store any data in data dict
   - Updates: Components update own data, headquarters manages flow
   - Default empty dict prevents None access

3. **Operation Tracking**
   - Handled by AtomicStateManager
   - Kept in memory only
   - Used for debugging/monitoring

## Code Organization

The state management code is organized in layers:

1. **Flow Layer** (headquarters.py)
   - Manages application flows
   - Uses state manager for data
   - Makes branching decisions

2. **State Layer** (manager.py, atomic_manager.py)
   - Manages state structure
   - Coordinates with Redis layer
   - Operation tracking in AtomicStateManager

3. **Storage Layer** (persistence/)
   - Handles Redis operations
   - Manages connections
   - Ensures data durability

Each layer has clear responsibilities and boundaries. Start with flow/manager.py to understand the core concepts, then explore other layers as needed.

## Mistakes to avoid:
1. DON'T bypass headquarters.py for flow control
2. DON'T access state directly - use get_state_value()
3. DON'T break component boundaries
4. DON'T mix state responsibilities
5. DON'T persist debug state (validation, metadata)
6. DON'T validate component_data.data in state validator
7. DON'T use get_component_data() - removed in favor of get_state_value()
