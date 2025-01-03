# Flow Framework

## Code Reading Guide
Before modifying flow-related functionality, read these files in order:

1. core/messaging/types.py - Understand message structures and flow types
   - Learn core message interfaces
   - Understand flow state structures
   - Review validation types

2. core/messaging/flow.py - Understand flow management
   - Learn flow progression logic
   - Understand state transitions
   - Review validation patterns

3. core/messaging/registry.py - Learn flow configurations
   - Understand flow registration
   - Learn component mapping
   - Review validation rules

4. core/messaging/exceptions.py - Understand error patterns
   - Learn flow-specific exceptions
   - Understand error boundaries
   - Review error handling patterns

Common mistakes to avoid:
1. DON'T modify flows without understanding message types
2. DON'T bypass flow registry for direct handling
3. DON'T mix component and flow responsibilities
4. DON'T create new patterns when existing ones suffice

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

## Integration Points

The Flow Framework has specific integration points with other systems:

### Component System Integration
- Components are registered in flow configurations
- Components handle input validation
- Components maintain their own state
- Flow progression depends on component validation

### State Management Integration
- Flow state stored in StateManager
- Flow progression updates state
- Component state tracked in flow state
- Validation state maintained per step

### Error Handling Integration
- Flow errors handled by ErrorHandler
- Component errors stay in components
- System errors propagate to top level
- Error state tracked in flow state

### Message Template Integration
- Templates linked to flow steps
- Templates access flow state
- Templates handle error display
- Templates maintain consistency

### API Service Integration
- Services accessed through flow state
- Service responses update flow state
- Service errors handled consistently
- State validated after service calls

Common mistakes to avoid:
1. DON'T bypass established integration points
2. DON'T create new connections when existing ones exist
3. DON'T mix responsibilities between systems
4. DON'T handle errors outside boundaries

## Common Modifications

### Adding New Flow Types
1. Check registry.py for similar flows
2. Add flow configuration to FLOWS
3. Create necessary components
4. Update validation rules
5. Test flow progression

Example:
```python
FLOWS["new_flow"] = {
    "handler_type": "member",
    "steps": ["step1", "step2"],
    "components": {
        "step1": "TextInput",
        "step2": "ConfirmInput"
    }
}
```

### Modifying Flow Progression
1. Check flow.py for progression logic
2. Update step sequence in registry
3. Modify component validation
4. Update state transitions
5. Test full flow

### Adding Flow Validation
1. Check existing validation in components
2. Add validation rules to component
3. Update flow state handling
4. Test validation scenarios

Common mistakes to avoid:
1. DON'T create new patterns when existing ones exist
2. DON'T bypass flow registry
3. DON'T mix validation responsibilities
4. DON'T duplicate validation logic

## Architecture Rules

Key principles that must be followed:

1. Flow Registry is Single Source of Truth
   - All flows must be registered
   - No dynamic flow creation
   - No bypassing registry

2. Components Own Validation
   - Components validate their own input
   - Flows don't modify component validation
   - No validation in flow logic

3. State Updates Through Manager Only
   - No direct state modification
   - All updates through state_manager
   - No state duplication

4. Clear Error Boundaries
   - Flow errors stay in flows
   - Component errors in components
   - System errors at top level

5. Pure Flow Functions
   - No side effects in flow logic
   - Clear input/output contracts
   - No stored state

Common mistakes to avoid:
1. DON'T create flows outside registry
2. DON'T mix validation responsibilities
3. DON'T modify state directly
4. DON'T bypass error boundaries

## State Management

### Flow State Access
- Access through state_manager.get_flow_state()
- Never access state directly
- Use proper accessor methods

### State Updates
- Update through state_manager.update_state()
- Include validation context
- Track update attempts

### Validation State
- Track in active_component
- Include attempt counting
- Maintain error context

### Progress Tracking
- Track step_index
- Maintain total_steps
- Record completion state

Common mistakes to avoid:
1. DON'T access state directly
2. DON'T update without validation
3. DON'T bypass state manager
4. DON'T lose tracking context
