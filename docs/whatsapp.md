# WhatsApp Integration

## Core Patterns

1. **Message Handling**
- Messages processed through state_manager
- Validation tracking on all operations
- Error context for failures
- NO direct state access
- NO manual validation
- NO state passing

2. **Template Management**
- Templates organized by domain
- Validation through state updates
- Error tracking on all operations
- NO direct data access
- NO manual validation
- NO state duplication

3. **Flow Integration**
- Flow state managed through updates
- Progress tracking on all steps
- Validation state for all operations
- NO direct state access
- NO manual validation
- NO state passing

4. **Error Handling**
- Error boundaries for all operations
- Validation state in all errors
- Attempt tracking for recovery
- NO direct error handling
- NO manual recovery
- NO state corruption

## Message Patterns

### 1. Message State
Every message includes:
```python
message_state = {
    "type": str,          # Message type
    "validation": {       # Validation state
        "in_progress": bool,
        "attempts": int,
        "last_attempt": Any,
        "error": Optional[Dict]
    }
}
```

### 2. Template State
Every template includes:
```python
template_state = {
    "name": str,          # Template name
    "validation": {       # Validation state
        "in_progress": bool,
        "attempts": int,
        "last_attempt": Any,
        "error": Optional[Dict]
    }
}
```

### 3. Flow State
Every flow includes:
```python
flow_state = {
    "step": str,          # Current step
    "validation": {       # Validation state
        "in_progress": bool,
        "attempts": int,
        "last_attempt": Any,
        "error": Optional[Dict]
    }
}
```

## Testing Patterns

### 1. Message Testing
Every message test verifies:
- Message validation state
- Attempt tracking
- Error context
- Recovery paths
- NO direct state access
- NO state assumptions

### 2. Template Testing
Every template test verifies:
- Template validation state
- Attempt tracking
- Error context
- Recovery paths
- NO direct state access
- NO state assumptions

### 3. Flow Testing
Every flow test verifies:
- Flow validation state
- Progress tracking
- Error context
- Recovery paths
- NO direct state access
- NO state assumptions

## Best Practices

1. **Message Handling**
- Use proper accessor methods
- Track validation state
- Include error context
- NO direct state access
- NO manual validation
- NO state passing

2. **Template Management**
- Use proper accessor methods
- Track validation state
- Include error context
- NO direct state access
- NO manual validation
- NO state passing

3. **Flow Integration**
- Use proper accessor methods
- Track validation state
- Include error context
- NO direct state access
- NO manual validation
- NO state passing

4. **Error Handling**
- Use proper error boundaries
- Track validation state
- Include error context
- NO direct error handling
- NO manual recovery
- NO state corruption

## Mock Testing

### 1. Test Categories
- Message validation tests
- Template validation tests
- Flow validation tests
- Error recovery tests
- NO direct state access
- NO state assumptions

### 2. Test Patterns
Every test verifies:
```python
test_state = {
    "validation": {       # Validation state
        "in_progress": bool,
        "attempts": int,
        "last_attempt": Any,
        "error": Optional[Dict]
    },
    "recovery": {         # Recovery state
        "type": str,
        "attempts": int,
        "last_valid": str
    }
}
```

### 3. Error Testing
Every error test verifies:
```python
error_state = {
    "type": str,          # Error type
    "validation": {       # Validation state
        "in_progress": bool,
        "attempts": int,
        "last_attempt": Any,
        "error": Optional[Dict]
    },
    "recovery": {         # Recovery state
        "type": str,
        "attempts": int,
        "last_valid": str
    }
}
```

## Integration

WhatsApp integration works with:
- Flow framework
- State management
- Error handling
- Message templates
- API services

For more details on:
- Flow Framework: [Flow Framework](flow-framework.md)
- State Management: [State Management](state-management.md)
- API Integration: [API Integration](api-integration.md)
- Security: [Security](security.md)
