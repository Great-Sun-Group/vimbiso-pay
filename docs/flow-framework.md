# Flow Framework

## Core Principles

1. **Clear Boundaries**
- Flows manage progression
- Components handle input
- State validates updates
- NO mixed responsibilities
- NO state duplication
- NO manual validation

2. **Simple Structure**
- Common flow configurations
- Clear flow types
- Standard components
- Flow type metadata
- NO complex hierarchies
- NO redundant wrapping

3. **Pure Functions**
- Stateless operations
- Clear input/output
- Standard validation
- NO stored state
- NO side effects
- NO manual handling

4. **Central Management**
- Single flow registry
- Standard progression
- Clear validation
- Progress tracking
- NO manual routing
- NO local state

## Flow Registry

### 1. Common Configurations
```python
COMMON_FLOWS = {
    "action": {
        "steps": ["select", "confirm"],
        "components": {
            "select": "SelectInput",
            "confirm": "ConfirmInput"
        }
    }
}
```

### 2. Flow Types
```python
FLOWS = {
    "registration": {
        "handler_type": "member",
        "steps": ["firstname", "lastname"],
        "components": {
            "firstname": "TextInput",
            "lastname": "TextInput"
        }
    },
    "credex_accept": {
        "handler_type": "credex",
        "flow_type": "action",
        "action_type": "accept"
    }
}
```

## State Patterns

### 1. Flow State
```python
flow_state = {
    # Flow identification
    "flow_type": str,     # Type of flow
    "handler_type": str,  # Handler responsible
    "step": str,         # Current step
    "step_index": int,   # Current position
    "total_steps": int,  # Total steps

    # Validation tracking
    "active_component": {
        "type": str,     # Component type
        "validation": {
            "in_progress": bool,
            "error": Optional[Dict],
            "attempts": int,
            "last_attempt": Any
        }
    }
}
```

### 2. Progress Tracking
Every flow update includes:
- Current step index
- Total steps
- Validation state
- Attempt tracking

## Best Practices

1. **Flow Management**
- Use common configurations
- Clear flow types
- Standard components
- Progress tracking
- NO manual routing
- NO local state

2. **State Updates**
- Track validation state
- Track progress
- Standard validation
- NO state duplication
- NO manual validation
- NO state fixing

3. **Error Handling**
- Track validation attempts
- Clear boundaries
- Standard formats
- NO manual handling
- NO local recovery
- NO state fixing

4. **Component Usage**
- Standard components
- Track validation state
- Pure functions
- NO stored state
- NO side effects
- NO manual handling

## Integration

The Flow Framework integrates with:
- Component system
- State management
- Error handling
- Message templates
- API services

For more details on:
- Components: [Components](components.md)
- State Management: [State Management](state-management.md)
- Error Handling: [Error Handling](error-handling.md)
