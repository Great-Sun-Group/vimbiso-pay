# Architecture Refinement Plan

## Overview

This document outlines the plan to refine the VimbisoPay architecture to:
1. Implement simple, focused components
2. Establish clear system boundaries
3. Reduce state complexity
4. Simplify error handling

## Core Architecture

### 1. Component System
```python
class Component:
    """Base component interface"""

    def validate(self, value: Any) -> Dict:
        """Validate component input

        Returns:
            On success: {"valid": True}
            On error: {
                "error": {
                    "type": "component",
                    "message": str,
                    "details": {...}
                }
            }
        """
        raise NotImplementedError

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified data"""
        raise NotImplementedError


class AmountInput(Component):
    """Amount input with validation"""

    def validate(self, value: Any) -> Dict:
        try:
            amount = float(value)
            if amount <= 0:
                return ErrorHandler.handle_component_error(
                    component="amount_input",
                    field="amount",
                    value=value,
                    message="Amount must be positive"
                )
            return {"valid": True}
        except ValueError:
            return ErrorHandler.handle_component_error(
                component="amount_input",
                field="amount",
                value=value,
                message="Invalid amount format"
            )

    def to_verified_data(self, value: Any) -> Dict:
        return {
            "amount": float(value)
        }
```

### 2. Flow Framework
```python
class FlowManager:
    """Manages flow progression"""

    def __init__(self, flow_type: str):
        self.config = FlowRegistry.FLOWS[flow_type]
        self.components = {}

    def process_step(self, step: str, value: Any) -> Dict:
        """Process step input"""
        # Get component
        component = self.get_component(step)

        # Validate input
        result = component.validate(value)
        if "error" in result:
            return result

        # Convert to verified data
        return component.to_verified_data(value)
```

### 3. State Structure
```python
{
    # Core identity
    "member_id": str,
    "channel": {
        "type": str,
        "identifier": str
    },
    "jwt_token": str,

    # Flow state
    "flow_data": {
        "flow_type": str,  # offer, accept, etc
        "step": str,       # current step id
        "data": {          # verified step data
            "amount": float,
            "handle": str,
            "confirmed": bool
        }
    }
}
```

### 4. Error Structure
```python
# Component error
{
    "type": "component",
    "message": str,
    "details": {
        "component": str,
        "field": str,
        "value": Any
    }
}

# Flow error
{
    "type": "flow",
    "message": str,
    "details": {
        "step": str,
        "action": str,
        "data": dict
    }
}

# System error
{
    "type": "system",
    "message": str,
    "details": {
        "code": str,
        "service": str,
        "action": str
    }
}
```

## Implementation Plan

### Phase 1: Error System (Priority)
1. Implement simplified ErrorHandler
2. Update error response structure
3. Establish error boundaries
4. Remove nested error handling

Files:
- `app/core/utils/error_handler.py`
- `app/core/utils/error_types.py`
- `app/core/utils/exceptions.py`

### Phase 2: Component System
1. Create base Component class
2. Implement core input components
3. Add component factory
4. Add component registry

Files:
- `app/core/components/base.py`
- `app/core/components/input.py`
- `app/core/components/registry.py`

### Phase 3: Flow Framework
1. Create FlowRegistry
2. Implement FlowManager
3. Add flow processing
4. Update flow state management

Files:
- `app/core/messaging/flow.py`
- `app/core/messaging/registry.py`
- `app/services/whatsapp/handlers/flow_manager.py`

### Phase 4: State Management
1. Simplify state structure
2. Update state validation
3. Clean up state access
4. Remove state nesting

Files:
- `app/core/config/state_manager.py`
- `app/core/config/state_utils.py`
- `app/core/utils/state_validator.py`

## Testing Strategy

### 1. Error Testing
- Error creation
- Error boundaries
- Error propagation
- Error responses

### 2. Component Testing
- Input validation
- Data conversion
- Error handling
- Component lifecycle

### 3. Flow Testing
- Flow progression
- State updates
- Error handling
- Flow completion

### 4. Integration Testing
- End-to-end flows
- Error scenarios
- State consistency
- System boundaries

## Success Criteria

1. Simpler Error Handling
- Clear error types
- No nested errors
- Standard formats
- Clear boundaries

2. Clean Component System
- Simple validation
- Clear conversion
- Standard errors
- No state management

3. Clear Flow Framework
- Simple progression
- Standard components
- Clear validation
- No mixed concerns

4. Simple State Management
- Minimal nesting
- Clear structure
- Standard validation
- No duplication

## Documentation

Updated docs reflect simplified architecture:
- [Error Handling](docs/error-handling.md)
- [Flow Framework](docs/flow-framework.md)
- [State Management](docs/state-management.md)
- [Components](docs/components.md)

## Migration Strategy

1. Error System First
- Implement new error handling
- Update error responses
- Fix error boundaries
- Remove nesting

2. Components Next
- Add component system
- Update validation
- Fix conversion
- Clean boundaries

3. Flows After
- Update flow framework
- Fix progression
- Clean validation
- Clear concerns

4. State Last
- Simplify structure
- Update validation
- Clean access
- Remove nesting

The system is pre-launch so we implement changes directly.
