# Testing Guide

## Overview

VimbisoPay provides testing infrastructure for both WhatsApp interactions and API integrations.

## Mock WhatsApp Interface

For detailed WhatsApp testing, see [WhatsApp Integration](whatsapp.md).

### Components
```
mock/
├── server.py          # Mock webhook server
├── cli.py            # CLI interface
├── whatsapp_utils.py # Shared utilities
├── scripts/          # Client-side scripts
│   ├── handlers.js   # Message handlers
│   ├── main.js      # Core functionality
│   └── ui.js        # Interface updates
└── styles/          # UI styling
    └── main.css     # Core styles
```

### CLI Usage
```bash
# Text message
./mock/cli.py "hi"

# Menu option selection
./mock/cli.py --type interactive "handleactionoffercredex"

# Flow navigation
./mock/cli.py --type interactive "flow:MAKE_SECURE_OFFER"

# Button response
./mock/cli.py --type button "accept_offer_123"

# Progressive input
./mock/cli.py --type interactive "form:amount=100,recipientAccountHandle=@user123"
```

### Web Interface
Access at http://localhost:8001
- WhatsApp-style chat interface
- Interactive menu options
- Flow navigation
- Real-time message display
- Environment switching (local/staging)
- Progressive input support

## Common Test Scenarios

### 1. User Registration Flow
```bash
# Start registration
./mock/cli.py "hi"

# Enter first name
./mock/cli.py "John"

# Enter last name
./mock/cli.py "Doe"

# Confirm registration
./mock/cli.py --type button "confirm_action"

# Verify validation state
./mock/cli.py --type debug "get_validation_state"
# Expected output:
{
    "flow_data": {
        "active_component": {
            "type": "registration",
            "validation": {
                "attempts": 1,
                "last_attempt": "2024-01-01T00:00:00Z",
                "in_progress": false,
                "error": null
            }
        }
    }
}
```

### 2. Transaction Flows
```bash
# Quick command with validation tracking
./mock/cli.py "0.5=>handle"

# Through menu with progress tracking
./mock/cli.py --type interactive "handleactionoffercredex"
# Expected output includes progress:
"Step 1 of 3: Enter amount"

# Progressive input with validation
./mock/cli.py --type interactive "form:amount=0.5,handle=user123"
# Verify validation state:
{
    "flow_data": {
        "active_component": {
            "type": "amount_input",
            "validation": {
                "attempts": 1,
                "last_attempt": "0.5",
                "in_progress": false,
                "error": null
            }
        }
    }
}

# Flow navigation with progress
./mock/cli.py --type interactive "flow:MAKE_SECURE_OFFER"
```

### 3. Menu Navigation
```bash
# Show menu with validation
./mock/cli.py "menu"

# Select options with tracking
./mock/cli.py --type interactive "handleactiontransactions"
```

## Message Types

### 1. Text Messages
```bash
# Basic text with validation
./mock/cli.py "Hello"

# Quick commands with tracking
./mock/cli.py "0.5=>handle"  # Secured credex
./mock/cli.py "0.5->handle"  # Unsecured credex
```

### 2. Interactive Messages
```bash
# Menu options with validation
./mock/cli.py --type interactive "handleactionoffercredex"
./mock/cli.py --type interactive "handleactiontransactions"

# Flow navigation with progress
./mock/cli.py --type interactive "flow:MEMBER_SIGNUP"
./mock/cli.py --type interactive "flow:MAKE_SECURE_OFFER"

# Progressive input with validation
./mock/cli.py --type interactive "form:field1=value1,field2=value2"
```

### 3. Button Responses
```bash
./mock/cli.py --type button "accept_offer_123"
./mock/cli.py --type button "decline_offer_123"
./mock/cli.py --type button "confirm_action"
```

## Error and Recovery Testing

### Common Scenarios
```bash
# Invalid menu option with validation tracking
./mock/cli.py --type interactive "invalid_option"
# Verify validation state:
{
    "flow_data": {
        "active_component": {
            "type": "menu_input",
            "validation": {
                "attempts": 1,
                "last_attempt": "invalid_option",
                "in_progress": false,
                "error": {
                    "message": "Invalid menu option",
                    "details": {
                        "value": "invalid_option",
                        "valid_options": ["offer", "ledger"]
                    }
                }
            }
        }
    }
}

# Expired session with tracking
./mock/cli.py --type interactive "handleactionoffercredex"  # After timeout

# Malformed command with validation
./mock/cli.py "0.5=>"  # Missing handle

# Invalid progressive input with tracking
./mock/cli.py --type interactive "form:amount=invalid"

# Flow validation errors with state
./mock/cli.py "not_a_name"  # During name input step

# Recovery scenarios with validation
./mock/cli.py --type interactive "flow:MAKE_SECURE_OFFER"  # After error
./mock/cli.py --type interactive "form:amount=0.5"  # Resume from last valid state
```

