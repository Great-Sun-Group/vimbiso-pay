# Security

## Overview

VimbisoPay implements multi-layered security for:
- WhatsApp communication
- API integrations
- User data protection
- System integrity
- Flow framework
- Redis instances

## Authentication

### JWT Tokens
```python
headers = {
    "Authorization": f"Bearer {jwt_token}",
    "x-client-api-key": config("CLIENT_API_KEY")
}
```

Features:
- 5-minute expiration
- Automatic refresh
- Secure Redis storage
- Session binding

### WhatsApp Verification
```python
def validate_webhook(request):
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_signature(signature, request.body):
        raise SecurityException("Invalid signature")
```

## Data Protection

### Redis Security

#### Cache Redis
- No persistence
- Memory limits
- LRU eviction
- Automatic cleanup
- Connection pooling
- Health checks

#### State Redis
- AOF persistence
- Memory limits
- LRU eviction
- Secure state storage
- Connection pooling
- Health checks

### Flow Framework Security
- Validation through state updates
- Member ID ONLY at top level
- Channel info ONLY at top level
- NO validation state
- NO state duplication
- NO error recovery

### State Management
- Member ID ONLY at top level
- Channel info ONLY at top level
- JWT token ONLY in state
- NO state duplication
- NO state transformation
- NO state passing

### Sensitive Data
- Data minimization
- TLS encryption
- Secure storage
- NO sensitive logs
- NO state duplication
- NO validation state

## API Security

### Request Validation
```python
def process_request(state_manager: Any) -> None:
    """Process request through state validation

    Args:
        state_manager: State manager instance

    Raises:
        StateException: If validation fails
    """
    # Let StateManager validate request data
    state_manager.update_state({
        "flow_data": {
            "request": {
                "phone": state_manager.get("channel")["identifier"],  # ONLY at top level
                "amount": state_manager.get("flow_data")["input"]["amount"],
                "handle": state_manager.get("flow_data")["input"]["handle"]
            }
        }
    })

    # Let StateManager validate headers
    state_manager.update_state({
        "flow_data": {
            "headers": {
                "content_type": "application/json",
                "api_key": state_manager.get("api_key"),  # ONLY in state
                "token": state_manager.get("jwt_token")   # ONLY in state
            }
        }
    })
```

### Rate Limiting
```python
def check_rate_limit(state_manager: Any) -> None:
    """Check rate limit through state validation

    Args:
        state_manager: State manager instance

    Raises:
        StateException: If rate limit exceeded
    """
    # Let StateManager validate rate limit
    state_manager.update_state({
        "flow_data": {
            "rate_limit": {
                "user_id": state_manager.get("member_id"),  # ONLY at top level
                "limit": 1000 if state_manager.get("authenticated") else 100,
                "period": "daily"
            }
        }
    })
```

## Error Handling

### Secure Responses
```python
def handle_error(state_manager: Any, error: StateException) -> Dict[str, Any]:
    """Handle error through state validation

    Args:
        state_manager: State manager instance
        error: StateException instance

    Returns:
        Error response dict
    """
    # Let StateManager validate error response
    state_manager.update_state({
        "flow_data": {
            "error": {
                "message": str(error),
                "code": error.code,
                "details": error.details
            }
        }
    })

    return {
        "error": state_manager.get("flow_data")["error"]["message"],
        "details": state_manager.get("flow_data")["error"]["details"]
    }
```

### Logging
```python
def log_event(state_manager: Any, event_type: str, data: Dict[str, Any]) -> None:
    """Log event through state validation

    Args:
        state_manager: State manager instance
        event_type: Type of event
        data: Event data

    Raises:
        StateException: If validation fails
    """
    # Let StateManager validate log data
    state_manager.update_state({
        "flow_data": {
            "log": {
                "type": event_type,
                "member_id": state_manager.get("member_id"),  # ONLY at top level
                "channel": state_manager.get("channel"),      # ONLY at top level
                "data": data
            }
        }
    })
```

## Environment Security

### Configuration
```python
# Core Security
DJANGO_ENV=production
DEBUG=False
ALLOWED_HOSTS=*.vimbisopay.africa
DJANGO_SECRET=secure-key

# Redis Security
REDIS_URL=redis://redis-cache:6379/0
REDIS_STATE_URL=redis://redis-state:6379/0

# API Security
MYCREDEX_APP_URL=https://api.mycredex.com
CLIENT_API_KEY=secure-api-key

# WhatsApp Security
WHATSAPP_API_URL=https://graph.facebook.com
WHATSAPP_ACCESS_TOKEN=secure-token
WHATSAPP_PHONE_NUMBER_ID=your-phone-id
WHATSAPP_BUSINESS_ID=your-business-id
```

### Production Settings
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
]

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

## Best Practices

1. **Authentication**
   - JWT token ONLY in state
   - NO token duplication
   - NO manual validation
   - NO error recovery
   - Let StateManager validate

2. **Data Protection**
   - Member ID ONLY at top level
   - Channel info ONLY at top level
   - NO state duplication
   - NO validation state
   - NO sensitive logs

3. **State Validation**
   - ALL validation through state updates
   - NO manual validation
   - NO validation helpers
   - NO error recovery
   - Let StateManager validate

4. **Monitoring**
   - Log through state updates
   - NO manual validation
   - NO error recovery
   - NO state fixing
   - Clear error messages
   - Let StateManager validate

For more details on:
- WhatsApp security: [WhatsApp](whatsapp.md)
- API security: [API Integration](api-integration.md)
- Flow security: [Flow Framework](flow-framework.md)
- Redis security: [Redis Management](redis-memory-management.md)
- Testing security: [Testing](testing.md)
