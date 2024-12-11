# Testing Guide

## Overview

VimbisoPay provides testing infrastructure for both WhatsApp interactions and API integrations.

## Mock WhatsApp Interface

For detailed WhatsApp testing, see [WhatsApp Integration](whatsapp.md).

### Components
```
mock/
├── server.py          # Mock webhook server
├── cli.py            # CLI interface
├── whatsapp_utils.py # Shared utilities
└── index.html        # Web interface
```

### CLI Usage
```bash
# Text message
./mock/cli.py "hi"

# Menu option selection
./mock/cli.py --type interactive "handleactionoffercredex"

# Flow navigation
./mock/cli.py --type interactive "flow:MAKE_SECURE_OFFER"

# Button response
./mock/cli.py --type button "accept_offer_123"
```

### Web Interface
Access at http://localhost:8001
- WhatsApp-style chat interface
- Interactive menu options
- Flow navigation
- Real-time message display
- Environment switching (local/staging)

## Common Test Scenarios

### 1. User Registration
```bash
# Start registration
./mock/cli.py "hi"

# Create account
./mock/cli.py --type interactive "flow:MEMBER_SIGNUP"
```

### 2. Transactions
```bash
# Quick command
./mock/cli.py "0.5=>handle"

# Through menu
./mock/cli.py --type interactive "handleactionoffercredex"

# Flow navigation
./mock/cli.py --type interactive "flow:MAKE_SECURE_OFFER"
```

### 3. Menu Navigation
```bash
# Show menu
./mock/cli.py "menu"

# Select options
./mock/cli.py --type interactive "handleactiontransactions"
```

## Message Types

### 1. Text Messages
```bash
# Basic text
./mock/cli.py "Hello"

# Quick commands
./mock/cli.py "0.5=>handle"  # Secured credex
./mock/cli.py "0.5->handle"  # Unsecured credex
```

### 2. Interactive Messages
```bash
# Menu options
./mock/cli.py --type interactive "handleactionoffercredex"
./mock/cli.py --type interactive "handleactiontransactions"

# Flow navigation
./mock/cli.py --type interactive "flow:MEMBER_SIGNUP"
./mock/cli.py --type interactive "flow:MAKE_SECURE_OFFER"
```

### 3. Button Responses
```bash
./mock/cli.py --type button "accept_offer_123"
./mock/cli.py --type button "decline_offer_123"
```

## Error Testing

### Common Scenarios
```bash
# Invalid menu option
./mock/cli.py --type interactive "invalid_option"

# Expired session
./mock/cli.py --type interactive "handleactionoffercredex"  # After timeout

# Malformed command
./mock/cli.py "0.5=>"  # Missing handle
```

### Error Format
```python
{
    "error": "Error description",
    "details": {
        "field": "Error details"
    }
}
```

## Best Practices

1. **Test Organization**
   - Group related tests
   - Use descriptive names
   - Document expected outcomes

2. **Environment Management**
   - Use appropriate target
   - Clean up test data
   - Reset state between tests

3. **Message Testing**
   - Test all message types
   - Verify formatting
   - Check interactions
   - Validate responses

4. **Flow Testing**
   - Test complete flows
   - Verify state transitions
   - Check error handling
   - Test timeouts

For more details on:
- WhatsApp integration: [WhatsApp Integration](whatsapp.md)
- State management: [State Management](state-management.md)
- API integration: [API Integration](api-integration.md)
- Security testing: [Security](security.md)
