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

## Error Types

### 1. Component Errors
```python
{
    "type": "component",
    "message": str,  # User-facing message
    "details": {     # Optional context
        "component": str,  # Component type
        "field": str,     # Invalid field
        "value": Any      # Invalid value
    }
}
```

### 2. Flow Errors
```python
{
    "type": "flow",
    "message": str,  # User-facing message
    "details": {     # Optional context
        "step": str,    # Current step
        "action": str,  # Failed action
        "data": dict    # Relevant data
    }
}
```

### 3. System Errors
```python
{
    "type": "system",
    "message": str,  # System message
    "details": {     # Optional context
        "code": str,    # Error code
        "service": str, # Failed service
        "action": str   # Failed action
    }
}
```

## Implementation

### 1. Error Handler
```python
class ErrorHandler:
    """Central error handling"""

    @classmethod
    def handle_error(
        cls,
        error: Exception,
        error_type: str,
        message: str,
        details: Optional[Dict] = None
    ) -> Dict:
        """Handle any error type"""
        return {
            "type": error_type,
            "message": message,
            "details": details or {}
        }

    @classmethod
    def handle_component_error(
        cls,
        component: str,
        field: str,
        value: Any,
        message: str
    ) -> Dict:
        """Handle component error"""
        return cls.handle_error(
            error_type="component",
            message=message,
            details={
                "component": component,
                "field": field,
                "value": value
            }
        )

    @classmethod
    def handle_flow_error(
        cls,
        step: str,
        action: str,
        data: Dict,
        message: str
    ) -> Dict:
        """Handle flow error"""
        return cls.handle_error(
            error_type="flow",
            message=message,
            details={
                "step": step,
                "action": action,
                "data": data
            }
        )

    @classmethod
    def handle_system_error(
        cls,
        code: str,
        service: str,
        action: str,
        message: str
    ) -> Dict:
        """Handle system error"""
        return cls.handle_error(
            error_type="system",
            message=message,
            details={
                "code": code,
                "service": service,
                "action": action
            }
        )
```

### 2. Error Usage

```python
# Component error
try:
    result = component.validate(value)
    if not result.valid:
        error = ErrorHandler.handle_component_error(
            component="amount_input",
            field="amount",
            value=value,
            message="Invalid amount format"
        )
        return error

# Flow error
try:
    if amount > balance:
        error = ErrorHandler.handle_flow_error(
            step="amount",
            action="validate",
            data={"amount": amount, "balance": balance},
            message="Insufficient balance"
        )
        return error

# System error
try:
    response = make_api_call()
except Exception as e:
    error = ErrorHandler.handle_system_error(
        code="API_ERROR",
        service="payment",
        action="process",
        message="Service unavailable"
    )
    return error
```

### 3. Error Response

```python
# API error response
{
    "error": {
        "type": "system",
        "message": "Service unavailable",
        "details": {
            "code": "API_ERROR",
            "service": "payment",
            "action": "process"
        }
    }
}

# Component error response
{
    "error": {
        "type": "component",
        "message": "Invalid amount format",
        "details": {
            "component": "amount_input",
            "field": "amount",
            "value": "abc"
        }
    }
}

# Flow error response
{
    "error": {
        "type": "flow",
        "message": "Insufficient balance",
        "details": {
            "step": "amount",
            "action": "validate",
            "data": {
                "amount": 100,
                "balance": 50
            }
        }
    }
}
```

## Best Practices

1. **Error Creation**
- Use ErrorHandler methods
- Provide clear messages
- Include relevant details
- NO manual error objects
- NO mixed error types
- NO sensitive data

2. **Error Handling**
- Handle at appropriate level
- Use correct error type
- Include needed context
- NO error propagation
- NO local recovery
- NO state fixing

3. **Error Response**
- Use standard format
- Clear messages
- Minimal structure
- NO nested wrappers
- NO redundant data
- NO state duplication

4. **Error Logging**
- Log through ErrorHandler
- Include error context
- Add debugging details
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
