# WhatsApp Integration Module

This module handles WhatsApp message processing for the Credex system, including user registration, credex transactions, and account management.

## Structure

```
whatsapp/
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

## Usage

### Basic Usage

```python
from core.whatsapp import WhatsAppActionHandler

# Initialize the handler with your service
handler = WhatsAppActionHandler(service)

# Handle an action
response = handler.handle_action("handle_action_menu")
```

### Message Types

The module uses TypedDict for type safety:

```python
from core.whatsapp import WhatsAppMessage

message: WhatsAppMessage = {
    "messaging_product": "whatsapp",
    "to": "phone_number",
    "recipient_type": "individual",
    "type": "text",
    "text": {"body": "message"}
}
```

### Forms

Pre-built form generators for common actions:

```python
from core.whatsapp import registration_form, offer_credex

# Generate registration form
form = registration_form(mobile_number, "Welcome message")

# Generate credex offer form
form = offer_credex(mobile_number, "Offer details")
```

## Handler Categories

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

## Development

### Adding New Actions

1. Choose the appropriate handler category
2. Add the action method to the handler class
3. Update the main handler's routing in `handler.py`

Example:

```python
# In credex_handlers.py
class CredexActionHandler(BaseActionHandler):
    def handle_new_action(self) -> WhatsAppMessage:
        # Implementation
        pass

# In handler.py
def _handle_credex_action(self, action: str) -> WhatsAppMessage:
    handler_map = {
        "handle_new_action": self.credex_handler.handle_new_action,
        # ... existing handlers
    }
    return handler_map.get(action, self.credex_handler.handle_default_action)()
```

### Adding New Message Templates

Add new templates to `screens.py`:

```python
NEW_TEMPLATE = """
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

{message}

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""
```

## Best Practices

1. Use type hints consistently
2. Keep handlers focused and single-purpose
3. Document new methods and classes
4. Use the base handler's utility methods
5. Follow the established message format
