# State Management

## Overview

VimbisoPay uses a member-centric state management system built on Redis to handle multi-channel conversations and user sessions. The system provides:

- Member-centric state operations
- Channel abstraction
- Atomic state operations
- Stateful conversations
- Multi-step form handling
- Error recovery
- Comprehensive audit logging

## Architecture

### 1. Core Components

- **AtomicStateManager** (redis_atomic.py)
  - Handles atomic Redis operations
  - Manages version tracking
  - Handles concurrent modifications
  - Manages TTL and cleanup

- **StateValidator** (state_validator.py)
  - Validates member and channel structure
  - Validates state structure
  - Checks field types
  - Ensures critical field preservation
  - Provides validation results

- **FlowStateManager** (flow_state.py)
  - Manages member-centric state
  - Handles channel information
  - Manages flow state transitions
  - Handles validation state
  - Provides rollback mechanisms
  - Preserves context during transitions

- **FlowAuditLogger** (flow_audit.py)
  - Logs flow events with member context
  - Tracks state transitions
  - Records validation results
  - Provides error context
  - Enables state recovery

### 2. State Structure

Core state includes:
```python
{
    # Core identity - SINGLE SOURCE OF TRUTH
    "member_id": "unique_member_id",  # Primary identifier, ONLY AND ALWAYS at top level

    # Channel information
    "channel": {
        "type": "whatsapp",
        "identifier": "channel_specific_id"
    },

    # Authentication
    "jwt_token": "token",  # 5-minute expiry
    "authenticated": true,

    # Profile and accounts
    "profile": { ... },
    "current_account": { ... },

    # Flow state
    "flow_data": {
        "id": "flow_id",
        "step": current_step,
        "data": {
            "flow_type": "flow_type",
            "channel": {
                "type": "whatsapp",
                "identifier": "channel_specific_id"
            },
            "_validation_context": {},
            "_validation_state": {}
        }
    },

    # Version and audit
    "_version": 1,
    "_last_updated": timestamp
}
```

Flow state includes:
- Member ID as primary identifier
- Channel information
- Current step and data
- Minimal validation state in flow_data.data
- Previous state for rollback
- Version information
- Smart recovery paths

### 3. Key Features

1. **Member Management**
   - Member ID as primary identifier
   - Channel abstraction
   - Cross-channel state sharing
   - Member-specific validation
   - Member context preservation

2. **Channel Handling**
   - Channel type abstraction
   - Channel-specific identifiers
   - Channel validation rules
   - Channel state preservation
   - Cross-channel compatibility

3. **Version Management**
   - Incremental version tracking
   - Conflict detection
   - Automatic retries
   - Version preservation

4. **TTL Management**
   - 5-minute session timeout
   - Aligned TTLs for related data
   - Automatic cleanup
   - Core field preservation

5. **Smart Recovery**
   - Member context preservation
   - Channel state recovery
   - Multi-step recovery paths
   - Last valid state restoration
   - Clear error messages
   - Recovery attempt logging

6. **Audit Logging**
   - Member-centric event tracking
   - Channel context logging
   - State transition history
   - Validation result logging
   - Error scenario documentation
   - Recovery attempt tracking

## Redis Configuration

Uses dedicated Redis instance with:
- Atomic operations support
- Persistence enabled
- Memory limits
- Independent scaling

## Best Practices

1. **Member-Centric Design**
   - Use member_id as primary key
   - Maintain proper channel abstraction
   - Handle cross-channel state
   - Validate member context
   - Preserve member identity

2. **Channel Management**
   - Abstract channel types
   - Handle channel-specific IDs
   - Validate channel state
   - Preserve channel context
   - Enable cross-channel support

3. **State Updates**
   - Use atomic operations
   - Validate member and channel
   - Keep validation minimal
   - Handle concurrent access
   - Log key transitions

4. **Flow Integration**
   - Use FlowStateManager
   - Maintain member context
   - Handle channel state
   - Keep validation in flow_data.data
   - Handle transitions efficiently
   - Implement smart recovery
   - Focus audit trail

5. **Error Handling**
   - Preserve member context
   - Handle channel errors
   - Use structured errors
   - Log error details
   - Clean up properly
   - Enable automatic recovery

6. **Audit Trail**
   - Include member context
   - Log channel information
   - Track state transitions
   - Record validation results
   - Document error scenarios
   - Monitor recovery attempts
   - Maintain debugging context

## Migration Considerations

When migrating to member-centric architecture:

1. **State Structure**
   - Update state to use member_id
   - Add channel abstraction
   - Preserve backward compatibility
   - Handle legacy mobile_number

2. **Flow Updates**
   - Update flow initialization
   - Add channel handling
   - Update message templates
   - Modify validation rules

3. **Data Migration**
   - Map mobile numbers to members
   - Add channel information
   - Update existing states
   - Preserve user context

4. **Validation**
   - Add member validation
   - Update channel validation
   - Handle legacy validation
   - Update error messages

For more details on:
- Flow Framework: [Flow Framework](flow-framework.md)
- Redis Management: [Redis Memory Management](redis-memory-management.md)
- Security: [Security](security.md)
