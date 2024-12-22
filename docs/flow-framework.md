# Flow Framework

## Overview

The Flow Framework provides a progressive interaction system for handling complex, multi-step conversations in WhatsApp. It enables:
- Structured data collection
- Input validation
- State management
- Error recovery
- Comprehensive audit logging

## Core Components

### 1. Flow Management

The framework consists of four main components:

- **Flow Base Class**
  - Manages step progression
  - Handles data collection
  - Integrates with state management
  - Provides error recovery
  - Maintains audit trail

- **FlowStateManager**
  - Validates flow state
  - Manages state transitions
  - Handles rollbacks
  - Preserves validation context

- **Step Definition**
  - Defines interaction type
  - Provides validation rules
  - Handles data transformation
  - Generates messages

- **FlowAuditLogger**
  - Logs flow events
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
- Current step index
- Collected data
- Minimal validation state in flow_data.data
- Previous state for rollback
- Audit trail data
- Smart recovery paths

Key improvements:
- Simplified validation context
- More efficient state transitions
- Better error recovery
- Clearer validation paths

## Implementation

### Flow Creation

```python
class CredexFlow(Flow):
    def __init__(self, flow_type: str):
        steps = self._create_steps()
        super().__init__(f"credex_{flow_type}", steps)
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

### Audit Logging

```python
# Log flow event
audit.log_flow_event(
    flow_id="credex_offer",
    event_type="step_start",
    step_id="amount",
    state=current_state,
    status="in_progress"
)

# Log validation
audit.log_validation_event(
    flow_id="credex_offer",
    step_id="amount",
    input_data=input_data,
    validation_result=result
)

# Log state transition
audit.log_state_transition(
    flow_id="credex_offer",
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
- Domain-specific templates
- Reusable components
- Type-safe creation
- Consistent formatting

## Best Practices

1. **State Management**
   - Keep validation context in flow_data.data
   - Use minimal required validations
   - Implement smart state recovery
   - Focus on critical data integrity
   - Maintain focused audit trail

2. **Flow Implementation**
   - Keep flows focused and single-purpose
   - Validate input properly
   - Handle errors gracefully
   - Log state transitions
   - Enable automatic recovery

3. **Template Usage**
   - Use domain-specific templates
   - Keep templates reusable
   - Follow WhatsApp limits
   - Handle errors properly

4. **Error Recovery**
   - Validate state before updates
   - Preserve context during errors
   - Implement proper rollback
   - Provide clear error messages
   - Log recovery attempts

5. **Audit Logging**
   - Log all flow events
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
