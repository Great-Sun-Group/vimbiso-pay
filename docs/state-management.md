# State Management

## Overview

VimbisoPay uses a state management system built on Redis that strictly enforces SINGLE SOURCE OF TRUTH:
- Member ID exists ONLY at top level state
- Channel info exists ONLY at top level state
- No duplication of data in flow_data
- All components access data from single source

Core features:
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
  - Manages flow state transitions
  - Accesses member_id from top level state
  - Accesses channel info from top level state
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
- Current step and data
- Flow type information
- Minimal validation state in flow_data.data
- Previous state for rollback
- Version information
- Smart recovery paths

Note: Member ID and channel info are ONLY stored at top level as SINGLE SOURCE OF TRUTH

### 3. Key Features

1. **Member Management**
   - Member ID as SINGLE SOURCE OF TRUTH at top level
   - No duplication of member info in flow_data
   - Access member_id only from top level state
   - Member-specific validation at top level
   - Cross-channel state through top level identifiers

2. **Channel Handling**
   - Channel info as SINGLE SOURCE OF TRUTH at top level
   - No duplication of channel info in flow_data
   - Access channel info only from top level state
   - Channel validation at top level
   - Cross-channel support through top level abstraction

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
   - Keep member_id ONLY at top level state
   - Never duplicate member info in flow_data
   - Always access member_id from top level
   - Validate member info at top level only
   - Maintain SINGLE SOURCE OF TRUTH

2. **Channel Management**
   - Keep channel info ONLY at top level state
   - Never duplicate channel info in flow_data
   - Always access channel info from top level
   - Validate channel info at top level only
   - Maintain SINGLE SOURCE OF TRUTH

3. **State Updates**
   - Use atomic operations
   - Validate member and channel
   - Keep validation minimal
   - Handle concurrent access
   - Log key transitions

4. **Flow Integration**
   - Use FlowStateManager
   - Access member_id from top level state
   - Access channel info from top level state
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

1. **State Structure**
   - Move member_id to SINGLE SOURCE OF TRUTH at top level
   - Move channel info to SINGLE SOURCE OF TRUTH at top level
   - Remove any duplicated data from flow_data
   - Convert mobile_number to channel identifier at top level

2. **Flow Updates**
   - Update flows to access member_id from top level only
   - Update flows to access channel info from top level only
   - Remove any duplicated data access
   - Enforce SINGLE SOURCE OF TRUTH in all flows

3. **Data Migration**
   - Consolidate member info to top level
   - Consolidate channel info to top level
   - Clean up duplicated data in flow_data
   - Maintain SINGLE SOURCE OF TRUTH during migration

4. **Validation**
   - Validate member_id at top level only
   - Validate channel info at top level only
   - Remove duplicate validation checks
   - Enforce SINGLE SOURCE OF TRUTH in validators

For more details on:
- Flow Framework: [Flow Framework](flow-framework.md)
- Redis Management: [Redis Memory Management](redis-memory-management.md)
- Security: [Security](security.md)
