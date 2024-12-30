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
├── service.py          # WhatsApp messaging service
├── base_handler.py     # Base handler class
├── auth_handlers.py    # Authentication handlers
└── handlers/           # Domain-specific handlers
    ├── credex/         # Credex transaction flows
    │   ├── __init__.py
    │   ├── flows.py    # Credex flow implementations
    │   └── templates.py # Credex message templates
    └── member/         # Member management flows
        ├── __init__.py
        ├── dashboard.py # Dashboard handling
        ├── flows.py    # Member flow implementations
        └── templates.py # Member message templates
```

### Message Types

The service uses standardized message types from `core.messaging.types`:

1. **Core Message Types**
   ```python
   @dataclass
   class Message:
       """Complete message with recipient and content"""
       recipient: MessageRecipient
       content: Union[
           TextContent,
           InteractiveContent,
           TemplateContent,
           MediaContent
       ]
   ```

2. **Content Types**
   ```python
   @dataclass
   class TextContent:
       """Text message content"""
       body: str

   @dataclass
   class InteractiveContent:
       """Interactive message content"""
       interactive_type: InteractiveType  # BUTTON or LIST
       body: str
       buttons: List[Button] = field(default_factory=list)
       action_items: Dict[str, Any] = field(default_factory=dict)
   ```

### Template Organization

1. **Domain-Specific Templates**
   ```python
   class MemberTemplates:
       @staticmethod
       def create_first_name_prompt(recipient: str) -> Message:
           return Message(
               recipient=MessageRecipient(phone_number=recipient),
               content=TextContent(body="What's your first name?")
           )

       @staticmethod
       def create_registration_confirmation(
           recipient: str,
           first_name: str,
           last_name: str
       ) -> Message:
           return Message(
               recipient=MessageRecipient(phone_number=recipient),
               content=InteractiveContent(
                   interactive_type=InteractiveType.BUTTON,
                   body=(
                       "✅ Please confirm your registration details:\n\n"
                       f"First Name: {first_name}\n"
                       f"Last Name: {last_name}\n"
                       f"Default Currency: USD"
                   ),
                   buttons=[
                       Button(id="confirm_action", title="Confirm Registration")
                   ]
               )
           )
   ```

2. **Flow Integration**
   ```python
   def process_registration(state_manager: Any) -> Message:
       """Process registration through state updates

       Args:
           state_manager: State manager instance

       Returns:
           Message to send

       Raises:
           StateException: If validation fails
       """
       # Let StateManager validate state
       mobile = state_manager.get("channel")["identifier"]  # ONLY at top level

       # Let StateManager validate registration data
       state_manager.update_state({
           "flow_data": {
               "registration": {
                   "first_name": state_manager.get("flow_data")["input"]["first_name"],
                   "last_name": state_manager.get("flow_data")["input"]["last_name"]
               }
           }
       })

       # Create message with validated data
       return MemberTemplates.create_registration_confirmation(
           recipient=mobile,
           first_name=state_manager.get("flow_data")["registration"]["first_name"],
           last_name=state_manager.get("flow_data")["registration"]["last_name"]
       )
   ```

### WhatsApp Service

The WhatsAppMessagingService handles all WhatsApp API interactions:

```python
class WhatsAppMessagingService:
    async def send_message(self, message: Message) -> None:
        """Send a message via WhatsApp Cloud API

        Args:
            message: Message to send

        Raises:
            StateException: If sending fails
        """
        # Convert core message to WhatsApp format
        whatsapp_message = WhatsAppMessage.from_core_message(message)

        # Send via API client (raises StateException if fails)
        await self.api_client.send_message(whatsapp_message)

    async def send_template(
        self,
        state_manager: Any,
        template_name: str,
        language: str,
        components: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Send a template message

        Args:
            state_manager: State manager instance
            template_name: Name of template
            language: Language code
            components: Optional template components

        Raises:
            StateException: If sending fails
        """
        # Let StateManager validate recipient
        recipient = state_manager.get("channel")["identifier"]

        # Create template message
        message = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language}
            }
        }
        if components:
            message["template"]["components"] = components

        # Send message (raises StateException if fails)
        await self.api_client.send_message(message)
```

## Best Practices

1. **Message Creation**
   - Let StateManager validate all data
   - NO manual validation
   - NO error recovery
   - NO state transformation

2. **Template Organization**
   - Group related templates in domain classes
   - Use static methods for template creation
   - Keep templates focused and reusable
   - Let StateManager validate data

3. **Flow Implementation**
   - Let StateManager validate through updates
   - NO manual validation
   - NO error recovery
   - NO state transformation
   - NO state passing

4. **Error Handling**
   ```python
   def process_completion(state_manager: Any) -> Message:
       """Process completion through state updates

       Args:
           state_manager: State manager instance

       Returns:
           Message to send

       Raises:
           StateException: If validation fails
       """
       # Let StateManager validate state
       mobile = state_manager.get("channel")["identifier"]  # ONLY at top level

       # Let StateManager validate completion
       state_manager.update_state({
           "flow_data": {
               "status": "complete"
           }
       })

       # Return success message
       return Templates.create_success_message(
           recipient=mobile,
           message="Operation completed successfully"
       )
   ```

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

For more details on:
- Flow framework: [Flow Framework](flow-framework.md)
- State management: [State Management](state-management.md)
- API integration: [API Integration](api-integration.md)
- Security: [Security](security.md)
