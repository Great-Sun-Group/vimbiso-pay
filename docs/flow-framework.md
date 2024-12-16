# Flow Framework

A comprehensive framework for building progressive, state-aware interactions in WhatsApp that provides type-safe message handling and standardized flow management.

## Architecture Overview

### Component Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Flow Class    │     │  Flow Handler   │     │  State Service  │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ - Steps         │     │ - Flow Registry │     │ - Redis Backend │
│ - State         │◄────┤ - Message Router│◄────┤ - State Lock    │
│ - Services      │     │ - State Manager │     │ - TTL Management│
└─────────────────┘     └─────────────────┘     └─────────────────┘
         ▲                      ▲                        ▲
         │                      │                        │
         │                      │                        │
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Step Class     │     │ Message Types   │     │ State Types     │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ - Validation    │     │ - Text          │     │ - Stage Enum    │
│ - Transform     │     │ - Interactive   │     │ - Transitions   │
│ - Conditions    │     │ - Template      │     │ - Validation    │
└─────────────────┘     └─────────────────┘     └─────────────────┘

## WhatsApp Integration

### 1. Message Types

```python
class MessageType(Enum):
    """Supported WhatsApp message types"""
    TEXT = "text"
    TEMPLATE = "template"
    INTERACTIVE = "interactive"
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    LOCATION = "location"
```

### 2. Interactive Messages

```python
def create_interactive_message(self, state: Dict[str, Any]) -> Message:
    """Create interactive message"""
    return ButtonSelection.create_buttons({
        "text": "Select an option:",
        "buttons": [
            {"id": "btn1", "title": "Option 1"},
            {"id": "btn2", "title": "Option 2"}
        ],
        "header": "Optional Header",
        "footer": "Optional Footer"
    }, recipient=state.get("phone", ""))
```

### 3. Template Messages

```python
def send_template_message(self, recipient: str) -> Dict[str, Any]:
    """Send template message"""
    return self.whatsapp.send_template(
        recipient=MessageRecipient(phone_number=recipient),
        template_name="welcome_template",
        language={"code": "en"},
        components=[{
            "type": "body",
            "parameters": [
                {"type": "text", "text": "User"}
            ]
        }]
    )
```

### 4. Media Messages

```python
def send_media_message(self, recipient: str, url: str) -> Dict[str, Any]:
    """Send media message"""
    return self.whatsapp.send_message(Message(
        recipient=MessageRecipient(phone_number=recipient),
        content=ImageContent(
            url=url,
            caption="Optional caption"
        )
    ))
```

## Message Templates

### 1. Text Formatting

```python
# Basic formatting
BASIC_TEMPLATE = """*Bold text*
_Italic text_
~Strikethrough~
```Monospace```"""

# Multi-line formatting
COMPLEX_TEMPLATE = """*{header}*
{message}

*Options:*
1. ✅ {option1}
2. ❌ {option2}"""

# List formatting
LIST_TEMPLATE = """*{title}*

{items_list}

Type *'{command}'* to continue"""
```

### 2. Interactive Components

```python
# Button selection
BUTTON_TEMPLATE = """*{title}*
{description}

1. ✅ Confirm
2. ❌ Cancel"""

# List selection
LIST_TEMPLATE = """*{category}*

*Available options:*
{options}

Select an option to continue"""
```

### 3. Status Messages

```python
# Success message
SUCCESS_TEMPLATE = """*✅ Success*

🎉 {message}

Type *'Menu'* to continue"""

# Error message
ERROR_TEMPLATE = """*❌ Error*

⚠️ {error_message}

Please try again"""

# Progress message
PROGRESS_TEMPLATE = """*⏳ Processing*

Please wait while we {action}..."""
```

## UI/UX Guidelines

### 1. Message Structure

1. **Header**
   - Use bold formatting
   - Keep it short and clear
   - Include emoji for visual context

2. **Body**
   - Break into logical sections
   - Use proper spacing
   - Include relevant details

3. **Actions**
   - Use buttons when possible
   - Use emoji indicators
   - Show clear commands

### 2. Formatting Rules

1. **Text Emphasis**
   - *Bold* for headers and important info
   - _Italic_ for instructions
   - ```Monospace``` for code/commands

2. **Emoji Usage**
   - 📝 For forms/input
   - ✅ For success/confirmation
   - ❌ For errors/cancellation
   - ⚠️ For warnings
   - 💡 For tips/info

3. **Layout**
   - Use blank lines for separation
   - Indent sub-items
   - Align related information

### 3. Response Times

1. **Immediate Responses**
   - Acknowledgment messages
   - Error notifications
   - Simple validations

2. **Progress Updates**
   - Long operations
   - Multi-step processes
   - External service calls

3. **Timeouts**
   - Session expiration
   - Input waiting time
   - Service timeouts

## Integration Examples

### 1. Registration Flow

