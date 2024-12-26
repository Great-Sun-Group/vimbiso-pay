# Flow Framework

## Overview

The Flow Framework provides a progressive interaction system for handling complex, multi-step conversations in WhatsApp, extendable to other channels. It enables:
- Member-centric state management
- Multi-channel support
- Structured data collection
- Input validation
- Error recovery
- Comprehensive audit logging

## Core Components

### 1. Flow Management

The framework consists of four main components:

- **Flow Base Class**
  - Manages member-centric state
  - Handles channel abstraction
  - Manages step progression
  - Handles data collection
  - Integrates with state management
  - Provides error recovery
  - Maintains audit trail

- **FlowStateManager**
  - Validates member and channel state
  - Manages state transitions
  - Handles rollbacks
  - Preserves validation context
  - Manages channel information

- **Step Definition**
  - Defines interaction type
  - Provides validation rules
  - Handles data transformation
  - Generates channel-aware messages

- **FlowAuditLogger**
  - Logs flow events with member context
  - Tracks state transitions
  - Records validation results
  - Enables state recovery
  - Provides debugging context

### 2. Step Types

Supports three interaction types:
- `TEXT`: Free-form text input
- `BUTTON`: Button-based responses
- `LIST`: Selection from a list of options

### 3. State Integration

Each flow maintains:
- Member ID as primary identifier
- Channel information
- Current step index
- Collected data
- Minimal validation state in flow_data.data
- Previous state for rollback
- Audit trail data
- Smart recovery paths

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
Step(
    id="amount",
    type=StepType.TEXT,
    message=self._get_amount_prompt,
    validator=self._validate_amount,
    transformer=self._transform_amount
)
```

### State Structure

```python
new_state = {
    # Core identity - SINGLE SOURCE OF TRUTH
    "member_id": member_id,  # Primary identifier, ONLY AND ALWAYS at top level

    # Channel information
    "channel": {
        "type": "whatsapp",
        "identifier": channel_id
    },

    # Flow and state info
    "flow_data": {
        "id": flow_id,
        "step": current_step,
        "data": {
            "flow_type": flow_type,
            "channel": {
                "type": "whatsapp",
                "identifier": channel_id
            }
        }
    }
}
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
   - Use member_id as primary identifier
   - Maintain proper channel abstraction
   - Keep validation context in flow_data.data
   - Use minimal required validations
   - Implement smart state recovery
   - Focus on critical data integrity
   - Maintain focused audit trail

2. **Flow Implementation**
   - Keep flows focused and single-purpose
   - Validate member and channel info
   - Handle channel-specific requirements
   - Validate input properly
   - Handle errors gracefully
   - Log state transitions
   - Enable automatic recovery

3. **Template Usage**
   - Use member-centric templates
   - Handle channel-specific formatting
   - Keep templates reusable
   - Follow channel limits
   - Handle errors properly

4. **Error Recovery**
   - Validate member and channel state
   - Preserve context during errors
   - Implement proper rollback
   - Provide clear error messages
   - Log recovery attempts

5. **Audit Logging**
   - Include member context in logs
   - Log channel information
   - Track state transitions
   - Record validation results
   - Document error scenarios
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
