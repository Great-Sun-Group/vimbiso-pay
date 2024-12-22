# State Management

## Overview

VimbisoPay uses a multi-layered state management system built on Redis to handle WhatsApp conversations and user sessions. The system provides:

- Atomic state operations
- Stateful conversations
- Multi-step form handling
- Session management
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
  - Validates state structure
  - Checks field types
  - Ensures critical field preservation
  - Provides validation results

- **FlowStateManager** (flow_state.py)
  - Manages flow state transitions
  - Handles validation state
  - Provides rollback mechanisms
  - Preserves context during transitions

- **FlowAuditLogger** (flow_audit.py)
  - Logs flow events and transitions
  - Tracks validation results
  - Provides error context
  - Enables state recovery

### 2. State Structure

Core state includes:
- JWT token (5-minute expiry)
- User profile and accounts
- Flow state
- Version tracking
- Audit trail data

Flow state includes:
- Current step and data
- Minimal validation state in flow_data.data
- Previous state for rollback
- Version information
- Smart recovery paths

Key improvements:
- Simplified validation context
- Focused state structure
- Efficient recovery mechanisms
- Clear validation paths

### 3. Key Features

1. **Version Management**
   - Incremental version tracking
   - Conflict detection
   - Automatic retries
   - Version preservation

2. **TTL Management**
   - 5-minute session timeout
   - Aligned TTLs for related data
   - Automatic cleanup
   - Core field preservation

3. **Smart Recovery**
   - Context-aware recovery
   - Multi-step recovery paths
   - Last valid state restoration
   - Clear error messages
   - Recovery attempt logging

4. **Audit Logging**
   - Flow event tracking
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

1. **State Updates**
   - Use atomic operations
   - Validate core fields
   - Keep validation minimal
   - Handle concurrent access
   - Log key transitions

2. **Flow Integration**
   - Use FlowStateManager
   - Keep validation in flow_data.data
   - Handle transitions efficiently
   - Implement smart recovery
   - Focus audit trail

3. **Error Handling**
   - Use structured errors
   - Preserve context
   - Log error details
   - Clean up properly
   - Enable automatic recovery

4. **Audit Trail**
   - Log all state transitions
   - Track validation results
   - Document error scenarios
   - Monitor recovery attempts
   - Maintain debugging context

For more details on:
- Flow Framework: [Flow Framework](flow-framework.md)
- Redis Management: [Redis Management](redis-memory-management.md)
- Security: [Security](security.md)