```python
# Message template
REGISTRATION_TEMPLATE = """*👤 Registration*

Please enter your {field}:

Examples:
{examples}"""

# Flow implementation
class RegistrationFlow(Flow):
    """Registration flow implementation"""

    def _create_steps(self) -> list[Step]:
        return [
            Step(
                id="first_name",
                type=StepType.TEXT_INPUT,
                stage=StateStage.REGISTRATION.value,
                message=lambda state: ProgressiveInput.create_prompt(
                    "What's your first name?",
                    ["John", "Jane"],
                    state.get("phone", "")
                ),
                validation=self._validate_name,
                transform=lambda value: {"first_name": value.strip()}
            ),
            # More steps...
        ]
```

### 2. Transaction Flow

```python
# Message template
TRANSACTION_TEMPLATE = """*💰 Transaction*

*From:* {sender}
*To:* {recipient}
*Amount:* ${amount}

1. ✅ Confirm
2. ❌ Cancel"""

# Flow implementation
class TransactionFlow(Flow):
    """Transaction flow implementation"""

    def _create_steps(self) -> list[Step]:
        return [
            Step(
                id="amount",
                type=StepType.TEXT_INPUT,
                stage=StateStage.TRANSACTION.value,
                message=lambda state: ProgressiveInput.create_prompt(
                    "Enter amount:",
                    ["100", "USD 100"],
                    state.get("phone", "")
                ),
                validation=self._validate_amount,
                transform=self._transform_amount
            ),
            # More steps...
        ]
```

## Testing Strategies

### 1. Unit Tests

```python
def test_message_formatting():
    """Test message formatting"""
    message = ProgressiveInput.create_prompt(
        text="Test prompt",
        examples=["ex1", "ex2"],
        recipient="1234567890"
    )
    assert message.content.body == "Test prompt\n\nExamples:\n• ex1\n• ex2"

def test_flow_validation():
    """Test flow validation"""
    flow = TestFlow("test", [])
    assert flow._validate_amount("100") is True
    assert flow._validate_amount("invalid") is False
```

### 2. Integration Tests

```python
def test_flow_progression():
    """Test flow progression"""
    handler = FlowHandler(MockStateService())

    # Start flow
    result = handler.start_flow("test_flow", "1234567890")
    assert isinstance(result, TestFlow)

    # Process steps
    messages = [
        {"type": "text", "text": {"body": "John"}},
        {"type": "text", "text": {"body": "100"}},
        {"type": "interactive", "interactive": {
            "type": "button",
            "button_reply": {"id": "confirm"}
        }}
    ]

    for msg in messages:
        response = handler.handle_message("1234567890", msg)
        assert response is not None
```

### 3. End-to-End Tests

```python
def test_complete_flow():
    """Test complete flow"""
    service = TestService()

    # Initialize flow
    flow = service.start_flow("test_flow", "1234567890")

    # Complete flow
    result = service.complete_flow([
        "John",           # Name input
        "100",           # Amount input
        "confirm"        # Confirmation
    ])

    assert result.success is True
    assert "transaction_id" in result.data
```

def _validate_input(self, value: str) -> bool:
    """Chain multiple validations"""
    validators = [
        self._validate_format,
        self._validate_content,
        self._validate_business_rules
    ]
    return all(validator(value) for validator in validators)
```

### 3. State Machine
```python
def _handle_state_machine(self, action: str) -> Tuple[bool, str]:
    """Handle state machine transitions"""
    state_handlers = {
        "init": self._handle_init,
        "processing": self._handle_processing,
        "complete": self._handle_complete
    }
    handler = state_handlers.get(self.state.get("stage"))
    if not handler:
        return False, "Invalid state"
    return handler(action)
```

### 4. Service Integration
```python
def _integrate_services(self) -> None:
    """Integrate multiple services"""
    services = {
        "auth": self._setup_auth_service,
        "data": self._setup_data_service,
        "notification": self._setup_notification_service
    }
    for service_name, setup_func in services.items():
        try:
            setup_func()
        except Exception as e:
            logger.error(f"Failed to setup {service_name}: {str(e)}")
```

## Example Flows

### 1. Registration Flow
See `app/services/whatsapp/handlers/member/registration_flow.py` for a complete example of:
- Progressive data collection
- Input validation
- State management
- Service integration
- Error handling

### 2. CredEx Offer Flow
See `app/services/whatsapp/handlers/credex/offer_flow_v2.py` for an example of:
- Complex validation
- Multiple services
- State transitions
- Error recovery
- Business logic integration

## Future Enhancements

1. **Flow Templates**
   - Standard flow patterns
   - Reusable components
   - Common validations
   - State templates

2. **Visual Builder**
   - Flow visualization
   - State inspection
   - Visual debugging
   - Flow testing

3. **Analytics**
   - Flow metrics
   - User behavior
   - Performance monitoring
   - Error tracking

4. **Enhanced Testing**
   - Automated flow testing
   - State verification
   - Service mocking
   - Load testing

## Troubleshooting

### 1. Common Issues
- State corruption
- Invalid transitions
- Service failures
- Message formatting
- Validation errors

### 2. Debugging
- Enable debug logging
- Inspect state changes
- Monitor service health
- Review message flow
- Check validations

### 3. Recovery
- Reset corrupted state
- Retry operations
- Fallback handlers
- Error notifications
- Audit logging
