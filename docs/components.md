# Components

## Core Principles

1. **Clear Boundaries**
- Components handle validation
- Components convert data
- Components manage errors
- NO business logic
- NO state management
- NO flow control

2. **Simple Structure**
- Minimal interfaces
- Clear validation
- Standard conversion
- NO complex hierarchies
- NO redundant wrapping
- NO state duplication

3. **Pure Functions**
- Stateless validation
- Clear conversion
- Standard errors
- NO stored state
- NO side effects
- NO manual handling

4. **Central Registry**
- Single component registry
- Standard validation
- Clear interfaces
- NO manual creation
- NO local state
- NO mixed concerns

## Component Types

```python
class ComponentRegistry:
    """Central component management"""

    COMPONENTS = {
        # Input components
        "AmountInput": {
            "type": "input",
            "validates": ["amount"],
            "converts_to": ["amount", "denomination"]
        },
        "HandleInput": {
            "type": "input",
            "validates": ["handle"],
            "converts_to": ["handle"]
        },
        "SelectInput": {
            "type": "input",
            "validates": ["selection"],
            "converts_to": ["selected_id"]
        },
        "ConfirmInput": {
            "type": "input",
            "validates": ["confirmation"],
            "converts_to": ["confirmed"]
        }
    }
```

## Validation Patterns

### 1. Validation State
Every component tracks validation:
```python
validation_state = {
    "in_progress": bool,    # Is validation in progress
    "error": Optional[Dict],# Current error if any
    "attempts": int,        # Number of validation attempts
    "last_attempt": Any     # Last attempted value
}
```

### 2. Validation Results
All validations return standard result:
```python
ValidationResult(
    valid: bool,           # Success/failure
    value: Optional[Any],  # Validated value if success
    error: Optional[Dict]  # Error details if failure
)
```

### 3. Error Context
All errors include standard context:
```python
error = {
    "message": str,        # User-facing message
    "field": str,          # Field that failed
    "details": {           # Error context
        "expected_type": str,
        "actual_type": str,
        "attempts": int
    }
}
```

## Best Practices

1. **Component Design**
- Single responsibility
- Clear validation tracking
- Standard conversion
- NO business logic
- NO state management
- NO flow control

2. **Error Handling**
- Use ValidationResult
- Track validation state
- Include attempt tracking
- NO manual handling
- NO local recovery
- NO state fixing

3. **Data Conversion**
- Include validation state
- Track conversion attempts
- Standard formats
- NO business logic
- NO validation
- NO state changes

4. **Integration**
- Use component factory
- Standard interfaces
- Clear boundaries
- NO manual creation
- NO state access
- NO flow control

## Integration

Components integrate with:
- Flow framework
- State management
- Error handling
- Message templates
- Input validation

For more details on:
- Flow Framework: [Flow Framework](flow-framework.md)
- State Management: [State Management](state-management.md)
- Error Handling: [Error Handling](error-handling.md)
