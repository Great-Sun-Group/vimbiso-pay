# Flow Framework

## Overview

The Flow Framework provides a progressive interaction system for handling complex, multi-step conversations in WhatsApp. It enables structured data collection, validation, and state management through a series of defined steps.

## Core Components

### Flow Base Class

The framework is built around the `Flow` base class which manages:
- Step progression
- Data collection
- State management
- Input validation
- Data transformation

```python
class Flow:
    def __init__(self, id: str, steps: List[Step]):
        self.id = id
        self.steps = steps
        self.current_index = 0
        self.data: Dict[str, Any] = {}
```

### Step Definition

Each step in a flow represents a single interaction:

```python
@dataclass
class Step:
    id: str                     # Unique step identifier
    type: StepType             # Interaction type (TEXT/BUTTON/LIST)
    message: Union[str, Callable]  # Static text or dynamic message generator
    validator: Optional[Callable]  # Input validation function
    transformer: Optional[Callable] # Data transformation function
```

### Step Types

The framework supports three types of interactions:
- `TEXT`: Free-form text input
- `BUTTON`: Button-based responses
- `LIST`: Selection from a list of options

## Message Handling

### Core Message Types

The framework uses standardized message types from `core.messaging.types`:

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
   ```
   - Encapsulate domain-specific message creation
   - Consistent message formatting
   - Reusable across flows
   - Type-safe message creation

2. **Flow Integration**
   ```python
   class MemberFlow(Flow):
       def _get_first_name_prompt(self, _) -> Message:
           return MemberTemplates.create_first_name_prompt(
               self.data.get("mobile_number")
           )
   ```
   - Use template methods directly
   - Clean flow implementation
   - Consistent message handling
   - Improved maintainability

### Message Types

1. **Text Messages**
   ```python
   def create_text_message(recipient: str, text: str) -> Message:
       return Message(
           recipient=MessageRecipient(phone_number=recipient),
           content=TextContent(body=text)
       )
   ```

2. **Button Messages**
   ```python
   def create_button_message(
       recipient: str,
       text: str,
       buttons: List[Dict[str, str]]
   ) -> Message:
       return Message(
           recipient=MessageRecipient(phone_number=recipient),
           content=InteractiveContent(
               interactive_type=InteractiveType.BUTTON,
               body=text,
               buttons=[
                   Button(id=btn["id"], title=btn["title"])
                   for btn in buttons
               ]
           )
       )
   ```

3. **List Messages**
   ```python
   def create_list_message(
       recipient: str,
       text: str,
       sections: List[Dict[str, Any]]
   ) -> Message:
       return Message(
           recipient=MessageRecipient(phone_number=recipient),
           content=InteractiveContent(
               interactive_type=InteractiveType.LIST,
               body=text,
               action_items={
                   "button": "Select",
                   "sections": sections
               }
           )
       )
   ```

## Implementation

### Flow Creation

Flows are created by extending the base Flow class and defining steps:

```python
class CredexFlow(Flow):
    def __init__(self, flow_type: str, **kwargs):
        self.flow_type = flow_type
        steps = self._create_steps()
        super().__init__(f"credex_{flow_type}", steps)
```

### Step Definition Example

```python
Step(
    id="amount",
    type=StepType.TEXT,
    message=self._get_amount_prompt,
    validator=self._validate_amount,
    transformer=self._transform_amount
)
```

## Best Practices

1. **Message Handling**
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

## Integration

The Flow Framework integrates with:
- WhatsApp message handling through standardized Message objects
- Redis state management with atomic updates
- API services with error handling
- User authentication with token management

For more details on:
- WhatsApp integration: [WhatsApp](whatsapp.md)
- State management: [State Management](state-management.md)
- API integration: [API Integration](api-integration.md)
