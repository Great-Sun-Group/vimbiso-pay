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

## Flow Types

```python
class FlowRegistry:
    """Central flow type management"""

    # Common flow configurations
    COMMON_FLOWS = {
        "action": {
            "steps": ["select", "confirm"],
            "components": {
                "select": "SelectInput",
                "confirm": "ConfirmInput"
            }
        }
    }

    # Flow type definitions with metadata
    FLOWS = {
        # Member flows
        "registration": {
            "handler_type": "member",
            "flow_type": "registration",
            "steps": ["firstname", "lastname"],
            "components": {
                "firstname": "TextInput",
                "lastname": "TextInput"
            }
        },

        # Action flows use common configuration
        "credex_accept": {
            "handler_type": "credex",
            "flow_type": "action",
            "action_type": "accept",
            **COMMON_FLOWS["action"]
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
    "total_steps": int,     # total steps in flow

    # Component state
    "active_component": {
        "type": str,        # component type
        "value": Any,       # current value
        "validation": {     # validation state
            "in_progress": bool,
            "error": Optional[Dict],
            "attempts": int,
            "last_attempt": Any
        }
    },

    # Flow metadata
    "started_at": str,      # ISO timestamp
    "action_type": str,     # For action flows

    # Business data
    "data": Dict           # Flow-specific data
}
```

## Implementation

### 1. Flow Manager
```python
class FlowManager:
    """Manages flow progression and component state"""

    def process_step(self, step: str, value: Any, state_manager: Any) -> Dict:
        """Process step with validation"""
        # Get component
        component = self.get_component(step)

        # UI validation with tracking
        validation = component.validate(value)
        if not validation.valid:
            return {
                "error": validation.error,
                "type": "validation",
                "attempts": component.validation_state["attempts"]
            }

        # Update component state
        state_manager.update_state({
            "flow_data": {
                "active_component": component.get_ui_state(),
                "step_index": current_index + 1
            }
        })

        return {
            "success": True,
            "value": validation.value,
            "progress": {
                "current": current_index + 1,
                "total": total_steps
            }
        }
```

### 2. Action Flow
```python
class ActionFlow(BaseFlow):
    """Flow for accept/decline/cancel actions"""

    ACTIONS = {
        "accept": {
            "service_method": "accept_credex",
            "confirm_prompt": "accept",
            "cancel_message": "Acceptance cancelled",
            "complete_message": "✅ Offer accepted successfully."
        }
    }

    def __init__(self, messaging_service: MessagingServiceInterface, action_type: str):
        super().__init__(messaging_service)
        self.action_type = action_type
        self.config = self.ACTIONS[action_type]

    def process_step(self, state_manager: Any, step: str, input_value: Any) -> Message:
        """Process action step with proper tracking"""
        # Get flow state
        flow_state = state_manager.get_flow_state()

        # Validate input
        component = self._get_component(step)
        value = self._validate_input(state_manager, step, input_value, component)

        # Update progress
        progress = f"Step {flow_state['step_index'] + 1} of {flow_state['total_steps']}"

        # Return result with progress
        return {
            "success": True,
            "message": f"{self.get_step_content(step)}\n\n{progress}"
        }
```

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
