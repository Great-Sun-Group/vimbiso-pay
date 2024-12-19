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
├── base_handler.py     # Base handler class
├── auth_handlers.py    # Authentication handlers
└── handlers/           # Domain-specific handlers
    ├── credex/         # Credex transaction flows
    │   ├── __init__.py
    │   └── flows.py    # Credex flow implementations
    └── member/         # Member management flows
        ├── __init__.py
        ├── dashboard.py # Dashboard handling
        └── flows.py    # Member flow implementations
```

### Flow Framework Integration

The service uses a progressive flow framework for handling complex interactions:

1. **Flow Types**
   - Member registration
   - Credex transactions
   - Account management
   - Dashboard navigation

2. **Step Types**
   - TEXT: Free-form text input
   - BUTTON: Button-based responses
   - LIST: Selection from options

3. **Flow Features**
   - Input validation
   - Data transformation
   - State management
   - Error handling

For details, see [Flow Framework](flow-framework.md).

### Message Types

The service supports several WhatsApp message types following the Cloud API format:

1. Text Messages
   - Basic text communication (up to 4096 characters)
   - Supports markdown-style formatting
   - Handles emojis and special characters
   - Flow step responses
   - Preview URL control

2. Interactive Messages
   - Button type (up to 3 buttons, 20 chars per title)
   - List type (sections with rows, 24 chars per title)
   - Flow navigation
   - Menu selection
   - Response handling
   - Headers and footers

3. Response Templates
   - Dynamic message generation
   - Button/list formatting
   - Flow step prompts
   - Error messages
   - Confirmation dialogs
   - Dashboard displays

4. Message Parsing
   - Strict WhatsApp format validation
   - Interactive message extraction
   - Button/list reply handling
   - Flow response processing
   - Error recovery

### Message Handling

1. Message Creation
   ```python
   # Text message
   WhatsAppMessage.create_text(
       to="phone_number",
       text="Hello, world!"
   )

   # Button message
   WhatsAppMessage.create_button(
       to="phone_number",
       text="Select an option:",
       buttons=[
           {"id": "btn_1", "title": "Option 1"},
           {"id": "btn_2", "title": "Option 2"}
       ],
       header={"type": "text", "text": "Header"}
   )

   # List message
   WhatsAppMessage.create_list(
       to="phone_number",
       text="Select from list:",
       button="Options",
       sections=[{
           "title": "Section 1",
           "rows": [
               {"id": "item_1", "title": "Item 1"},
               {"id": "item_2", "title": "Item 2"}
           ]
       }]
   )
   ```

2. Response Templates
   ```python
   def get_response_template(self, message_text: str) -> Dict[str, Any]:
       # Check for button format
       if "\n\n[" in message_text and "]" in message_text:
           text, button = message_text.rsplit("\n\n", 1)
           button_id = button[1:button.index("]")].strip()
           button_label = button[button.index("]")+1:].strip()
           return WhatsAppMessage.create_button(
               self.user.mobile_number,
               text,
               [{"id": button_id, "title": button_label}]
           )

       # Default text message
       return WhatsAppMessage.create_text(
           self.user.mobile_number,
           message_text
       )
   ```

3. Message Parsing
   ```python
   def _parse_message(self, payload: Dict[str, Any]) -> None:
       # Extract message data
       message_data = (
           payload.get("entry", [{}])[0]
           .get("changes", [{}])[0]
           .get("value", {})
       )
       messages = message_data.get("messages", [{}])

       # Parse message content
       message = messages[0]
       self.message_type = message.get("type", "")

       if self.message_type == "text":
           self.body = message.get("text", {}).get("body", "")
       elif self.message_type == "interactive":
           self._parse_interactive(message.get("interactive", {}))
   ```

### Handler Categories

1. Member Flows (`handlers/member/flows.py`)
   - Registration flow with validation
   - Profile management with templates
   - Dashboard navigation with lists
   - Account settings with buttons

2. Credex Flows (`handlers/credex/flows.py`)
   - Offer creation with step validation
   - Transaction management with confirmations
   - Balance viewing with formatting
   - Offer responses with buttons

## Mock Implementation

Located in `mock/`, this module provides a testing interface that simulates both WhatsApp client and server behavior.

### Structure

```
mock/
├── server.py          # Mock WhatsApp server
├── cli.py            # CLI client interface
├── index.html        # Web client interface
├── whatsapp_utils.py # Shared utilities
├── scripts/          # Client-side scripts
│   ├── handlers.js   # Message handlers
│   ├── main.js      # Core functionality
│   └── ui.js        # Interface updates
└── styles/          # UI styling
    └── main.css     # Core styles
```

### Components

1. Mock Server (`server.py`)
   - Simulates WhatsApp webhook endpoint
   - Forwards requests to the Credex bot
   - Handles message routing and responses
   - Provides detailed logging
   - Supports flow testing

2. Web Interface (`index.html`)
   - Simulates WhatsApp client UI
   - Supports all message types
   - Handles WhatsApp markdown formatting
   - Real-time message display
   - Flow visualization

3. CLI Interface (`cli.py`)
   - Command-line testing tool
   - Supports all message types
   - Flow testing commands
   - Quick testing of specific flows

### Usage

1. Start the mock server:
   ```bash
   python mock/server.py
   ```

2. Access the web interface:
   ```bash
   # Open in browser
   http://localhost:8001
   ```

3. Use the CLI interface:
   ```bash
   # Text message
   ./mock/cli.py "hi"

   # Flow navigation
   ./mock/cli.py --type interactive "flow:MEMBER_SIGNUP"
   ./mock/cli.py --type interactive "flow:MAKE_SECURE_OFFER"

   # Button response
   ./mock/cli.py --type button "accept_offer_123"

   # Menu selection
   ./mock/cli.py --type interactive "handleactionoffercredex"
   ```

## Best Practices

1. Flow Implementation
   - Define clear step sequences
   - Implement robust validation
   - Handle state transitions
   - Provide clear user feedback
   - Document flow logic

2. Message Handling
   - Use type hints consistently
   - Follow WhatsApp message format
   - Handle all message types
   - Validate message content
   - Support flow progression

3. Error Handling
   - Provide clear error messages
   - Log errors with context
   - Handle edge cases gracefully
   - Maintain consistent format
   - Support flow recovery

4. Testing
   - Test complete flows
   - Verify all message types
   - Check state transitions
   - Test error scenarios
   - Validate flow completion

5. Code Organization
   - Separate flow logic
   - Keep handlers focused
   - Document methods
   - Use shared utilities
   - Follow patterns

For more details on:
- Flow framework: [Flow Framework](flow-framework.md)
- State management: [State Management](state-management.md)
- API integration: [API Integration](api-integration.md)
- Security: [Security](security.md)
