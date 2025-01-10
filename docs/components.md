# Component System

The component system provides self-contained operational units that handle specific tasks while maintaining clear boundaries and responsibilities. Each component type follows standard patterns for validation, state management, and error handling.

## Component Types

### 1. Display Components
Handle UI presentation and messaging:
- Format data for display
- Access state through get_state_value()
- Store display data in component_data.data
- No schema validation for component data
- Clear messaging patterns

### 2. Input Components
Handle user input validation:
- Pure UI validation
- Business validation in services
- State updates with validation
- Store input data in component_data.data
- Clear validation patterns

### 3. API Components
Handle external API calls:
- Make API calls directly
- Let handlers update schema-validated state
- Store API data in component_data.data
- Use action data for flow control
- Clear error handling

### 4. Confirm Components
Handle user confirmations:
- Extend ConfirmBase
- Context-aware messaging
- Store confirmation data in component_data.data
- State updates with validation
- Clear confirmation patterns

## Core Principles

### 1. Self-Contained Operation
Components handle their own:
- Business logic and validation
- Activation of shared utilities
- State access through get_state_value()
- Error handling and messaging
- Clear operational boundaries
- Component-specific data storage

### 2. State Management
Components follow standard state patterns:
- All state access through get_state_value()
- Schema validation for core state
- Component freedom in data dict
- Default empty dict prevents None access
- No direct state passing
- Standard validation tracking

### 3. Error Handling
Components use standard error patterns:
- All operations in try/except
- Use ErrorHandler consistently
- Clear error context
- Proper validation state
- Standard error patterns
- Validation failures include details

### 4. Validation Boundaries
Components implement layered validation:
- Schema validation at state manager level
- Component-specific validation:
  * Display components -> Format requirements
  * Input components -> UI requirements
  * API components -> Request/response requirements
  * Confirm components -> Confirmation requirements
- Business validation in services
- Clear validation patterns
- Standard validation results

### 5. Component Data Freedom
Components have freedom in their data:
- component_data.data is unvalidated
- Store any component-specific data
- No schema restrictions
- Clear data ownership
- Proper cleanup

## Mistakes to avoid:
1. DON'T use get_component_data() - use get_state_value()
2. DON'T access state directly - always use state manager
3. DON'T validate component_data.data in schema
4. DON'T mix validation responsibilities
5. DON'T store sensitive data in component data
6. DON'T bypass component boundaries
7. DON'T forget default empty dicts
8. DON'T persist validation state
