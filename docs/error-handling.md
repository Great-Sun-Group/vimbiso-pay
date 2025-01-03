# Error Handling

## Core Principles

1. **Clear Error Boundaries**
- Component errors stay in components
- Flow errors stay in flows
- System errors at top level
- NO mixed error types
- NO error propagation
- NO error recovery

2. **Simple Error Structure**
- Minimal nesting
- Clear error types
- Standard messages
- NO complex hierarchies
- NO redundant wrapping
- NO state duplication

3. **Standardized Context**
- Error type (required)
- Clear message (required)
- Relevant details (optional)
- NO sensitive data
- NO mixed contexts
- NO redundant info

4. **Central Management**
- Single error handler
- Standard responses
- Clear logging
- NO manual handling
- NO local recovery
- NO state fixing

## Error Patterns

### 1. Component Errors
```python
{
    "type": "component",
    "message": str,        # User-facing message
    "details": {
        "component": str,  # Component type
        "field": str,     # Invalid field
        "value": Any,     # Invalid value
        "attempts": int   # Validation attempts
    }
}
```

### 2. Flow Errors
```python
{
    "type": "flow",
    "message": str,     # User-facing message
    "details": {
        "step": str,    # Current step
        "action": str,  # Failed action
        "data": dict,   # Relevant data
        "attempts": int # Flow attempts
    }
}
```

### 3. System Errors
```python
{
    "type": "system",
    "message": str,     # System message
    "details": {
        "code": str,    # Error code
        "service": str, # Failed service
        "action": str,  # Failed action
        "attempts": int # Operation attempts
    }
}
```

## Error Context

### 1. Validation Context
Every error includes validation state:
```python
"validation": {
    "in_progress": bool,
    "attempts": int,
    "last_attempt": datetime,
    "error": {
        "message": str,
        "details": dict
    }
}
```

### 2. Operation Context
Every error includes operation details:
```python
"operation": {
    "type": str,      # Operation type
    "service": str,   # Service name
    "action": str,    # Action name
    "attempts": int   # Attempt count
}
```

## Best Practices

1. **Error Creation**
- Use ErrorHandler methods
- Include validation state
- Track all attempts
- NO manual error objects
- NO mixed error types
- NO sensitive data

2. **Error Handling**
- Handle at appropriate level
- Include validation context
- Track all attempts
- NO error propagation
- NO local recovery
- NO state fixing

3. **Error Response**
- Use standard format
- Include validation state
- Track attempts
- NO nested wrappers
- NO redundant data
- NO state duplication

4. **Error Logging**
- Include validation state
- Track all attempts
- Add operation context
- NO sensitive data
- NO redundant info
- NO manual logging

## Integration

The error system integrates with:
- Component validation
- Flow management
- State updates
- API responses
- Message handling

For more details on:
- Components: [Components](components.md)
- Flow Framework: [Flow Framework](flow-framework.md)
- State Management: [State Management](state-management.md)
