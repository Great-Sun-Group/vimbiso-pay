# Flow Handler Debug Reference

## Overview

The Flow Handler (`app/core/messaging/flow_handler.py`) manages WhatsApp interaction flows, handling message routing, state transitions, and flow progression.

## Core Components

```
┌─────────────────────┐
│    Flow Handler     │
├─────────────────────┤
│ - Registered Flows  │
│ - Service Injectors │
│ - State Service     │
└─────────────────────┘
```

### Key Features
- Flow registration and instantiation
- Message handling and routing
- Input extraction and validation
- State synchronization
- Error handling

## Common Issues & Debug Steps

### 1. Flow Registration Issues

**Symptoms:**
- Flow not found errors
- Service injection failures
- Invalid flow state

**Debug Steps:**
```python
# Check registered flows
print(f"Registered flows: {handler._registered_flows.keys()}")

# Verify service injectors
print(f"Service injectors: {handler._service_injectors.keys()}")

# Check flow initialization
flow = handler.get_flow(flow_id)
print(f"Flow instance: {flow}")
print(f"Flow state: {flow.state}")
```

### 2. Message Handling Issues

**Symptoms:**
- Input extraction failures
- Validation errors
- Step progression issues

**Debug Steps:**
```python
# Log incoming message
logger.debug(f"Message content: {message}")

# Check input extraction
input_value = handler._extract_input(message, step_type)
logger.debug(f"Extracted input: {input_value}")

# Verify step validation
if not current_step.validate(input_value):
    logger.error(f"Validation failed for input: {input_value}")
```

### 3. State Synchronization Issues

**Symptoms:**
- Lost flow state
- Incorrect step progression
- Profile/account data missing

**Debug Steps:**
```python
# Check flow data in state
flow_data = state.get("flow_data", {})
print(f"Flow ID: {flow_data.get('id')}")
print(f"Current step: {flow_data.get('current_step')}")
print(f"Flow state: {flow_data.get('data')}")

# Verify profile preservation
if "profile" in state:
    print(f"Profile data: {state['profile']}")
if "current_account" in state:
    print(f"Account data: {state['current_account']}")
```

## Key Code Sections

### 1. Flow Registration
```python
def register_flow(self, flow_class: Type[Flow], service_injector: Optional[callable] = None) -> None:
    """Register a flow class and optional service injector"""
    # Register both by class name and flow ID for flexibility
    self._registered_flows[flow_class.__name__] = flow_class
    if hasattr(flow_class, 'FLOW_ID'):
        self._registered_flows[flow_class.FLOW_ID] = flow_class
        if service_injector:
            self._service_injectors[flow_class.FLOW_ID] = service_injector
```

### 2. Input Extraction
```python
def _extract_input(self, message: Dict[str, Any], step_type: StepType) -> Any:
    """Extract input value from message based on step type"""
    if step_type == StepType.TEXT_INPUT:
        messages = (
            message.get("entry", [{}])[0]
            .get("changes", [{}])[0]
            .get("value", {})
            .get("messages", [{}])
        )
        if messages:
            return messages[0].get("text", {}).get("body", "")
```

### 3. State Updates
```python
# Update state with flow data
state["flow_data"] = {
    "id": flow.id,
    "current_step": flow.current_step_index,
    "data": flow.state
}

# Preserve profile and account data
if "profile" in state:
    state["flow_data"]["data"]["profile"] = state["profile"]
if "current_account" in state:
    state["flow_data"]["data"]["current_account"] = state["current_account"]
```

## Improvement Recommendations

### 1. Enhanced Error Recovery
```python
def recover_flow_state(self, user_id: str) -> bool:
    """Attempt to recover corrupted flow state"""
    try:
        state = self.state_service.get_state(user_id)
        flow_data = state.get("flow_data", {})

        if not flow_data:
            logger.error("No flow data to recover")
            return False

        # Attempt to recreate flow
        flow = self.get_flow(flow_data.get("id"))
        if not flow:
            logger.error("Could not recreate flow")
            return False

        # Restore state and verify
        flow.state = flow_data.get("data", {})
        if not flow.validate_state():
            logger.error("Invalid flow state")
            return False

        return True

    except Exception as e:
        logger.error(f"Flow recovery failed: {str(e)}")
        return False
```

### 2. Input Validation Enhancement
```python
def validate_message_format(self, message: Dict[str, Any]) -> bool:
    """Validate incoming message format"""
    required_fields = {
        "text": ["body"],
        "interactive": ["type"],
        "template": ["name", "language"]
    }

    msg_type = message.get("type")
    if not msg_type:
        return False

    fields = required_fields.get(msg_type, [])
    return all(
        message.get(field) is not None
        for field in fields
    )
```

## Testing Strategy

### 1. Flow Registration Tests
```python
def test_flow_registration():
    """Test flow registration"""
    handler = FlowHandler(state_service)

    # Register test flow
    class TestFlow(Flow):
        FLOW_ID = "test_flow"

    handler.register_flow(TestFlow)

    # Verify registration
    assert "test_flow" in handler._registered_flows
    assert TestFlow.__name__ in handler._registered_flows
```

### 2. Message Handling Tests
```python
def test_message_handling():
    """Test message handling"""
    handler = FlowHandler(state_service)

    # Test text input
    message = {
        "type": "text",
        "text": {"body": "test input"}
    }

    result = handler._extract_input(
        message,
        StepType.TEXT_INPUT
    )
    assert result == "test input"
```

### 3. State Management Tests
```python
def test_state_updates():
    """Test state updates"""
    handler = FlowHandler(state_service)

    # Start flow
    flow = handler.start_flow("test_flow", "user123")

    # Verify state
    state = state_service.get_state("user123")
    assert "flow_data" in state
    assert state["flow_data"]["id"] == "test_flow"
