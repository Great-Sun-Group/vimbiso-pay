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
   - High-level interface and validation
   - Protected state management
   - Component state coordination

2. **AtomicStateManager** (atomic_manager.py)
   - Transaction handling
   - Validation tracking
   - Redis interface

3. **Redis Layer** (persistence/)
   - Atomic operations (redis_operations.py)
   - Connection management (redis_client.py)
   - Retry and durability handling

## Core Principles

1. **Flow State Management**
- headquarters.py manages flow through state
- Components update state with results
- Flow decisions based on state
- Clear state boundaries
- Standard validation

2. **Single Source of Truth**
- Protected state accessed through dedicated methods:
  * Channel info: `get_channel_id()`, `get_channel_type()`
  * Dashboard data: `get_dashboard_data()`
  * Action data: `get_action_data()`
  * Auth state: Through validation utilities
- Messaging service accessed through `state_manager.messaging`
- NO direct state access or passing

3. **State Persistence**
- Redis as persistent storage
- Atomic operations for consistency
- AOF persistence for durability
- Transaction handling for safety
- NO direct Redis access
- NO manual persistence

4. **Component State Integration**
- Components handle their own state:
  * API calls through `make_api_request`
  * Message sending through `state_manager.messaging`
  * Error handling through `ErrorHandler`
  * State updates with validation tracking
- Clear boundaries between components:
  * Display components -> Read-only state access
  * Input components -> Validated state updates
  * API components -> State updates through handlers
  * Confirm components -> Gate for user confirmation

## State Structure

```python
{
    # Protected Core State (only updated through utilities)
    "channel": {              # Channel info
        "type": str,         # Channel type (e.g., "whatsapp")
        "identifier": str    # Channel ID
    },
    "dashboard": dict,        # Dashboard state (API-sourced)
    "action": dict,          # Action state (API-sourced)
    "auth": {                # Auth state
        "token": str        # JWT token
    },

    # Flow/Component State
    "current": {
        "path": str,         # Current flow path
        "component": str,    # Active component
        "awaiting_input": bool,  # True while waiting for input
        "component_result": str,  # For flow branching
        "data": dict         # Component-specific data
    },

    # Validation
    "validation": {
        "attempts": dict,    # Attempts per operation
        "history": [         # Validation history
            {
                "operation": str,
                "component": str,
                "timestamp": str,
                "success": bool,
                "error": Optional[str]
            }
        ]
    },

    "_metadata": {
        "initialized_at": str,  # ISO format datetime
        "updated_at": str      # ISO format datetime
    }
}
```

### State Access and Updates

1. **Protected State**
   - Access through dedicated methods (get_dashboard_data, etc.)
   - Updated only through specific utilities
   - Set during initialization or by API calls

2. **Component State**
   - Access: get_path(), get_component(), get_component_result()
   - Data: Components manage through get_component_data()
   - Updates: Components update own data, headquarters manages flow

3. **Validation**
   ```python
   # Get validation status
   status = state_manager.get_validation_status("operation_name")
   print(f"Attempts: {status['attempts']}")
   print(f"Latest: {status['latest']}")

   # Get full history
   history = state_manager.get_validation_history()
   ```

## Code Organization

The state management code is organized in layers:

1. **Flow Layer** (headquarters.py)
   - Manages application flows
   - Uses state manager for data
   - Makes branching decisions

2. **State Layer** (manager.py, atomic_manager.py)
   - Manages protected and component state
   - Handles validation and tracking
   - Coordinates with Redis layer

3. **Storage Layer** (persistence/)
   - Handles Redis operations
   - Manages connections
   - Ensures data durability

Each layer has clear responsibilities and boundaries. Start with flow/manager.py to understand the core concepts, then explore other layers as needed.

## Mistakes to avoid:
1. DON'T bypass headquarters.py for flow control
2. DON'T access state directly
3. DON'T update without validation
4. DON'T break component boundaries
5. DON'T mix state responsibilities
