# API Integration

## Overview

VimbisoPay integrates with two main APIs:
- CredEx Core API for financial services
- WhatsApp Business API for messaging

## CredEx Core Integration

### Base Configuration
```python
base_url = config('MYCREDEX_APP_URL')
headers = {
    "Content-Type": "application/json",
    "x-client-api-key": config("CLIENT_API_KEY")
}
```

### Core Features
- User authentication and registration
- Account management
- Financial transactions
- Balance and ledger queries
- Real-time webhooks
- Internal API endpoints

### Webhook Events
- Company updates
- Member updates
- Offer status changes

## WhatsApp Integration

For detailed WhatsApp implementation, see [WhatsApp Integration](whatsapp.md).

### Key Features
- Interactive menus and forms
- Message templates
- State-based conversations
- Real-time updates

### Testing Tools
- Mock server for local development
- CLI testing interface
- Web-based testing interface

## Error Handling

All endpoints follow a consistent error format:

```python
{
    "error": "Error description",
    "details": {
        "field": "Error details"
    }
}
```

Common status codes:
- 400: Bad Request (validation errors)
- 401: Unauthorized (authentication failed)
- 403: Forbidden (authorization failed)
- 404: Not Found
- 500: Internal Server Error

## Security

1. **Authentication**
   - JWT tokens
   - API keys
   - WhatsApp verification

2. **Request Validation**
   - Input sanitization
   - Schema validation
   - Webhook signatures

For more details on security measures, see [Security](security.md).

## Development Tools

### Mock Server
```bash
# Start all services
make dev-up

# Test endpoints
./mock/cli.py "message"
```

### Environment Setup
Required variables:
```bash
MYCREDEX_APP_URL=
CLIENT_API_KEY=
WHATSAPP_API_URL=
WHATSAPP_ACCESS_TOKEN=
```

For deployment details, see [Deployment](../deployment.md).
