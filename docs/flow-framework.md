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

### Flow Processing

1. **Input Processing**
   ```python
   def process_input(self, input_data: Any) -> Optional[str]:
       step = self.current_step
       if not step:
           return None

       # Validate and transform input
       if not step.validate(input_data):
           return "Invalid input"

       # Update flow data
       self.data[step.id] = step.transform(input_data)

       # Move to next step
       self.current_index += 1

       return self.current_step.get_message(self.data) if self.current_step else None
   ```

2. **State Management**
   ```python
   def get_state(self) -> Dict[str, Any]:
       return {
           "id": self.id,
           "step": self.current_index,
           "data": self.data
       }

   def set_state(self, state: Dict[str, Any]) -> None:
       self.data = state.get("data", {})
       self.current_index = state.get("step", 0)
   ```

## Practical Examples

### Member Registration Flow

```python
class MemberFlow(Flow):
    def _create_steps(self) -> List[Step]:
        return [
            Step(
                id="first_name",
                type=StepType.TEXT,
                message=self._get_first_name_prompt,
                validator=self._validate_name,
                transformer=lambda value: {"first_name": value.strip()}
            ),
            Step(
                id="last_name",
                type=StepType.TEXT,
                message=self._get_last_name_prompt,
                validator=self._validate_name,
                transformer=lambda value: {"last_name": value.strip()}
            ),
            Step(
                id="confirm",
                type=StepType.BUTTON,
                message=self._create_confirmation_message,
                validator=self._validate_button_response
            )
        ]
```

### Credex Transaction Flow

```python
class CredexFlow(Flow):
    def _create_steps(self) -> List[Step]:
        return [
            Step(
                id="amount",
                type=StepType.TEXT,
                message=self._get_amount_prompt,
                validator=self._validate_amount,
                transformer=self._transform_amount
            ),
            Step(
                id="handle",
                type=StepType.TEXT,
                message="Enter recipient handle:",
                validator=self._validate_handle,
                transformer=self._transform_handle
            ),
            Step(
                id="confirm",
                type=StepType.BUTTON,
                message=self._create_confirmation_message,
                validator=self._validate_button_response
            )
        ]
```

## Best Practices

1. **Step Design**
   - Keep steps focused on single pieces of information
   - Use appropriate step types for the data being collected
   - Provide clear validation feedback
   - Transform data into consistent formats

2. **State Management**
   - Store minimal required data
   - Clean up completed flow data
   - Handle timeouts gracefully
   - Preserve critical state information

3. **Error Handling**
   - Validate all inputs thoroughly
   - Provide clear error messages
   - Handle edge cases explicitly
   - Log validation failures

4. **Message Design**
   - Use clear, concise prompts
   - Provide example inputs where helpful
   - Support multiple input formats
   - Include navigation options

## Architectural Patterns

### 1. Message Handling
```python
def _get_prompt(self, state: Dict[str, Any]) -> Dict[str, Any]:
    """Get prompt message using WhatsAppMessage"""
    return WhatsAppMessage.create_text(
        self.data.get("mobile_number"),
        "Enter value:"
    )
```

- Use WhatsAppMessage consistently for all responses
- Follow WhatsApp Cloud API format strictly
- Handle character limits (4096 for text, 20 for buttons)
- Support all message types (text, button, list)
- Validate message format before sending

### 2. Template Hierarchy
1. **String Templates** (screens.py)
   ```python
   BALANCE = """*💰 SECURED BALANCES*
   {securedNetBalancesByDenom}

   *📊 NET ASSETS*
   {netCredexAssetsInDefaultDenom}
   {tier_limit_display}"""
   ```
   - Basic text templates
   - Format strings only
   - No message creation logic
   - Reusable across flows

2. **Message Builders** (templates.py)
   ```python
   class ProgressiveInput:
       @staticmethod
       def create_prompt(text: str, examples: List[str], recipient: str) -> Message:
           return Message(
               recipient=MessageRecipient(phone_number=recipient),
               content=TextContent(body=format_prompt(text, examples))
           )
   ```
   - WhatsAppMessage creation
   - Common message patterns
   - Reusable components
   - Format validation

3. **Flow Messages**
   ```python
   def _create_confirmation(self, state: Dict[str, Any]) -> Dict[str, Any]:
       return WhatsAppMessage.create_button(
           to=self.data.get("mobile_number"),
           text=format_confirmation(state),
           buttons=[{"id": "confirm", "title": "Confirm"}]
       )
   ```
   - Flow-specific formatting
   - State-aware messages
   - Validation feedback
   - Error messages

### 3. State Management
```python
def _update_state(self, response: Dict[str, Any]) -> None:
    """Update state preserving critical data"""
    try:
        current_state = self.user.state.state
        new_state = {
            "profile": current_state.get("profile", {}),
            "current_account": current_state.get("current_account"),
            "jwt_token": current_state.get("jwt_token")
        }

        # Update with new data
        if "data" in response:
            if "data" in new_state["profile"]:
                new_state["profile"]["data"].update(response["data"])
            else:
                new_state["profile"]["data"] = response["data"]

        # Atomic update
        self.user.state.update_state(new_state, "state_update")
    except Exception as e:
        logger.error(f"State update error: {str(e)}")
        raise ValueError("Failed to update state")
```

- Preserve critical state data
- Atomic state updates
- Error recovery
- Clean expired data
- State validation

### 4. Error Handling
```python
def complete(self) -> Dict[str, Any]:
    """Complete flow with error handling"""
    try:
        if not self.validate_state():
            raise ValueError("Invalid state")

        result = self._process_completion()
        self._update_state(result)

        return WhatsAppMessage.create_text(
            self.data.get("mobile_number"),
            "✅ Operation completed successfully"
        )
    except Exception as e:
        logger.error(f"Flow completion error: {str(e)}")
        return WhatsAppMessage.create_text(
            self.data.get("mobile_number"),
            f"❌ {str(e)}"
        )
```

- Consistent error messages
- Proper logging
- State recovery
- User feedback
- Error tracking

## Integration

The Flow Framework integrates with:
- WhatsApp message handling through WhatsAppMessage
- Redis state management with atomic updates
- API services with error handling
- User authentication with token management

For more details on:
- WhatsApp integration: [WhatsApp](whatsapp.md)
- State management: [State Management](state-management.md)
- API integration: [API Integration](api-integration.md)
