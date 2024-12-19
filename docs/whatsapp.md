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
   class MemberFlow(Flow):
       def _get_first_name_prompt(self, _) -> Message:
           return MemberTemplates.create_first_name_prompt(
               self.data.get("mobile_number")
           )

       def _create_registration_confirmation(self, state: Dict[str, Any]) -> Message:
           return MemberTemplates.create_registration_confirmation(
               recipient=self.data.get("mobile_number"),
               first_name=state["first_name"]["first_name"],
               last_name=state["last_name"]["last_name"]
           )
   ```

### WhatsApp Service

The WhatsAppMessagingService handles all WhatsApp API interactions:

```python
class WhatsAppMessagingService:
    async def _send_message(self, message: Message) -> Dict[str, Any]:
        """Send a message via WhatsApp Cloud API"""
        try:
            # Convert core message to WhatsApp format
            whatsapp_message = WhatsAppMessage.from_core_message(message)

            # Send via API client
            return await self.api_client.send_message(whatsapp_message)
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            raise

    async def send_template(
        self,
        recipient: str,
        template_name: str,
        language: str,
        components: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Send a template message"""
        try:
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
            return await self.api_client.send_message(message)
        except Exception as e:
            logger.error(f"Error sending template: {str(e)}")
            raise
```

## Best Practices

1. **Message Creation**
   - Use domain-specific template classes
   - Return Message objects consistently
   - Follow WhatsApp Cloud API limits
   - Handle errors gracefully

2. **Template Organization**
   - Group related templates in domain classes
   - Use static methods for template creation
   - Keep templates focused and reusable
   - Document template parameters

3. **Flow Implementation**
   - Use template methods directly
   - Keep flow logic separate from templates
   - Handle state updates consistently
   - Provide clear error messages

4. **Error Handling**
   ```python
   def complete(self) -> Message:
       try:
           if not self.validate_state():
               return Templates.create_error_message(
                   self.data.get("mobile_number"),
                   "Invalid state"
               )

           result = self._process_completion()
           self._update_state(result)

           return Templates.create_success_message(
               self.data.get("mobile_number"),
               "Operation completed successfully"
           )
       except Exception as e:
           logger.error(f"Flow completion error: {str(e)}")
           return Templates.create_error_message(
               self.data.get("mobile_number"),
               str(e)
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
