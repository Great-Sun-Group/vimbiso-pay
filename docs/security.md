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
- Input validation per step
- State isolation
- Secure transitions
- Data transformation
- Error handling
- Timeout management

### State Management
- User state isolation
- 5-minute session timeout
- Secure transitions
- Automatic cleanup
- Dedicated Redis instance

### Sensitive Data
- Data minimization
- TLS encryption
- Secure storage
- No sensitive logs

## API Security

### Request Validation
```python
# Input validation
validate_phone_number(phone)
validate_amount(amount)
validate_handle(handle)

# Headers
validate_content_type(headers)
validate_api_key(headers)
validate_token(headers)
```

### Rate Limiting
- 100 requests/day anonymous
- 1000 requests/day authenticated
- Per-user tracking

## Error Handling

### Secure Responses
```python
{
    "error": "Error description",
    "details": {
        "field": "Error details"
    }
}
```

### Logging
```python
logger.info(f"Action: {sanitize_log_message(action)}")
logger.error(f"Error: {sanitize_error_message(error)}")
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
   - Strong JWT config
   - Secure sessions
   - Token validation
   - API key protection

2. **Data Protection**
   - Minimal collection
   - Proper encryption
   - Regular cleanup
   - Redis persistence

3. **Input Validation**
   - Flow framework validation
   - Sanitize all input
   - Validate formats
   - Secure responses

4. **Monitoring**
   - Security logging
   - Error tracking
   - Access monitoring
   - Regular audits
   - Redis monitoring

For more details on:
- WhatsApp security: [WhatsApp](whatsapp.md)
- API security: [API Integration](api-integration.md)
- Flow security: [Flow Framework](flow-framework.md)
- Redis security: [Redis Management](redis-memory-management.md)
- Testing security: [Testing](testing.md)
