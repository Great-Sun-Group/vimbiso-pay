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
├── scripts/          # Client-side scripts
│   ├── handlers.js   # Message handlers
│   ├── main.js      # Core functionality
│   └── ui.js        # Interface updates
└── styles/          # UI styling
    └── main.css     # Core styles
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

# Progressive input
./mock/cli.py --type interactive "form:amount=100,recipientAccountHandle=@user123"
```

### Web Interface
Access at http://localhost:8001
- WhatsApp-style chat interface
- Interactive menu options
- Flow navigation
- Real-time message display
- Environment switching (local/staging)
- Progressive input support

## Common Test Scenarios

### 1. User Registration Flow
```bash
# Start registration
./mock/cli.py "hi"

# Enter first name
./mock/cli.py "John"

# Enter last name
./mock/cli.py "Doe"

# Confirm registration
./mock/cli.py --type button "confirm_action"
```

### 2. Transaction Flows
```bash
# Quick command
./mock/cli.py "0.5=>handle"

# Through menu
./mock/cli.py --type interactive "handleactionoffercredex"

# Progressive input
./mock/cli.py --type interactive "form:amount=0.5,handle=user123"

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

# Progressive input
./mock/cli.py --type interactive "form:field1=value1,field2=value2"
```

### 3. Button Responses
```bash
./mock/cli.py --type button "accept_offer_123"
./mock/cli.py --type button "decline_offer_123"
./mock/cli.py --type button "confirm_action"
```

## Error and Recovery Testing

### Common Scenarios
```bash
# Invalid menu option
./mock/cli.py --type interactive "invalid_option"

# Expired session
./mock/cli.py --type interactive "handleactionoffercredex"  # After timeout

# Malformed command
./mock/cli.py "0.5=>"  # Missing handle

# Invalid progressive input
./mock/cli.py --type interactive "form:amount=invalid"

# Flow validation errors
./mock/cli.py "not_a_name"  # During name input step

# Recovery scenarios
./mock/cli.py --type interactive "flow:MAKE_SECURE_OFFER"  # After error
./mock/cli.py --type interactive "form:amount=0.5"  # Resume from last valid state
```

### Error and Recovery Format
```python
{
    "error": "Error description",
    "details": {
        "field": "Error details"
    },
    "recovery": {
        "type": "step_recovery",  # or "path_recovery"
        "message": "Recovered to previous valid step",
        "context": {
            "step_id": "amount",
            "valid_data": {...}
        }
    }
}
```

## Best Practices

1. **Flow Testing**
   - Test complete flows end-to-end
   - Verify core state transitions
   - Test essential validations
   - Check smart recovery
   - Test timeouts
   - Verify data transformation

2. **Progressive Input Testing**
   - Test critical validations
   - Verify error messages
   - Test data transformations
   - Check flow_data.data state
   - Test input examples

3. **Message Testing**
   - Test all message types
   - Verify formatting
   - Check interactions
   - Validate responses
   - Test WhatsApp limits

4. **Environment Management**
   - Use appropriate target
   - Clean up test data
   - Reset state between tests
   - Verify Redis instances

5. **Recovery Testing**
   - Test context-aware recovery
   - Check multi-step recovery
   - Verify error messages
   - Test recovery paths
   - Check recovery logging

For more details on:
- WhatsApp integration: [WhatsApp Integration](whatsapp.md)
- Flow framework: [Flow Framework](flow-framework.md)
- State management: [State Management](state-management.md)
- API integration: [API Integration](api-integration.md)
- Security testing: [Security](security.md)
