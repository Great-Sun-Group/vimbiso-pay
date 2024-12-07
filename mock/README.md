# Mock WhatsApp Testing Server

This directory contains a mock WhatsApp server for testing the Credex chatbot. It provides both a CLI interface and a web interface for sending test messages.

## Purpose

The mock server acts as a proxy that:
1. Accepts WhatsApp-formatted webhook messages
2. Forwards them to either:
   - Local development server (http://localhost:8000)
   - Staging server (https://stage.whatsapp.vimbisopay.africa)
3. Returns the responses back to the client

This allows testing the chatbot without needing a real WhatsApp integration.

## Features

- Simulates WhatsApp webhook messages
- Supports both local and staging environments
- CLI interface for automated testing
- Web interface for manual testing
- Adds X-Mock-Testing header to identify test requests
- Detailed logging of requests and responses

## Usage

### CLI Interface

```bash
# Send to local development server
python3 mock/cli.py --phone 263778177125 "hi"

# Send to staging server
python3 mock/cli.py --phone 263778177125 "hi" --target staging
```

### Web Interface

1. Start the mock server:
```bash
python3 mock/server.py
```

2. Open http://localhost:8001 in your browser
3. Use the toggle to switch between local and staging targets
4. Send messages through the web interface

## Configuration

The mock server supports two target environments:

- Local: http://localhost:8000
- Staging: https://stage.whatsapp.vimbisopay.africa

You can switch between them using:
- CLI: --target flag (local/staging)
- Web: Environment toggle button

## Security Note

The mock server adds an X-Mock-Testing header to identify test requests. The chatbot server only accepts this header in debug mode, ensuring test messages can't interfere with production traffic.
