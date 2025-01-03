# Testing Guide

## Core Testing Patterns

1. **Validation Testing**
- Test validation state tracking
- Test attempt counting
- Test error context
- Test recovery patterns
- NO direct state access
- NO state assumptions

2. **Flow Testing**
- Test state transitions
- Test progress tracking
- Test validation state
- Test error handling
- NO state manipulation
- NO flow assumptions

3. **Error Testing**
- Test error boundaries
- Test error context
- Test recovery paths
- Test validation state
- NO error suppression
- NO state corruption

4. **State Testing**
- Test state access patterns
- Test validation tracking
- Test attempt counting
- Test error handling
- NO direct state access
- NO state assumptions

## Test Scenarios

### 1. Validation State
Every validation test verifies:
```python
validation_state = {
    "in_progress": bool,
    "error": Optional[Dict],
    "attempts": int,
    "last_attempt": Any
}
```

### 2. Flow Progress
Every flow test verifies:
```python
flow_state = {
    "step_index": int,     # Current step
    "total_steps": int,    # Total steps
    "validation": {        # Validation state
        "in_progress": bool,
        "attempts": int,
        "last_attempt": Any
    }
}
```

### 3. Error Context
Every error test verifies:
```python
error_context = {
    "type": str,          # Error type
    "message": str,       # Error message
    "details": {          # Error details
        "component": str,
        "field": str,
        "value": Any,
        "attempts": int
    }
}
```

## Test Categories

### 1. Component Testing
- Validate input handling
- Verify validation state
- Check error handling
- Test recovery paths
- NO direct state access
- NO state assumptions

### 2. Flow Testing
- Verify state transitions
- Check progress tracking
- Test validation state
- Verify error handling
- NO state manipulation
- NO flow assumptions

### 3. Integration Testing
- Test component interactions
- Verify state management
- Check error propagation
- Test recovery paths
- NO direct state access
- NO state assumptions

### 4. Error Testing
- Test error boundaries
- Verify error context
- Check recovery paths
- Test validation state
- NO error suppression
- NO state corruption

## Recovery Testing

### 1. State Recovery
Every recovery test verifies:
```python
recovery_state = {
    "type": str,          # Recovery type
    "step_id": str,       # Recovery step
    "validation": {       # Validation state
        "attempts": int,
        "last_valid": str
    }
}
```

### 2. Error Recovery
Every error recovery test verifies:
```python
error_recovery = {
    "type": str,          # Recovery type
    "message": str,       # Recovery message
    "context": {          # Recovery context
        "step_id": str,
        "valid_data": Dict,
        "validation": {
            "attempts": int,
            "last_valid": str
        }
    }
}
```

## Best Practices

1. **Validation Testing**
- Test all validation states
- Verify attempt tracking
- Check error context
- Test recovery paths
- NO state manipulation
- NO test assumptions

2. **Flow Testing**
- Test complete flows
- Verify state transitions
- Check validation state
- Test error handling
- NO state corruption
- NO flow assumptions

3. **Error Testing**
- Test all error types
- Verify error context
- Check recovery paths
- Test validation state
- NO error suppression
- NO state corruption

4. **State Testing**
- Test state access patterns
- Verify validation tracking
- Check attempt counting
- Test error handling
- NO direct state access
- NO state assumptions

## Integration

Testing integrates with:
- Component system
- Flow framework
- State management
- Error handling
- Message handling
