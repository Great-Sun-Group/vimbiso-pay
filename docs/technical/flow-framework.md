# Flow Framework

A reusable framework for building progressive, state-aware interactions in WhatsApp that provides type-safe message handling and standardized flow management.

## Overview

The Flow Framework provides a structured way to build complex multi-step interactions while maintaining state and ensuring proper validation at each step. It abstracts away the complexities of WhatsApp message handling and state management, allowing developers to focus on business logic.

## Core Components

### Step Types
```python
class StepType(Enum):
    TEXT_INPUT = 'text_input'          # Free text input
    LIST_SELECT = 'list_select'        # List of options
    BUTTON_SELECT = 'button_select'    # Quick reply buttons
```

### Step Definition
Each step in a flow is defined with:
- **ID**: Unique identifier for the step
- **Type**: The type of interaction (text, list, buttons)
- **Stage**: Mapping to state management stage
- **Message**: Static message or dynamic generator
- **Validation**: Optional input validation
- **Transform**: Optional input transformation
- **Condition**: Optional execution condition

```python
@dataclass
class Step:
    id: str
    type: StepType
    stage: str
    message: Union[WhatsAppMessage, Callable[[Dict[str, Any]], WhatsAppMessage]]
    validation: Optional[Callable[[Any], bool]] = None
    transform: Optional[Callable[[Any], Any]] = None
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
```

### Flow Management
The Flow class manages:
- Step progression
- State persistence
- Input validation
- Data transformation
- Conditional execution

## Key Features

### State Management
- Automatic state persistence between messages
- Type-safe state access
- State-based conditional progression
- Validation of required fields
- Safe handling of missing or malformed data

### Input Processing
- Validation before state updates
- Data transformation hooks
- Error handling and recovery
- Clear error messages

### Conditional Logic
- Step execution based on state
- Dynamic message generation
- Flow branching support
- State validation for conditions

### WhatsApp Integration
- Native WhatsApp message types
- Rich message formatting
- Interactive components
- Clean message presentation

## Real-World Example: CredEx Offer Flow

Here's how we use the framework for processing CredEx offers:

```python
class CredexOfferFlow(Flow):
    """Progressive flow for creating credex offers"""

    def _create_steps(self) -> list[Step]:
        return [
            # Step 1: Amount Input
            Step(
                id="amount",
                type=StepType.TEXT_INPUT,
                stage=StateStage.CREDEX.value,
                message=lambda state: ProgressiveInput.create_prompt(
                    "Enter amount in USD or specify denomination:",
                    [
                        "100",           # Default USD
                        "USD 100",       # Explicit USD
                        "ZWG 100",       # Zimbabwe Gold
                        "XAU 1"          # Gold
                    ],
                    state.get("phone", "")
                ),
                validation=self._validate_amount,
                transform=self._transform_amount
            ),

            # Step 2: Recipient Handle Input
            Step(
                id="handle",
                type=StepType.TEXT_INPUT,
                stage=StateStage.CREDEX.value,
                message=lambda state: ProgressiveInput.create_prompt(
                    "Enter recipient's handle:",
                    ["greatsun_ops"],
                    state.get("phone", "")
                ),
                validation=self._validate_handle,
                transform=self._transform_handle,
                condition=lambda state: self._has_valid_amount(state)
            ),

            # Step 3: Final Confirmation
            Step(
                id="confirm",
                type=StepType.BUTTON_SELECT,
                stage=StateStage.CREDEX.value,
                message=self._create_final_confirmation_message,
                condition=lambda state: self._can_show_confirmation(state)
            )
        ]
```

This flow demonstrates:
1. **Progressive Data Collection**: Amount → Handle → Confirmation
2. **Input Validation**: Amount format, handle validation
3. **Data Transformation**: Parse amounts, validate handles with API
4. **Conditional Steps**: Each step depends on previous data
5. **State Management**: Maintains data between steps
6. **Safe State Access**: Proper validation and error handling
7. **Clean Message Formatting**: Clear user prompts and confirmations

## Best Practices

### State Handling
1. Always use state.get() with defaults
2. Validate state data types and structure
3. Check for required fields
4. Handle missing or malformed data gracefully
5. Log validation failures

### Message Formatting
1. Keep prompts clear and concise
2. Show relevant examples
3. Format multi-line messages consistently
4. Handle special characters properly
5. Use proper spacing and line breaks

### Error Handling
1. Provide clear error messages
2. Log errors with context
3. Handle API errors gracefully
4. Validate service dependencies
5. Check for missing data

### Flow Design
1. Keep steps focused and simple
2. Validate data before proceeding
3. Transform data into proper formats
4. Handle state transitions cleanly
5. Log flow progression

## Benefits

1. **Maintainability**: Standardized flow structure makes code easier to maintain
2. **Type Safety**: Built-in type checking and validation
3. **Reusability**: Common patterns abstracted into reusable components
4. **Testability**: Isolated steps are easier to test
5. **Reliability**: Consistent error handling and state management
6. **User Experience**: Clean message formatting and clear prompts
7. **Data Integrity**: Safe state handling and validation

## Future Enhancements

1. **Flow Templates**: Common flow patterns as reusable templates
2. **Visual Flow Builder**: GUI for flow creation and editing
3. **Flow Analytics**: Built-in analytics and monitoring
4. **A/B Testing**: Native support for flow variations
5. **Flow Versioning**: Version control for flows
6. **Test Framework**: Automated testing for flows
7. **State Migration**: Handle state schema changes
