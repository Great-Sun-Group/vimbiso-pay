# Flow Implementation Debug Reference

## Overview

The Flow base class (`app/core/messaging/flow.py`) provides the foundation for building progressive WhatsApp interactions with state management and step progression.

## Core Components

```
┌─────────────────────┐
│        Flow         │
├─────────────────────┤
│ - Steps            │
│ - Current Step     │
│ - State            │
└─────────────────────┘
        ▲
        │
┌─────────────────────┐
│        Step         │
├─────────────────────┤
│ - Validation       │
│ - Transformation   │
│ - Conditions       │
└─────────────────────┘
```

## Step Types

```python
class StepType(Enum):
    TEXT_INPUT = 'text_input'      # Free text input
    LIST_SELECT = 'list_select'    # List of options
    BUTTON_SELECT = 'button_select'# Quick reply buttons
```

## Common Issues & Debug Steps

### 1. State Preservation Issues

**Symptoms:**
- Lost step data
- Missing essential fields
- State corruption
- Inconsistent state

**Debug Steps:**
```python
# Check preserved fields
preserve_fields = {
    "phone",
    "authorizer_member_id",
    "issuer_member_id",
    "sender_account",
    "sender_account_id",
    "jwt_token"
}

# Verify state
for field in preserve_fields:
    if field in flow._state:
        print(f"{field}: {flow._state[field]}")
    else:
        print(f"Missing field: {field}")

# Check step data
for step in flow.steps:
    if step.id in flow._state:
        print(f"Step {step.id}: {flow._state[step.id]}")
```

### 2. Step Progression Issues

**Symptoms:**
- Stuck at step
- Invalid progression
- Skipped steps
- Condition failures

**Debug Steps:**
```python
# Check current step
current = flow.current_step
print(f"Current step: {current.id if current else None}")
print(f"Step index: {flow.current_step_index}")

# Verify conditions
if current and current.condition:
    result = current.should_execute(flow.state)
    print(f"Should execute: {result}")

# Test progression
next_step = flow.next()
print(f"Next step: {next_step.id if next_step else None}")
```

### 3. Input Processing Issues

**Symptoms:**
- Validation failures
- Transform errors
- Invalid input handling
- Type mismatches

**Debug Steps:**
```python
# Test validation
step = flow.current_step
if step:
    is_valid = step.validate(input_value)
    print(f"Input validation: {is_valid}")

# Check transformation
if step and step.transform:
    try:
        transformed = step.transform_input(input_value)
        print(f"Transformed: {transformed}")
    except Exception as e:
        print(f"Transform error: {str(e)}")
```

## Key Code Sections

### 1. State Management
```python
def _get_clean_state(self) -> Dict[str, Any]:
    """Get a clean state with essential fields"""
    clean_state = {}
    preserve_fields = {
        "phone",
        "authorizer_member_id",
        "issuer_member_id",
        "sender_account",
        "sender_account_id",
        "jwt_token"
    }

    # Add step IDs
    for step in self.steps:
        preserve_fields.add(step.id)

    # Preserve fields
    for field in preserve_fields:
        if field in self._state:
            clean_state[field] = self._state[field]

    return clean_state
```

### 2. Step Progression
```python
def next(self) -> Optional[Step]:
    """Move to next applicable step"""
    while self.current_step_index < len(self.steps) - 1:
        self.current_step_index += 1
        if self.current_step.should_execute(self._state):
            return self.current_step
    return None
```

## Improvement Recommendations

### 1. Enhanced State Validation
```python
def validate_state(self) -> bool:
    """Validate flow state integrity"""
    try:
        # Check required fields
        required = {"phone"}
        if not all(field in self._state for field in required):
            return False

        # Validate step data
        for step in self.steps:
            if step.id in self._state:
                if not step.validate(self._state[step.id]):
                    return False

        return True

    except Exception:
        return False
```

### 2. Step Recovery
```python
def recover_step(self) -> Optional[Step]:
    """Attempt to recover current step"""
    try:
        # Verify current index
        if not 0 <= self.current_step_index < len(self.steps):
            self.current_step_index = 0

        # Find last valid step
        while self.current_step_index > 0:
            if self.current_step.should_execute(self._state):
                return self.current_step
            self.current_step_index -= 1

        return self.steps[0] if self.steps else None

    except Exception:
        return None
```

## Testing Strategy

### 1. State Management Tests
```python
def test_state_preservation():
    """Test state preservation"""
    flow = TestFlow("test", steps)

    # Set initial state
    flow.state = {
        "phone": "1234567890",
        "step1": "value1",
        "extra": "should_not_preserve"
    }

    # Update state
    flow.update_state("step2", "value2")

    # Verify preservation
    assert "phone" in flow.state
    assert "step1" in flow.state
    assert "step2" in flow.state
    assert "extra" not in flow.state
```

### 2. Step Progression Tests
```python
def test_step_progression():
    """Test step progression"""
    flow = TestFlow("test", steps)

    # Test forward progression
    step1 = flow.current_step
    assert step1.id == "step1"

    step2 = flow.next()
    assert step2.id == "step2"

    # Test backward progression
    prev = flow.back()
    assert prev.id == "step1"
```

### 3. Input Processing Tests
```python
def test_input_processing():
    """Test input processing"""
    step = Step(
        id="test",
        type=StepType.TEXT_INPUT,
        stage="test",
        message="Test message",
        validation=lambda x: len(x) > 0,
        transform=lambda x: x.strip()
    )

    # Test validation
    assert step.validate("valid input")
    assert not step.validate("")

    # Test transformation
    assert step.transform_input(" test ") == "test"
