# API Integration Documentation

## Overview

VimbisoPay integrates with the credex-core API to provide financial services through WhatsApp. The integration handles:
- User authentication and registration
- Account management
- Financial transactions
- Balance and ledger queries
- Real-time webhooks for updates
- Internal API endpoints for system operations

## Base Configuration

```python
base_url = config('MYCREDEX_APP_URL')
headers = {
    "Content-Type": "application/json",
    "x-client-api-key": config("CLIENT_API_KEY")
}
```

## Webhook Integration

### Webhook Handler
**Endpoint:** `/api/webhooks/`

Handles incoming webhooks from CredEx core for real-time updates.

#### Company Update Webhook
```python
# Request
{
    "metadata": {
        "webhook_id": "unique_id",
        "timestamp": "2024-01-01T00:00:00Z",
        "signature": "webhook_signature",
        "event_type": "company_update"
    },
    "payload": {
        "company_id": "string",
        "name": "string",
        "status": "string",
        "updated_fields": ["field1", "field2"],
        "metadata": {}  # Optional
    }
}

# Response (200)
{
    "status": "success",
    "message": "Company update processed"
}
```

#### Member Update Webhook
```python
# Request
{
    "metadata": {
        "webhook_id": "unique_id",
        "timestamp": "2024-01-01T00:00:00Z",
        "signature": "webhook_signature",
        "event_type": "member_update"
    },
    "payload": {
        "member_id": "string",
        "company_id": "string",
        "status": "string",
        "updated_fields": ["field1", "field2"],
        "metadata": {}  # Optional
    }
}

# Response (200)
{
    "status": "success",
    "message": "Member update processed"
}
```

#### Offer Update Webhook
```python
# Request
{
    "metadata": {
        "webhook_id": "unique_id",
        "timestamp": "2024-01-01T00:00:00Z",
        "signature": "webhook_signature",
        "event_type": "offer_update"
    },
    "payload": {
        "offer_id": "string",
        "company_id": "string",
        "status": "string",
        "amount": 100.00,
        "currency": "USD",
        "expiry": "2024-02-01T00:00:00Z",
        "metadata": {}  # Optional
    }
}

# Response (200)
{
    "status": "success",
    "message": "Offer update processed"
}
```

## Internal API Endpoints

### Company Operations
**Base Path:** `/api/companies/`

#### List Companies
```python
# GET /api/companies/
# Headers: Authorization: Bearer <token>

# Response (200)
[
    {
        "company_id": "string",
        "name": "string",
        "status": "string"
    }
]
```

#### Get Company Details
```python
# GET /api/companies/{company_id}/
# Headers: Authorization: Bearer <token>

# Response (200)
{
    "company_id": "string",
    "name": "string",
    "status": "string",
    "details": {}
}
```

### Member Operations
**Base Path:** `/api/members/`

#### List Members
```python
# GET /api/members/
# Headers: Authorization: Bearer <token>

# Response (200)
[
    {
        "member_id": "string",
        "company_id": "string",
        "status": "string"
    }
]
```

#### Get Member Details
```python
# GET /api/members/{member_id}/
# Headers: Authorization: Bearer <token>

# Response (200)
{
    "member_id": "string",
    "company_id": "string",
    "status": "string",
    "details": {}
}
```

### Offer Operations
**Base Path:** `/api/offers/`

#### List Offers
```python
# GET /api/offers/
# Headers: Authorization: Bearer <token>

# Response (200)
[
    {
        "offer_id": "string",
        "company_id": "string",
        "status": "string",
        "amount": 100.00,
        "currency": "USD"
    }
]
```

#### Get Offer Details
```python
# GET /api/offers/{offer_id}/
# Headers: Authorization: Bearer <token>

# Response (200)
{
    "offer_id": "string",
    "company_id": "string",
    "status": "string",
    "amount": 100.00,
    "currency": "USD",
    "expiry": "2024-02-01T00:00:00Z"
}
```

#### Accept Offer
```python
# POST /api/offers/{offer_id}/accept/
# Headers: Authorization: Bearer <token>

# Response (200)
{
    "message": "Offer accepted successfully"
}
```

#### Reject Offer
```python
# POST /api/offers/{offer_id}/reject/
# Headers: Authorization: Bearer <token>

# Response (200)
{
    "message": "Offer rejected successfully"
}
```

[Previous CredEx API Integration Content...]

## Error Handling

All endpoints follow a consistent error response format:

### API Errors
```python
# 400 Bad Request
{
    "error": "Error description",
    "details": {
        "field": "Error details"
    }
}

# 401 Unauthorized
{
    "error": "Authentication failed",
    "details": {
        "error_type": "authentication"
    }
}

# 403 Forbidden
{
    "error": "Authorization failed",
    "details": {
        "error_type": "authorization"
    }
}

# 404 Not Found
{
    "error": "Resource not found",
    "details": {
        "resource_type": "Type of resource not found"
    }
}
```

### Webhook Errors
```python
# 400 Bad Request - Validation Error
{
    "error": "Invalid webhook payload",
    "details": {
        "validation_errors": {
            "field": "Error description"
        }
    }
}

# 400 Bad Request - Signature Error
{
    "error": "Invalid webhook signature",
    "details": {
        "error_type": "signature_validation"
    }
}

# 400 Bad Request - Type Error
{
    "error": "Unsupported webhook type: type_name",
    "details": {
        "webhook_type": "type_name"
    }
}

# 500 Internal Server Error
{
    "error": "Error processing webhook",
    "details": {
        "error_type": "processing_error",
        "original_error": "Error description"
    }
}
```

## Authentication Flow

1. **Initial Request**
   - Try operation with existing token
   - If 401, attempt login
   - If login fails with 400, trigger registration

2. **Token Management**
   - Tokens stored in Redis cache
   - 5-minute expiration
   - Automatic refresh on expiry

## Security Considerations

1. **Headers**
   ```python
   headers = {
       "Content-Type": "application/json",
       "x-client-api-key": config("CLIENT_API_KEY"),
       "Authorization": f"Bearer {jwt_token}"  # When authenticated
   }
   ```

2. **Request Validation**
   - Phone number format validation
   - Amount format validation
   - Handle format validation
   - Date format validation for unsecured credex
   - Webhook signature validation
   - Payload schema validation

3. **Error Handling**
   - Comprehensive error logging
   - User-friendly error messages
   - Automatic retry on token expiry
   - Webhook processing error recovery

## Testing

1. **Mock Server**
   - Available at `mock/server.py`
   - Simulates WhatsApp webhook
   - Supports all message types

2. **Test Endpoints**
   ```bash
   # Using CLI tool
   ./mock/cli.py --type text "message"
   ./mock/cli.py --type button "button_1"

   # Test webhooks
   ./mock/cli.py --type webhook company_update
   ```

3. **Environment Variables**
   ```env
   MYCREDEX_APP_URL=https://dev.mycredex.dev
   CLIENT_API_KEY=your_api_key
