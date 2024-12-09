# API Integration Documentation

## Overview

VimbisoPay integrates with the credex-core API to provide financial services through WhatsApp. The integration handles:
- User authentication and registration
- Account management
- Financial transactions
- Balance and ledger queries

## Base Configuration

```python
base_url = config('MYCREDEX_APP_URL')
headers = {
    "Content-Type": "application/json",
    "x-client-api-key": config("CLIENT_API_KEY")
}
```

## Authentication

### 1. Login
**Endpoint:** `/login`
```python
# Request
{
    "phone": "user_phone_number"
}

# Response (200)
{
    "data": {
        "action": {
            "details": {
                "token": "jwt_token"
            }
        }
    }
}
```

### 2. Registration
**Endpoint:** `/onboardMember`
```python
# Request
{
    "first_name": "string",
    "last_name": "string",
    "phone_number": "string"
}

# Response (201)
{
    "data": {
        "action": {
            "details": {
                "token": "jwt_token"
            }
        }
    }
}
```

## Account Management

### 1. Get Member Dashboard
**Endpoint:** `/getMemberDashboardByPhone`
```python
# Request
{
    "phone": "user_phone_number"
}

# Response (200)
{
    "data": {
        "action": {
            "details": {
                "memberID": "string",
                "firstname": "string",
                "lastname": "string",
                "memberHandle": "string",
                "defaultDenom": "USD",
                "memberTier": {
                    "low": 1,
                    "high": 0
                }
            }
        },
        "dashboard": {
            "accounts": [
                {
                    "data": {
                        "accountID": "string",
                        "accountName": "string",
                        "accountHandle": "string",
                        "defaultDenom": "USD",
                        "isOwnedAccount": true,
                        "balanceData": {
                            "data": {
                                "securedNetBalancesByDenom": ["99.76 USD"],
                                "unsecuredBalancesInDefaultDenom": {
                                    "totalPayables": "0.00 USD",
                                    "totalReceivables": "0.00 USD",
                                    "netPayRec": "0.00 USD"
                                }
                            }
                        }
                    }
                }
            ]
        }
    }
}
```

### 2. Validate Handle
**Endpoint:** `/getAccountByHandle`
```python
# Request
{
    "accountHandle": "handle_to_validate"
}

# Response (200)
{
    "success": true,
    "data": {
        "accountDetails": {
            "accountID": "string",
            "accountName": "string"
        }
    }
}
```

## Transaction Operations

### 1. Create Credex Offer
**Endpoint:** `/createCredex`
```python
# Request
{
    "authorizer_member_id": "string",
    "issuer_member_id": "string",
    "amount": "string",
    "currency": "USD",
    "securedCredex": true,
    "dueDate": "timestamp" # Only for unsecured credex
}

# Response (200)
{
    "data": {
        "action": {
            "type": "CREDEX_CREATED",
            "details": {
                "amount": "string",
                "denomination": "USD",
                "securedCredex": true,
                "receiverAccountID": "string",
                "receiverAccountName": "string"
            }
        }
    }
}
```

### 2. Accept Credex
**Endpoint:** `/acceptCredex`
```python
# Request
{
    "credexID": "string",
    "signerID": "string"
}

# Response (200)
{
    "data": {
        "action": {
            "type": "CREDEX_ACCEPTED"
        }
    }
}
```

### 3. Accept Multiple Credex
**Endpoint:** `/acceptCredexBulk`
```python
# Request
{
    "signerID": "string",
    "credexIDs": ["string"]
}

# Response (200)
{
    "summary": {
        "accepted": true,
        "total": 5,
        "successful": 5
    }
}
```

### 4. Decline/Cancel Credex
**Endpoints:**
- `/declineCredex`
- `/cancelCredex`
```python
# Request
{
    "credexID": "string",
    "signerID": "string"
}

# Response (200)
{
    "status": "success",
    "message": "Credex cancelled/declined successfully"
}
```

### 5. Get Transaction History
**Endpoint:** `/getLedger`
```python
# Request
{
    "accountID": "string",
    "numRows": 8,
    "startRow": 1
}

# Response (200)
{
    "data": [
        {
            "credexID": "string",
            "formattedInitialAmount": "string",
            "counterpartyAccountName": "string",
            "transactionType": "string",
            "dateTime": "string"
        }
    ]
}
```

## Error Handling

All endpoints follow a consistent error response format:

```python
# 400 Bad Request
{
    "message": "Error description"
}

# 401 Unauthorized
{
    "message": "Invalid token or unauthorized access"
}

# 404 Not Found
{
    "message": "Resource not found"
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

3. **Error Handling**
   - Comprehensive error logging
   - User-friendly error messages
   - Automatic retry on token expiry

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
   ```

3. **Environment Variables**
   ```env
   MYCREDEX_APP_URL=https://dev.mycredex.dev
   CLIENT_API_KEY=your_api_key
