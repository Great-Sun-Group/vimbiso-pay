# State Management

## Overview

VimbisoPay uses atomic Redis-based state management to handle WhatsApp conversations and user sessions. This enables:
- Atomic state operations with optimistic locking
- Stateful conversations with context
- Multi-step form handling
- Menu navigation tracking
- Session timeouts with JWT token management

## Architecture

The state management system is implemented in `app/core/utils/redis_atomic.py` using the AtomicStateManager class, which provides:

- Atomic operations using Redis WATCH/MULTI/EXEC
- Version tracking and conflict detection
- Automatic retries for concurrent modifications
- JWT token management with 5-minute expiry
- Preservation of critical fields during cleanup

## Core Features

### Atomic State Operations

```python
class AtomicStateManager:
    """Manages atomic state operations with Redis"""

    def atomic_update(self, key_prefix: str, state: Dict[str, Any], ttl: int) -> Tuple[bool, Optional[str]]:
        """Atomically update state with optimistic locking"""

    def atomic_get(self, key_prefix: str, include_metadata: bool = True) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Atomically get state and metadata"""

    def atomic_cleanup(self, key_prefix: str, preserve_fields: Optional[set] = None) -> Tuple[bool, Optional[str]]:
        """Atomically cleanup state while preserving fields"""
```

### State Structure
```python
{
    "jwt_token": str,          # 5-minute expiry token
    "profile": {
        "member": {...},       # Member details
        "accounts": [...]      # Account information
    },
    "current_account": {...},  # Active account context
    "_version": int,          # State version for conflict detection
    "_last_updated": str      # ISO timestamp of last update
}
```

### State Flow
1. **Initial Contact**
   - Create new state with version tracking
   - Initialize user context
   - Set JWT token with 5-minute expiry

2. **Menu Navigation**
   - Atomic updates with optimistic locking
   - Automatic retry on concurrent modifications
   - Preserve critical fields during updates

3. **Form Handling**
   - Atomic state transitions
   - Validation before state changes
   - Cleanup of abandoned forms

4. **Transaction Context**
   - Atomic transaction state updates
   - Version-tracked changes
   - Automatic cleanup of expired states

## Redis Configuration

VimbisoPay uses a dedicated Redis instance (`REDIS_STATE_URL`) for state management:
- Optimized for atomic operations
- Configured for persistence
- Independent scaling

### Key Structure
- State: `{key_prefix}` (e.g., "user:123")
- Metadata: `{key_prefix}_stage`, `{key_prefix}_option`, `{key_prefix}_direction`

### Configuration
```yaml
redis-state:
  command: >
    redis-server
    --maxmemory 256mb
    --maxmemory-policy allkeys-lru
    --appendonly yes
    --appendfsync everysec
```

### Timeouts
- JWT Token: 5 minutes (refreshed on use)
- State TTL: 5 minutes (aligned with JWT)
- Metadata: 5 minutes

## Error Recovery

1. **Concurrent Modifications**
   - Optimistic locking with WATCH
   - Automatic retry (max 3 attempts)
   - Version conflict detection

2. **Failed Operations**
   - Atomic rollback
   - Detailed error logging
   - Preserved critical fields

## Security

- Atomic operations prevent race conditions
- Short-lived JWT tokens (5 minutes)
- Version tracking prevents stale updates
- Automatic cleanup of expired states
- Isolated Redis instance

For more details on:
- WhatsApp integration: [WhatsApp](whatsapp.md)
- API integration: [API Integration](api-integration.md)
- Redis configuration: [Redis Management](../redis-memory-management.md)
