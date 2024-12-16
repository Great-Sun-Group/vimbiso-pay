# Mock CLI Debug Guide

This guide explains how to use the mock CLI interface (`mock/cli.py`) to debug WhatsApp flows while monitoring server logs.

## Setup

1. Start the development server:
```bash
make dev
```

This will:
- Start the Django application
- Start the mock WhatsApp server
- Show server logs in the terminal

## CLI Usage

### Basic Message Types

1. **Text Messages**
```bash
# Basic text
./mock/cli.py "Hello"

# Quick commands
./mock/cli.py "0.5=>handle"  # Secured credex
./mock/cli.py "0.5->handle"  # Unsecured credex
```

2. **Menu Navigation**
```bash
# Select menu option
./mock/cli.py --type interactive "handleactionoffercredex"

# Start flow
./mock/cli.py --type interactive "flow:MAKE_SECURE_OFFER"
```

3. **Button Responses**
```bash
# Confirm action
./mock/cli.py --type button "confirm_registration"

# Accept offer
./mock/cli.py --type button "accept_offer_123"
```

## Debugging Flows

### 1. Registration Flow

```bash
# Start registration
./mock/cli.py "hi"

# Watch logs for:
- State initialization
- Flow creation
- Step progression

# Enter first name
./mock/cli.py "John"

# Watch logs for:
- Input validation
- State updates
- Step transition

# Enter last name
./mock/cli.py "Doe"

# Watch logs for:
- Data transformation
- State preservation
- Confirmation setup

# Confirm registration
./mock/cli.py --type button "confirm_registration"

# Watch logs for:
- Final validation
- State completion
- Flow cleanup
```

### 2. CredEx Offer Flow

```bash
# Start offer flow
./mock/cli.py --type interactive "flow:MAKE_SECURE_OFFER"

# Watch logs for:
- Service initialization
- Profile loading
- State setup

# Enter amount
./mock/cli.py "100"

# Watch logs for:
- Amount validation
- Currency handling
- State updates

# Enter recipient
./mock/cli.py "@recipient"

# Watch logs for:
- Handle validation
- Account lookup
- State preservation

# Confirm offer
./mock/cli.py --type button "confirm"

# Watch logs for:
- Final validation
- Transaction creation
- State cleanup
```

## Log Analysis

### 1. State Changes

Watch for these log patterns:
```
Current state: {...}  # State before update
Updated state: {...}  # State after update
Flow state: {...}     # Flow-specific state
```

Key things to monitor:
- State structure integrity
- Field preservation
- Transition validity
- Error handling

### 2. Flow Progression

Watch for these log patterns:
```
Current step: step_id      # Current step info
Extracted input: value     # Input processing
Validation result: bool    # Input validation
Next step: next_step_id    # Step progression
```

Key things to monitor:
- Step sequence
- Input handling
- Validation logic
- Transition rules

### 3. Error Handling

Watch for these log patterns:
```
Error: message            # Error details
Validation failed: reason # Validation errors
Recovery attempt: status  # Recovery process
State reset: user_id      # State resets
```

Key things to monitor:
- Error types
- Recovery attempts
- State preservation
- User experience

## Common Debug Scenarios

### 1. Invalid Input

```bash
# Send invalid input
./mock/cli.py "inv@lid"

# Watch logs for:
- Validation failure
- Error message
- State preservation
- Recovery process
```

### 2. Flow Recovery

```bash
# Interrupt flow
Ctrl+C during flow

# Restart flow
./mock/cli.py --type interactive "flow:PREVIOUS_FLOW"

# Watch logs for:
- State recovery
- Flow restoration
- Data preservation
```

### 3. State Corruption

```bash
# Force invalid state
./mock/cli.py --type interactive "invalid_action"

# Watch logs for:
- Error detection
- State validation
- Recovery attempt
- Error response
```

## Best Practices

1. **Systematic Testing**
   - Test each flow step by step
   - Verify state after each action
   - Check error handling
   - Validate recovery

2. **Log Analysis**
   - Monitor state changes
   - Track flow progression
   - Watch for errors
   - Verify recovery

3. **Error Testing**
   - Test invalid inputs
   - Interrupt flows
   - Corrupt states
   - Verify recovery

4. **Flow Verification**
   - Check step sequence
   - Verify data preservation
   - Test conditions
   - Validate outcomes
