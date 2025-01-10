# Component System

The component system provides self-contained operational units that handle specific tasks while maintaining clear boundaries and responsibilities. Each component type follows standard patterns for validation, state management, and error handling.

## Component Types

### 1. Display Components
Handle UI presentation and messaging:
- Format data for display
- Access state through state_manager
- No state modifications
- Clear messaging patterns

### 2. Input Components
Handle user input validation:
- Pure UI validation
- Business validation in services
- State updates with validation
- Clear validation patterns

### 3. API Components
Handle external API calls:
- Make API calls directly
- Let handlers update state
- Use action data for flow
- Clear error handling

### 4. Confirm Components
Handle user confirmations:
- Extend ConfirmBase
- Context-aware messaging
- State updates with validation
- Clear confirmation patterns

## Core Principles

### 1. Self-Contained Operation
Components handle their own:
- Business logic and validation
- Activation of shared utilities
- State access and updates
- Error handling and messaging
- Clear operational boundaries

### 2. State Management
Components follow standard state patterns:
- Read through state_manager
- Update through validation
- Clear state boundaries
- No direct state passing
- Standard validation tracking

### 3. Error Handling
Components use standard error patterns:
- All operations in try/except
- Use ErrorHandler consistently
- Clear error context
- Proper validation state
- Standard error patterns

### 4. Validation
Components implement standard validation:
- Input validation
- State validation
- Business validation
- Clear validation patterns
- Standard validation results
