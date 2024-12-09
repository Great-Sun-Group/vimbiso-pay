# Mock WhatsApp Testing Server

This directory contains a mock WhatsApp server for testing the Credex chatbot. It provides both a CLI interface and a web interface for sending test messages.

## Purpose

The mock server acts as a proxy that:
1. Accepts WhatsApp-formatted webhook messages
2. Forwards them to either:
   - Local development server (http://app:8000/bot/webhook) via Docker network
   - Staging server (https://stage.whatsapp.vimbisopay.africa/bot/webhook)
3. Returns the responses back to the client

This allows testing the chatbot without needing a real WhatsApp integration.

## Docker Setup

The mock server runs in its own Docker container and communicates with the app service over the Docker network:
```yaml
services:
  mock:
    build:
      context: ..
      target: development
    volumes:
      - ../mock:/app/mock
    ports:
      - "8001:8001"
    command: ["python3", "mock/server.py"]
    depends_on:
      - app
    networks:
      - app-network
```

## Usage

### CLI Interface

```bash
# Send to local development server (from host machine)
python3 mock/cli.py --phone 263778177125 "hi"

# Send to staging server
python3 mock/cli.py --phone 263778177125 "hi" --target staging

# Send button response
python3 mock/cli.py --type button "button_1"

# Send interactive message
python3 mock/cli.py --type interactive "menu_option_1"
```

### Web Interface

1. Start the services:
```bash
# Start all services including mock server
make dev-up

# Or start mock server separately
make mockery
```

2. Access the web interface:
   - From host machine: http://localhost:8001
   - From Docker network: http://mock:8001

3. Use the toggle to switch between local and staging targets
4. Send messages through the web interface

## Network Architecture

```
Host Machine (localhost)
└── Docker Network (app-network)
    ├── mock service (mock:8001)
    │   └── Forwards requests to app service
    ├── app service (app:8000)
    │   └── Handles WhatsApp webhook requests
    └── redis service (redis:6379)
        └── State management
```

## Message Flow

1. **Request Processing**
```python
# Incoming webhook message
POST /webhook?target=local
{
    "entry": [{
        "changes": [{
            "value": {
                "messages": [{
                    "type": "text|button|interactive",
                    "text|button|interactive": { ... }
                }]
            }
        }]
    }]
}
```

2. **Request Forwarding**
```python
# Headers added by mock server
headers = {
    "Content-Type": "application/json",
    "X-Mock-Testing": "true",
    "Accept": "application/json"
}
```

## Logging

The server implements detailed logging:
```python
logger.info(f"Received message: {text}")
logger.info(f"From: {contact['profile']['name']}")
logger.info(f"Phone: {contact['wa_id']}")
logger.info(f"Type: {message_type}")
logger.info(f"Target: {target}")
```

Error logging includes:
- Connection failures
- Timeout errors
- JSON parsing errors
- Server errors

## Security

1. **Test Request Identification**
   - X-Mock-Testing header added to all requests
   - Only accepted in development/debug mode
   - Prevents test traffic in production

2. **Error Handling**
   - Sanitized error responses
   - Detailed error logging
   - Connection timeout handling

3. **Environment Isolation**
   - Separate local/staging targets
   - Docker network isolation
   - Port mapping control

## Troubleshooting

1. **Connection Issues**
```bash
# Check if app service is running
docker-compose ps app

# Check mock server logs
docker-compose logs -f mock
```

2. **Common Errors**
- 502 Bad Gateway: App service not accessible
- 504 Gateway Timeout: Request timeout
- 500 Internal Server Error: Processing error

3. **Debug Mode**
```bash
# Start mock server with debug logging
python3 mock/server.py
