# State Management

## Overview

VimbisoPay uses Redis-based state management to handle WhatsApp conversations and user sessions. This enables:
- Stateful conversations with context
- Multi-step form handling
- Menu navigation tracking
- Session timeouts
- Token management

## Architecture

```
app/services/state/
├── interface.py    # Service interface
├── service.py     # Implementation
├── exceptions.py  # Error handling
└── config.py      # Configuration
```

## Core Features

### Conversation State
```python
{
    "stage": "handle_action_menu",
    "option": "handle_action_offer_credex",
    "direction": "OUT",
    "profile": {
        "member": {...},
        "accounts": [...]
    },
    "current_account": {...}
}
```

### State Flow
1. **Initial Contact**
   - Create new state
   - Set default menu stage
   - Initialize user context

2. **Menu Navigation**
   - Track selected options
   - Store menu context
   - Handle back navigation

3. **Form Handling**
   - Store partial submissions
   - Validate inputs
   - Track completion

4. **Transaction Context**
   - Store offer details
   - Track confirmation steps
   - Handle timeouts

## Redis State Management

VimbisoPay uses a dedicated Redis instance (`REDIS_STATE_URL`) for state management, separate from the caching Redis instance. This separation provides:
- Optimized persistence for conversation state
- Dedicated resources for state operations
- Independent scaling and monitoring

### Key Structure
- User-specific: `user:{phone_number}:state`
- Session-based: `session:{id}:data`
- Token storage: `token:{phone_number}`

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
- Session: 5 minutes
- Tokens: 30 minutes
- Forms: 10 minutes

## Error Recovery

1. **Session Expiry**
   - Clear expired state
   - Return to menu
   - Preserve critical data

2. **Failed Operations**
   - State rollback
   - Error logging
   - User notification

## Security

- Automatic session cleanup
- Secure token storage
- Input validation
- State isolation

For more details on:
- WhatsApp integration: [WhatsApp](whatsapp.md)
- API integration: [API Integration](api-integration.md)
- Redis configuration: [Redis Management](../redis-memory-management.md)