### Error and Recovery Format
```python
{
    "error": "Error description",
    "details": {
        "field": "Error details"
    },
    "validation": {
        "attempts": int,
        "last_attempt": str,
        "in_progress": bool,
        "error": Optional[Dict]
    },
    "recovery": {
        "type": "step_recovery",  # or "path_recovery"
        "message": "Recovered to previous valid step",
        "context": {
            "step_id": "amount",
            "valid_data": {...},
            "validation_state": {
                "attempts": int,
                "last_valid": str
            }
        }
    }
}
```

## Best Practices

1. **Flow Testing**
   - Test complete flows end-to-end
   - Verify core state transitions
   - Test validation state tracking
   - Test progress tracking
   - Check attempt tracking
   - Verify error context
   - Test smart recovery
   - Test timeouts
   - Verify data transformation

2. **Progressive Input Testing**
   - Test validation state tracking
   - Test attempt tracking
   - Verify error messages
   - Test data transformations
   - Check flow_data.data state
   - Test input examples
   - Verify progress tracking

3. **Message Testing**
   - Test validation state tracking
   - Test attempt tracking
   - Test all message types
   - Verify formatting
   - Check interactions
   - Validate responses
   - Test WhatsApp limits

4. **Environment Management**
   - Use appropriate target
   - Clean up test data
   - Reset validation state
   - Reset attempt counters
   - Reset state between tests
   - Verify Redis instances

5. **Recovery Testing**
   - Test validation state recovery
   - Test attempt counter recovery
   - Test context-aware recovery
   - Check multi-step recovery
   - Verify error messages
   - Test recovery paths
   - Check recovery logging

## Test Cases

### 1. Validation State Testing
```python
def test_validation_state_tracking():
    """Test validation state tracking"""
    # Initialize test state
    state_manager = StateManager("test")
    component = AmountInput()

    # Test initial state
    assert component.validation_state == {
        "in_progress": False,
        "error": None,
        "attempts": 0,
        "last_attempt": None
    }

    # Test invalid input
    result = component.validate("invalid")
    assert not result.valid
    assert component.validation_state["attempts"] == 1
    assert component.validation_state["last_attempt"] == "invalid"
    assert component.validation_state["error"] is not None

    # Test valid input
    result = component.validate("100.00")
    assert result.valid
    assert component.validation_state["attempts"] == 2
    assert component.validation_state["last_attempt"] == "100.00"
    assert component.validation_state["error"] is None
```

### 2. Progress Tracking Testing
```python
def test_progress_tracking():
    """Test flow progress tracking"""
    # Initialize test state
    state_manager = StateManager("test")
    flow = OfferFlow(messaging_service)

    # Start flow
    flow.start(state_manager)
    flow_state = state_manager.get_flow_state()
    assert flow_state["step_index"] == 0
    assert flow_state["total_steps"] == 3

    # Process first step
    result = flow.process_step(state_manager, "amount", "100.00")
    flow_state = state_manager.get_flow_state()
    assert flow_state["step_index"] == 1
    assert "Step 2 of 3" in result["message"]

    # Complete flow
    result = flow.process_step(state_manager, "confirm", True)
    flow_state = state_manager.get_flow_state()
    assert flow_state["step_index"] == 3
    assert "Step 3 of 3" in result["message"]
```

### 3. Error Context Testing
```python
def test_error_context():
    """Test error context in validation"""
    # Initialize test state
    state_manager = StateManager("test")
    component = AmountInput()

    # Test validation error
    result = component.validate("invalid")
    assert not result.valid
    assert result.error["details"]["attempts"] == 1
    assert result.error["details"]["value"] == "invalid"
    assert "Invalid amount format" in result.error["message"]

    # Test flow error
    try:
        flow.process_step(state_manager, "invalid_step", "value")
    except FlowException as e:
        assert e.data["step"] == "invalid_step"
        assert e.data["attempts"] == 1
        assert "Invalid step" in str(e)
```

For more details on:
- WhatsApp integration: [WhatsApp Integration](whatsapp.md)
- Flow framework: [Flow Framework](flow-framework.md)
- State management: [State Management](state-management.md)
- API integration: [API Integration](api-integration.md)
- Security testing: [Security](security.md)
