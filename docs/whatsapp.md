# WhatsApp Integration

This document covers both the core WhatsApp service implementation and the mock testing interface.

## Core WhatsApp Service

Located in `app/services/whatsapp/`, this module handles WhatsApp message processing for the Credex system.

### Structure

```
app/services/whatsapp/
├── __init__.py          # Package exports
├── handler.py           # Main action handler
├── types.py            # Type definitions
├── screens.py          # Message templates
├── forms.py            # Form generation
├── base_handler.py     # Base handler class
├── auth_handlers.py    # Authentication handlers
├── credex_handlers.py  # Credex transaction handlers
└── account_handlers.py # Account management handlers
```

### Message Types

The service supports several WhatsApp message types:

1. Text Messages
   - Basic text communication
   - Supports markdown-style formatting
   - Handles emojis and special characters

2. Interactive Messages
   - Flow type: For forms and navigation
   - List type: For menus and options
   - Button type: For simple interactions

3. Templates
   - Registration forms
   - Credex offer forms
   - Menu layouts
   - Balance displays

### Handler Categories

1. Authentication (`auth_handlers.py`)
   - User registration
   - Menu navigation
   - Profile selection

2. Credex Transactions (`credex_handlers.py`)
   - Offer creation
   - Transaction management
   - Balance viewing

3. Account Management (`account_handlers.py`)
   - Member authorization
   - Notification settings
   - Account switching

## Mock Implementation

Located in `mock/`, this module provides a testing interface that simulates both WhatsApp client and server behavior.

### Structure

```
mock/
├── server.py          # Mock WhatsApp server
├── cli.py             # CLI client interface
├── index.html         # Web client interface
└── whatsapp_utils.py  # Shared utilities
```

### Components

1. Mock Server (`server.py`)
   - Simulates WhatsApp webhook endpoint
   - Forwards requests to the Credex bot
   - Handles message routing and responses
   - Provides detailed logging

2. Web Interface (`index.html`)
   - Simulates WhatsApp client UI
   - Supports all message types
   - Handles WhatsApp markdown formatting
   - Real-time message display

3. CLI Interface (`cli.py`)
   - Command-line testing tool
   - Supports all message types
   - Quick testing of specific flows

4. Shared Utilities (`whatsapp_utils.py`)
   - Message payload creation
   - Response formatting
   - Message type handling

### Usage

1. Start the mock server:
   ```bash
   python mock/server.py
   ```

2. Access the web interface:
   - Open http://localhost:8001 in your browser
   - Enter test phone number and name
   - Send messages to interact with the bot

3. Use the CLI interface:
   ```bash
   python mock/cli.py --phone 1234567890 --type text "hello"
   ```

## Best Practices

1. Message Handling
   - Use type hints consistently
   - Follow WhatsApp message format specifications
   - Handle all message types appropriately
   - Validate message content

2. Error Handling
   - Provide clear error messages
   - Log errors with context
   - Handle edge cases gracefully
   - Maintain consistent error format

3. Testing
   - Use mock interface for development
   - Test all message types
   - Verify markdown formatting
   - Check error scenarios

4. Code Organization
   - Keep handlers focused and single-purpose
   - Document new methods and classes
   - Use shared utilities
   - Follow established patterns
