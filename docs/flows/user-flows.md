# User Flows

## Overview

VimbisoPay provides a WhatsApp interface for:
- User registration
- Account management
- Financial transactions
- Settings management

For technical details, see [WhatsApp Integration](../technical/whatsapp.md).

## Core Flows

### 1. Registration

Initial greeting:
```
I'm VimbisoPay. I'm a WhatsApp chatbot connecting
you to the credex ecosystem.

Would you like to become a member?
```

Account creation:
```
Free tier includes:
- One personal credex account
- Member handle = phone number
- Account handle = phone number
```

### 2. Account Management

Dashboard view:
```
💳 [Account Name]
Account Handle: [handle]

SECURED BALANCES
[balances]

NET ASSETS
[total]
```

Member authorization:
```
1. Enter member handle
2. Confirm authorization
3. Receive confirmation
```

### 3. Transactions

Quick commands:
```
Secured:   0.5=>handle
Unsecured: 0.5->handle
```

Confirmation flow:
1. Enter amount and recipient
2. Review offer details
3. Confirm transaction
4. Receive confirmation

Success message:
```
Transaction Complete!!
$[amount] [denomination] [type] to [recipient]
From: [source]
```

### 4. Navigation

Commands:
- `menu` - Main menu
- `home` - Dashboard
- `x` or `c` - Cancel

## Error Handling

Session expiry:
```
Invalid option selected.
Session expired. Send "hi" to login.
```

Transaction errors:
```
Failed: [error message]

To retry:
  0.5=>recipientHandle

Type 'Menu' to return
```

## Security

For security details, see [Security](../technical/security.md).

Key features:
- 5-minute sessions
- Secure state management
- Input validation
- Transaction authorization

## Testing

For testing these flows, see [Testing Guide](../technical/testing.md).

Test commands:
```bash
# Registration
./mock/cli.py "hi"

# Transaction
./mock/cli.py "0.5=>handle"

# Navigation
./mock/cli.py "menu"
```

## Related Documentation

- [API Integration](../technical/api-integration.md)
- [State Management](../technical/state-management.md)
- [WhatsApp Integration](../technical/whatsapp.md)
