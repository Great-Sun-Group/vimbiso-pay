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
- Minimal nesting
- Clear flow types
- Standard components
- NO complex hierarchies
- NO redundant wrapping
- NO state duplication

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
- NO manual routing
- NO local state
- NO mixed concerns

## Handler Types

The system uses domain-specific handlers to process flows:

1. **Member Handler**
- Registration flows
- Authentication flows
- Profile upgrade flows
- Uses MemberHandler class

2. **Account Handler**
- Ledger operations
- Balance inquiries
- Transaction history
- Uses AccountHandler class

3. **Credex Handler**
- Credit offers
- Offer acceptance
- Offer management
- Uses CredexHandler class

## Flow Types

```python
class FlowRegistry:
    """Central flow type management"""

    FLOWS = {
        # Member flows
        "registration": {
            "handler_type": "member",
            "steps": ["firstname", "lastname"],
            "components": {
                "firstname": "TextInput",
                "lastname": "TextInput"
            }
        },
        "upgrade": {
            "handler_type": "member",
            "steps": ["confirm"],
            "components": {
                "confirm": "ConfirmInput"
            }
        },

        # Account flows
        "ledger": {
            "handler_type": "account",
            "steps": ["period", "confirm"],
            "components": {
                "period": "PeriodInput",
                "confirm": "ConfirmInput"
            }
        },

        # Credex flows
        "offer": {
            "handler_type": "credex",
            "steps": ["amount", "handle", "confirm"],
            "components": {
                "amount": "AmountInput",
                "handle": "HandleInput",
                "confirm": "ConfirmInput"
            }
        },
        "accept": {
            "handler_type": "credex",
            "steps": ["select", "confirm"],
            "components": {
                "select": "SelectInput",
                "confirm": "ConfirmInput"
            }
        }
    }
```

## Flow State

```python
{
    # Flow identification
    "flow_type": str,        # registration, upgrade, ledger, offer, accept
    "handler_type": str,     # member, account, credex
    "step": str,            # current step id
    "step_index": int,      # current step index

    # Component state
    "active_component": {
        "type": str,        # component type
        "value": Any,       # current value
        "validation": {     # validation state
            "in_progress": bool,
            "error": Optional[Dict]
        }
    },

    # Verified data
    "data": {
        # Member data
        "firstname": str,    # Registration
        "lastname": str,     # Registration
        "confirmed": bool,   # Upgrade

        # Account data
        "period": str,      # Ledger period
        "transactions": List, # Transaction history

        # Credex data
        "amount": float,    # Offer amount
        "handle": str,      # Offer recipient
        "offer_id": str     # Selected offer
    }
}
```

## Implementation

### 1. Flow Manager
```python
class FlowManager:
    """Manages flow progression"""

    def __init__(self, flow_type: str):
        self.config = FlowRegistry.FLOWS[flow_type]
        self.components = {}

    def get_component(self, step: str) -> Component:
        """Get component for step"""
        component_type = self.config["components"][step]
        if step not in self.components:
            self.components[step] = create_component(component_type)
        return self.components[step]

    def validate_step(self, step: str, value: Any) -> Dict:
        """Validate step input"""
        component = self.get_component(step)
        result = component.validate(value)
        if not result.valid:
            return ErrorHandler.handle_component_error(
                component=component.type,
                field=step,
                value=value,
                message=result.message
            )
        return None

    def process_step(self, step: str, value: Any) -> Dict:
        """Process step input"""
        # Validate input
        error = self.validate_step(step, value)
        if error:
            return error

        # Convert to verified data
        component = self.get_component(step)
        return component.to_verified_data(value)
```

### 2. Flow Processing
```python
def process_flow_input(
    state_manager: Any,
    input_data: Any
) -> Optional[Dict]:
    """Process flow input"""
    # Get flow state
    flow_state = state_manager.get_flow_state()
    flow_type = flow_state["flow_type"]
    handler_type = flow_state["handler_type"]
    current_step = flow_state["step"]

    # Get appropriate handler
    if handler_type == "member":
        handler = MemberHandler(messaging_service)
    elif handler_type == "account":
        handler = AccountHandler(messaging_service)
    elif handler_type == "credex":
        handler = CredexHandler(messaging_service)
    else:
        raise FlowException(f"Invalid handler type: {handler_type}")

    # Process through handler
    result = handler.handle_flow_step(
        state_manager,
        flow_type,
        current_step,
        input_data
    )

    # Handle error
    if "error" in result:
        return result

    # Update state
    state_manager.update_state({
        "flow_data": {
            "data": result.data,
            "step_index": flow_state["step_index"] + 1
        }
    })

    # Get next step
    next_step = get_next_step(flow_type, current_step)
    if not next_step:
        return handler.complete_flow(state_manager)

    # Update step
    state_manager.update_state({
        "flow_data": {
            "step": next_step,
            "active_component": {
                "type": get_component_type(flow_type, next_step),
                "validation": {"in_progress": False}
            }
        }
    })

    return handler.get_step_message(next_step)
```

### 3. Flow Completion
```python
def complete_flow(state_manager: Any) -> Dict:
    """Complete flow processing"""
    try:
        # Get flow data
        flow_data = state_manager.get_flow_state()

        # Process completion
        result = process_completion(flow_data)

        # Clear flow state
        state_manager.update_state({
            "flow_data": None
        })

        return result

    except Exception as e:
        return ErrorHandler.handle_flow_error(
            step="complete",
            action="process",
            data=flow_data,
            message="Failed to complete flow"
        )
```

## Best Practices

1. **Flow Management**
- Use FlowRegistry
- Clear step progression
- Standard components
- NO manual routing
- NO local state
- NO mixed concerns

2. **State Updates**
- Minimal updates
- Clear structure
- Standard validation
- NO state duplication
- NO manual validation
- NO state fixing

3. **Error Handling**
- Use ErrorHandler
- Clear boundaries
- Standard formats
- NO manual handling
- NO local recovery
- NO state fixing

4. **Component Usage**
- Standard components
- Clear validation
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
