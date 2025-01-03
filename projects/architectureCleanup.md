# Architecture Cleanup Project Plan

## Overview

This project aims to align the codebase with the standardization docs by implementing proper state management, flow framework patterns, and component architecture. The focus is on maintaining clear boundaries between UI validation, flow coordination, and business logic.

## Progress Update

1. Completed:
- Removed legacy core/accounts/ implementation
- Confirmed new architecture pattern in services/
- Identified proper validation requirements

2. Current Architecture:
```
core/api/
  - Pure API functions
  - State validation at boundaries
  - Error handling

services/credex/
  - Business logic layer
  - Pure functions
  - Service coordination

services/messaging/credex/
  - Flow coordination
  - UI validation
  - State management
```

## Next Steps

1. Flow Framework
- Update flow initialization with proper step_index
- Add component state tracking
- Implement proper validation state
- Files: app/core/messaging/flow.py

2. Component System
- Update base component with ValidationResult
- Clean up input components
- Remove any remaining business logic
- Files: app/core/components/{base,input}.py

3. Service Layer
- Verify API integration patterns
- Clean up service coordination
- Ensure proper error handling
- Files: app/services/credex/*, app/core/api/credex.py

4. Documentation
- Update architecture docs if needed
- Add examples of proper patterns
- Document validation requirements
- Files: docs/*.md

## Implementation Guidelines

### 1. Clean Architecture

```python
# Simple Three-Layer Design

1. Components (UI Layer)
   - Pure input validation
   - Clear validation messages
   - No business logic

   Example:
   class HandleInput(Component):
       def validate(self, value: str) -> ValidationResult:
           if not value.strip():
               return ValidationResult(valid=False, error="Handle required")
           if len(value) > 30:
               return ValidationResult(valid=False, error="Handle too long")
           return ValidationResult(valid=True)

2. Handlers (Flow Layer)
   - Flow coordination
   - Service calls
   - State updates

   Example:
   class CredexHandler:
       def handle_handle_step(self, state_manager, value):
           # Get component validation
           component = HandleInput()
           validation = component.validate(value)
           if not validation.valid:
               return self.messaging.send_error(validation.error)

           # Call service
           result = self.credex_service.validate_handle(value)
           if not result.success:
               return self.messaging.send_error(result.error)

           # Update state and continue flow
           state_manager.update_state({
               "flow_data": {
                   "data": {"handle": value},
                   "step": "confirm"
               }
           })
           return self.messaging.send_confirmation()

3. Services (Business Layer)
   - API calls
   - Business logic
   - Data transformation

   Example:
   class CredexService:
       def validate_handle(self, handle: str) -> Result:
           # Call API
           response = self.api.check_handle(handle)

           # Transform response
           if not response.success:
               return Result(success=False, error="Handle not available")

           return Result(success=True, data={
               "handle": handle,
               "validated": True
           })
```

### 2. Key Principles

1. Clear Boundaries
- Components only validate input format
- Handlers manage flow and state
- Services handle business logic and APIs

2. Simple Data Flow
```
Input -> Component validates -> Handler coordinates -> Service processes -> Handler updates state -> Next step
```

3. Clean State Management
```python
# Clear state structure
{
    "flow_data": {
        # Flow state
        "flow_type": "credex_offer",
        "handler_type": "credex",
        "step": "handle",
        "step_index": 1,

        # Component state
        "active_component": {
            "type": "handle_input",
            "value": "@alice",
            "validation": {
                "in_progress": False,
                "error": None
            }
        },

        # Business data
        "data": {
            "handle": "@alice",
            "validated": True
        }
    }
}
```

### 3. State Management

```python
# UI State (in flow_data.active_component)
{
    "type": "amount_input",
    "value": "100.00",
    "validation": {
        "in_progress": bool,
        "error": Optional[Dict]
    }
}

# Flow State (in flow_data)
{
    "flow_type": str,
    "handler_type": str,
    "step": str,
    "step_index": int
}

# Business State (in flow_data.data)
{
    "verified_data": Dict,  # Transformed by service
    "api_results": Dict,    # From service calls
    "errors": List[Dict]    # Business logic errors
}
```

## Current Issues

### 1. State Management
- Missing step_index tracking in flow state
- Missing active_component state structure
- Missing validation state tracking
- Components directly accessing state_manager
- Inconsistent state validation

### 2. Component System
- Components returning Dict instead of ValidationResult
- Error handling mixed with validation logic
- Direct API calls in components
- Missing component state tracking
- No clear component state boundaries

### 3. Flow Framework
- Missing proper component state updates
- API calls in wrong layer
- Unclear handler boundaries
- Inconsistent error handling
- Missing step progression tracking

### 4. Error Handling
- Mixed error handling responsibilities
- Inconsistent error boundaries
- Non-standardized error responses
- Missing error context in some areas

## Implementation Plan

### Phase 1: Service Layer Implementation

1. Create Domain Services
```python
class CredexService:
    """Handles all Credex business logic and API calls"""

    def validate_amount(self, amount: str) -> ValidationResult:
        """Business validation of amount"""
        pass

    def create_offer(self, amount: float, handle: str) -> Result:
        """Create offer through API"""
        pass

    def transform_offer_data(self, api_response: Dict) -> Dict:
        """Transform API data to business model"""
        pass

class MemberService:
    """Handles all Member business logic and API calls"""

    def validate_profile(self, data: Dict) -> ValidationResult:
        """Business validation of profile data"""
        pass

    def update_profile(self, data: Dict) -> Result:
        """Update profile through API"""
        pass

    def transform_profile_data(self, api_response: Dict) -> Dict:
        """Transform API data to business model"""
        pass
```

2. Update State Validation
- Enforce handler_type validation
- Add step_index validation
- Add component state validation
- Implement ValidationResult returns

Files to modify:
- app/core/messaging/flow.py
- app/core/utils/state_validator.py
- app/core/config/state_manager.py
- app/core/config/state_utils.py

### Phase 2: Component System Cleanup

1. Update Component Base Classes
```python
class Component:
    """Pure UI component with validation"""

    def validate(self, value: Any) -> ValidationResult:
        """UI-level validation only"""
        pass

class InputComponent(Component):
    """Input component with UI state"""

    def get_ui_state(self) -> Dict:
        """Get current UI state"""
        return {
            "type": self.type,
            "value": self.value,
            "validation": self.validation_state
        }
```

2. Update Input Components
- Remove all business logic
- Focus on UI validation only
- Manage UI state cleanly
- Clear validation messages

Files to modify:
- app/core/components/base.py
- app/core/components/input.py
- app/core/components/action.py
- app/core/components/auth.py

### Phase 3: Flow Framework Alignment

1. Update Flow Management
```python
class FlowManager:
    """Coordinates flow without business logic"""

    def process_step(self, step: str, value: Any) -> FlowResult:
        # Get component
        component = self.get_component(step)

        # UI validation
        validation = component.validate(value)
        if not validation.valid:
            return FlowResult.validation_error(validation.error)

        # Get appropriate service
        service = self.get_service(step)

        # Process through service
        result = service.process(value)
        if not result.success:
            return FlowResult.business_error(result.error)

        # Update state and progress
        self.update_flow_state(result.data)
        return FlowResult.success(self.get_next_step())
```

2. Update Flow Processing
- Clear separation of UI/business validation
- Proper state management
- Clean error boundaries
- Predictable flow progression

Files to modify:
- app/core/messaging/flow.py
- app/core/messaging/registry.py
- app/services/messaging/service.py
- app/services/messaging/member/handlers.py
- app/services/messaging/account/handlers.py
- app/services/messaging/credex/handlers.py

### Phase 4: Error Handling Standardization

1. Error Types
```python
class ValidationError:
    """UI validation errors"""
    type = "validation"
    component: str
    field: str
    message: str

class BusinessError:
    """Business logic errors"""
    type = "business"
    code: str
    message: str
    details: Dict

class SystemError:
    """System/technical errors"""
    type = "system"
    code: str
    service: str
    message: str
```

2. Error Handling
- Components handle UI errors
- Services handle business errors
- System handles technical errors
- Clear error boundaries and ownership

Files to modify:
- app/core/utils/error_handler.py
- app/core/utils/error_types.py
- app/core/utils/exceptions.py

## Implementation Steps

For each phase:
1. Update base classes/utilities first
2. Update implementations to use new patterns
3. Add tests to verify changes
4. Update documentation

## Testing Strategy

1. Unit Tests
- Test state validation
- Test component validation
- Test flow progression
- Test error handling

2. Integration Tests
- Test flow completion
- Test error propagation
- Test state management
- Test component interaction

3. System Tests
- Test full flows
- Test error recovery
- Test state persistence
- Test component lifecycle

## Success Criteria

1. State Management
- [ ] All state updates go through state_manager
- [ ] No direct state access in components
- [ ] Proper validation at all levels
- [ ] Clear state boundaries

2. Component System
- [ ] All components use ValidationResult
- [ ] No direct API calls in components
- [ ] Clear component state tracking
- [ ] Proper error handling

3. Flow Framework
- [ ] Proper step tracking
- [ ] Clear handler boundaries
- [ ] Consistent state updates
- [ ] Standard error handling

4. Error Handling
- [ ] Clear error boundaries
- [ ] Standard error formats
- [ ] Proper error context
- [ ] Consistent error handling

## Rollout Plan

1. Phase 1: State Management (1-2 days)
- Update state structure
- Implement validation
- Update state access

2. Phase 2: Component System (2-3 days)
- Update base classes
- Update implementations
- Add tests

3. Phase 3: Flow Framework (2-3 days)
- Update flow management
- Update handlers
- Add tests

4. Phase 4: Error Handling (1-2 days)
- Update error handling
- Standardize responses
- Add tests

Total estimated time: 6-10 days

## Risk Mitigation

1. State Management
- Implement changes incrementally
- Add validation checks
- Monitor state updates

2. Component System
- Update components one at a time
- Test each component thoroughly
- Monitor API interactions

3. Flow Framework
- Update flows incrementally
- Test flow progression
- Monitor state changes

4. Error Handling
- Add logging
- Monitor error rates
- Track error resolution

## Documentation Updates

1. Update Architecture Docs
- State management patterns
- Component patterns
- Flow patterns
- Error handling

2. Update API Docs
- Component interfaces
- Handler interfaces
- Error responses
- State structure

3. Update Developer Guides
- State management guide
- Component development guide
- Flow development guide
- Error handling guide
