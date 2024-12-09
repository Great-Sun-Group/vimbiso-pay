# Testing Infrastructure

## Overview

VimbisoPay provides a comprehensive testing infrastructure centered around a mock WhatsApp server that enables testing without real WhatsApp credentials. The system supports:
- Web interface for manual testing
- CLI interface for automated testing
- Request/response logging
- Environment switching (local/staging)

## Mock Server Architecture

### Components
```
mock/
├── server.py      # Mock WhatsApp webhook server
├── cli.py         # Command-line testing interface
└── index.html     # Web testing interface
```

### Server Configuration
```python
TARGETS = {
    'local': 'http://app:8000/bot/webhook',
    'staging': 'https://stage.whatsapp.vimbisopay.africa/bot/webhook'
}
```

## CLI Testing Tool

### Basic Usage
```bash
# Send text message
./mock/cli.py "Hello, world!"

# Custom phone and username
./mock/cli.py --phone 263778177125 --username "Test User" "Hello!"

# Button response
./mock/cli.py --type button "button_1"

# Interactive message
./mock/cli.py --type interactive "menu_option_1"
```

### Command Line Options
```bash
options:
  -h, --help            Show help message
  --phone PHONE         Phone number (default: 1234567890)
  --username USERNAME   Username (default: CLI User)
  --type {text,button,interactive}
                       Message type (default: text)
  --port PORT          Server port (default: 8001)
  --phone_number_id ID  WhatsApp Phone Number ID (default: 123456789)
  --target {local,staging}
                       Target environment (default: local)
```

### Message Types
1. Text Messages
```bash
./mock/cli.py "Your message here"
```

2. Button Responses
```bash
./mock/cli.py --type button "accept_offer_123"
```

3. Interactive Messages
```bash
./mock/cli.py --type interactive "menu_option_1"
```

## Web Interface

Access the web interface at http://localhost:8001

### Features
1. **Chat Interface**
   - WhatsApp-style messaging
   - Real-time conversation history
   - Message type selection
   - Environment switching

2. **Message Types**
   - Text messages
   - Button responses
   - Interactive messages
   - Form responses

3. **Testing Controls**
   - Custom phone numbers
   - Custom usernames
   - Environment selection
   - Message history

## Message Format

### WhatsApp Webhook Format
```python
{
    "entry": [{
        "changes": [{
            "value": {
                "metadata": {
                    "phone_number_id": "PHONE_ID",
                    "display_phone_number": "DISPLAY_NUMBER"
                },
                "contacts": [{
                    "wa_id": "PHONE_NUMBER",
                    "profile": {"name": "USERNAME"}
                }],
                "messages": [{
                    "type": "MESSAGE_TYPE",
                    "timestamp": "TIMESTAMP",
                    # Message-specific content
                }]
            }
        }]
    }]
}
```

### Message Content Types
```python
# Text Message
{
    "text": {
        "body": "message_text"
    }
}

# Button Response
{
    "button": {
        "payload": "button_id"
    }
}

# Interactive Response
{
    "interactive": {
        "type": "button_reply",
        "button_reply": {
            "id": "menu_option"
        }
    }
}
```

## Logging and Debugging

### Server Logs
```python
logger.info(f"Received message: {text}")
logger.info(f"From: {contact['profile']['name']}")
logger.info(f"Phone: {contact['wa_id']}")
logger.info(f"Type: {message_type}")
logger.info(f"Target: {target}")
```

### Request/Response Logging
```python
logger.info(f"Target URL: {TARGETS[target]}")
logger.info(f"Request Headers: {headers}")
logger.info(f"Request Payload: {payload}")
logger.info(f"Response Status: {response.status_code}")
logger.info(f"Response Content: {response.text}")
```

### Error Handling
1. **Connection Errors**
   - Timeout handling
   - Connection failure detection
   - Server unavailability checks

2. **Response Validation**
   - JSON format validation
   - Status code checking
   - Error message formatting

## Testing Scenarios

### 1. User Registration
```bash
# Start registration flow
./mock/cli.py "hi"

# Submit registration form
./mock/cli.py --type interactive "registration_form"
```

### 2. Transaction Testing
```bash
# Offer credex
./mock/cli.py "0.5=>recipientHandle"

# Accept offer
./mock/cli.py --type button "accept_123"

# Decline offer
./mock/cli.py --type button "decline_123"
```

### 3. Menu Navigation
```bash
# Main menu
./mock/cli.py "menu"

# Select options
./mock/cli.py --type interactive "handle_action_transactions"
```

## Security Testing

### Headers
```python
headers = {
    "Content-Type": "application/json",
    "X-Mock-Testing": "true",
    "Accept": "application/json"
}
```

### Test Environments
- Local: http://app:8000/bot/webhook
- Staging: https://stage.whatsapp.vimbisopay.africa/bot/webhook

### Error Scenarios
- Invalid tokens
- Expired sessions
- Malformed requests
- Server timeouts
- Connection failures

## Best Practices

1. **Test Organization**
   - Group related tests
   - Use descriptive test names
   - Document expected outcomes

2. **Environment Management**
   - Use appropriate target environment
   - Clean up test data
   - Reset state between tests

3. **Error Handling**
   - Test error scenarios
   - Validate error messages
   - Check recovery flows

4. **Data Validation**
   - Verify message format
   - Check state transitions
   - Validate responses
