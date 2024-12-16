# Flow Examples Debug Reference

## Registration Flow Example

The Registration Flow (`app/services/whatsapp/handlers/member/registration_flow.py`) demonstrates a typical progressive flow implementation.

### Flow Structure

```
┌─────────────────────┐
│  Registration Flow  │
├─────────────────────┤
│ Step 1: First Name │
│ Step 2: Last Name  │
│ Step 3: Confirm    │
└─────────────────────┘
```

### Step Configuration

```python
# Step 1: First Name Input
Step(
    id="first_name",
    type=StepType.TEXT_INPUT,
    stage=StateStage.REGISTRATION.value,
    message=lambda state: self._create_text_prompt(...),
    validation=lambda value: self._validate_name(value, "First name")[0],
    transform=lambda value: {"first_name": value.strip()}
)

# Step 2: Last Name Input
Step(
    id="last_name",
    type=StepType.TEXT_INPUT,
    stage=StateStage.REGISTRATION.value,
    message=lambda state: self._create_text_prompt(...),
    validation=lambda value: self._validate_name(value, "Last name")[0],
    transform=lambda value: {"last_name": value.strip()},
    condition=lambda state: bool(state.get("first_name"))
)

# Step 3: Confirmation
Step(
    id="confirm",
    type=StepType.BUTTON_SELECT,
    stage=StateStage.REGISTRATION.value,
    message=self._create_confirmation_message,
    condition=lambda state: self._has_valid_registration(state),
    transform=lambda value: {"confirmed": value == "confirm_registration"},
    validation=lambda value: value == "confirm_registration"
)
```

## Common Issues & Debug Steps

### 1. Input Validation Issues

**Symptoms:**
- Invalid input accepted
- Valid input rejected
- Inconsistent validation
- Missing error messages

**Debug Steps:**
```python
def debug_name_validation(name: str, field: str) -> None:
    """Debug name validation"""
    # Test basic validation
    valid, msg = flow._validate_name(name, field)
    print(f"Input: '{name}'")
    print(f"Valid: {valid}")
    print(f"Message: {msg}")

    # Check specific rules
    print("\nValidation Rules:")
    print(f"Length (3-50): {3 <= len(name) <= 50}")
    print(f"Only letters: {name.replace(' ', '').isalpha()}")
    print(f"Not empty: {bool(name.strip())}")
```

### 2. State Transformation Issues

**Symptoms:**
- Missing data in state
- Incorrect data format
- Lost transformations
- State corruption

**Debug Steps:**
```python
def debug_state_transform(flow: RegistrationFlow) -> None:
    """Debug state transformations"""
    # Check first name
    first_name_state = flow.state.get("first_name", {})
    print(f"First Name State: {first_name_state}")

    # Check last name
    last_name_state = flow.state.get("last_name", {})
    print(f"Last Name State: {last_name_state}")

    # Verify format
    for key, value in flow.state.items():
        if isinstance(value, dict):
            print(f"\nKey: {key}")
            print(f"Value type: {type(value)}")
            print(f"Value content: {value}")
```

### 3. Flow Progression Issues

**Symptoms:**
- Stuck at step
- Skipped validation
- Missing conditions
- Invalid transitions

**Debug Steps:**
```python
def debug_flow_progression(flow: RegistrationFlow) -> None:
    """Debug flow progression"""
    # Check current step
    current = flow.current_step
    print(f"Current Step: {current.id if current else None}")

    # Check conditions
    if current and current.condition:
        result = current.should_execute(flow.state)
        print(f"Should Execute: {result}")

    # Test next step
    next_step = flow.next()
    print(f"Next Step: {next_step.id if next_step else None}")
```

## Implementation Patterns

### 1. Progressive Validation

```python
def _has_valid_registration(self, state: Dict[str, Any]) -> bool:
    """Progressive validation pattern"""
    # Extract values
    first_name = state.get("first_name", {}).get("first_name", "")
    last_name = state.get("last_name", {}).get("last_name", "")

    # Revalidate all fields
    first_valid, _ = self._validate_name(first_name, "First name")
    last_valid, _ = self._validate_name(last_name, "Last name")

    return first_valid and last_valid
```

### 2. State-Aware Messages

```python
def _create_confirmation_message(self, state: Dict[str, Any]) -> WhatsAppMessage:
    """State-aware message pattern"""
    return {
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": (
                    f"✅ Please confirm your registration details:\n\n"
                    f"First Name: {state.get('first_name', {}).get('first_name', '')}\n"
                    f"Last Name: {state.get('last_name', {}).get('last_name', '')}\n"
                )
            }
        }
    }
```

## Testing Strategy

### 1. Input Validation Tests

```python
def test_name_validation():
    """Test name validation"""
    flow = RegistrationFlow("test", [])

    # Test valid cases
    assert flow._validate_name("John", "First name")[0]
    assert flow._validate_name("Mary Jane", "First name")[0]

    # Test invalid cases
    assert not flow._validate_name("", "First name")[0]  # Empty
    assert not flow._validate_name("Jo", "First name")[0]  # Too short
    assert not flow._validate_name("John123", "First name")[0]  # Numbers
```

### 2. Flow Progression Tests

```python
def test_flow_progression():
    """Test flow progression"""
    flow = RegistrationFlow("test", [])

    # Test first name step
    assert flow.current_step.id == "first_name"
    flow.update_state("first_name", {"first_name": "John"})

    # Test last name step
    next_step = flow.next()
    assert next_step.id == "last_name"
    flow.update_state("last_name", {"last_name": "Doe"})

    # Test confirmation step
    next_step = flow.next()
    assert next_step.id == "confirm"
```

### 3. State Management Tests

```python
def test_state_management():
    """Test state management"""
    flow = RegistrationFlow("test", [])

    # Test state updates
    flow.update_state("first_name", {"first_name": "John"})
    assert flow.state["first_name"]["first_name"] == "John"

    # Test state preservation
    flow.state = {"new": "state"}
    assert "first_name" in flow.state  # Should preserve step data
