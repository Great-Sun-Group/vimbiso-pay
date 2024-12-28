# Flow Framework

## Overview

The Flow Framework provides a progressive interaction system for handling complex, multi-step conversations in WhatsApp, extendable to other channels. It enables:
- Member-centric state management (SINGLE SOURCE OF TRUTH)
- Multi-channel support
- Structured data collection
- Validation through state updates
- Clear error handling
- Comprehensive audit logging

## Core Components

### 1. Flow Management

The framework consists of four main components:

- **Flow Base Class**
  - Manages member-centric state
  - Handles channel abstraction
  - Manages step progression
  - Processes input through state updates
  - Integrates with state management
  - Handles errors through StateException
  - Maintains audit trail

- **FlowStateManager**
  - Validates all state updates
  - Manages state transitions
  - Raises StateException for invalid state
  - Enforces SINGLE SOURCE OF TRUTH
  - Manages channel information

- **Step Definition**
  - Defines interaction type
  - Updates state for validation
  - Processes input through state
  - Generates channel-aware messages

- **FlowAuditLogger**
  - Logs flow events with member context
  - Tracks state transitions
  - Records state updates
  - Provides debugging context

### 2. Step Types

Supports three interaction types:
- `TEXT`: Free-form text input
- `BUTTON`: Button-based responses
- `LIST`: Selection from a list of options

### 3. State Integration

Each flow maintains:
- Member ID as primary identifier (ONLY at top level)
- Channel information (ONLY at top level)
- Current step index
- Collected data
- NO validation state
- NO previous state
- NO recovery paths

## Implementation

### Flow Creation

```python
class CredexFlow(Flow):
    def __init__(self, flow_type: str, state: Dict = None):
        # Get member ID and channel info
        member_id = state.get("member_id")
        channel_id = self._get_channel_identifier(state)

        steps = self._create_steps()
        super().__init__(f"{flow_type}_{member_id}", steps)
```

### Step Definition

```python
# WRONG - Using validator and transformer functions
Step(
    id="amount",
    type=StepType.TEXT,
    message=self._get_amount_prompt,
    validator=self._validate_amount,  # NO manual validation!
    transformer=self._transform_amount
)

# CORRECT - Let StateManager validate through state updates
Step(
    id="amount",
    type=StepType.TEXT,
    message=self._get_amount_prompt,
    process_input=self._process_amount  # Updates state for validation
)

def _process_amount(self, state_manager: Any, input_data: str) -> None:
    """Process amount input through state update"""
    state_manager.update_state({
        "flow_data": {
            "input": {
                "amount": input_data  # StateManager validates
            }
        }
    })
```

### State Structure

```python
# Core identity - SINGLE SOURCE OF TRUTH
state_manager.update_state({
    # Member ID - ONLY at top level
    "member_id": member_id,

    # Channel info - ONLY at top level
    "channel": {
        "type": "whatsapp",
        "identifier": channel_id
    },

    # Flow state - NO validation state
    "flow_data": {
        "step": current_step,
        "flow_type": flow_type
    }
})
```

### Audit Logging

```python
# Log flow event with member context
audit.log_flow_event(
    flow_id=f"credex_offer_{member_id}",
    event_type="step_start",
    step_id="amount",
    state={
        "member_id": member_id,
        "channel": {
            "type": "whatsapp",
            "identifier": channel_id
        },
        **current_state
    },
    status="in_progress"
)

# Log validation with member context
audit.log_validation_event(
    flow_id=f"credex_offer_{member_id}",
    step_id="amount",
    input_data={
        "member_id": member_id,
        "channel": channel_info,
        "data": input_data
    },
    validation_result=result
)

# Log state transition with member context
audit.log_state_transition(
    flow_id=f"credex_offer_{member_id}",
    from_state=old_state,
    to_state=new_state,
    status="success"
)
```

## Message Handling

### 1. Message Types
- Text messages
- Button messages
- List messages
- Interactive content
- Template messages

### 2. Template Organization
- Member-centric templates
- Channel-aware components
- Reusable components
- Type-safe creation
- Consistent formatting

## Best Practices

1. **State Management**
   - Member ID ONLY at top level
   - Channel info ONLY at top level
   - NO validation state
   - NO state duplication
   - NO state transformation
   - NO state passing
   - NO error recovery

2. **Flow Implementation**
   - Keep flows focused and single-purpose
   - Let StateManager validate through updates
   - Handle channel-specific requirements
   - Process input through state updates
   - Handle errors through StateException
   - Log state transitions
   - NO manual validation

3. **Template Usage**
   - Use member-centric templates
   - Handle channel-specific formatting
   - Keep templates reusable
   - Follow channel limits
   - Let StateManager validate templates

4. **Error Handling**
   - Let StateManager validate state
   - NO manual validation
   - NO error recovery
   - NO state fixing
   - Clear error messages
   - Log errors only

5. **Audit Logging**
   - Include member context in logs
   - Log channel information
   - Track state transitions
   - Log state updates
   - Document errors
   - Enable debugging

## Integration

The Flow Framework integrates with:
- WhatsApp message handling
- Redis state management
- API services
- User authentication
- Audit logging system

For more details on:
- State Management: [State Management](state-management.md)
- WhatsApp Integration: [WhatsApp](whatsapp.md)
- API Integration: [API Integration](api-integration.md)
