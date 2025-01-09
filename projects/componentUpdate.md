# Component System Type Safety Update

## Overview
Update the component system to use proper type safety with StateManagerInterface, eliminating Any types while maintaining the existing validation and state management patterns.

## Changes Required

### 1. Core Config Package
- [x] Created StateManagerInterface in core.config.interface
- [x] Updated Component base class to use StateManagerInterface
- [ ] Update state_utils.py to use StateManagerInterface:
  ```python
  def update_state_core(state_manager: StateManagerInterface, updates: Dict[str, Any]) -> None
  def update_flow_state(state_manager: StateManagerInterface, context: str, ...) -> None
  def update_flow_data(state_manager: StateManagerInterface, data: Dict[str, Any]) -> None
  def clear_flow_state(state_manager: StateManagerInterface) -> None
  ```

### 2. Core Messaging Package
- [ ] Update flow.py functions to use StateManagerInterface:
  ```python
  def _set_default_account(state_manager: StateManagerInterface) -> bool
  def activate_component(component_type: str, state_manager: StateManagerInterface) -> Any
  def handle_component_result(..., state_manager: Optional[StateManagerInterface] = None)
  def process_component(context: str, component: str, state_manager: StateManagerInterface)
  ```
- [ ] Update utils.py to use StateManagerInterface:
  ```python
  def get_recipient(state_manager: StateManagerInterface) -> MessageRecipient
  ```

### 3. Core API Package
- [ ] Update api_response.py to use StateManagerInterface:
  ```python
  def handle_api_response(response: Response, state_manager: StateManagerInterface)
  ```
- [ ] Update base.py to use StateManagerInterface:
  ```python
  def make_api_request(..., state_manager: StateManagerInterface)
  def get_headers(state_manager: StateManagerInterface, url: str)
  ```

### 4. Component Classes
All component classes inherit from Component base class which now uses StateManagerInterface, so their set_state_manager methods are automatically typed correctly. No changes needed to:
- Display components (ViewLedger, AccountDashboard, etc.)
- Input components (AmountInput, HandleInput, etc.)
- API components (LoginApiCall, CreateCredexApiCall, etc.)
- Confirm components (ConfirmUpgrade, ConfirmOfferSecured, etc.)

## Implementation Strategy

1. Start with Core Config:
   - Update state_utils.py first since it's part of core config
   - This establishes the pattern for other modules

2. Move to Core Messaging:
   - Update flow.py next as it's the main flow controller
   - Then update utils.py for consistency

3. Update Core API:
   - Update api_response.py and base.py
   - These handle API interactions and state updates

4. Verify Component System:
   - Confirm Component base class changes propagate correctly
   - Test with different component types
   - Verify validation and state management still work

## Success Criteria

1. No Any types in state manager usage
2. All components use StateManagerInterface
3. Validation and state tracking work correctly
4. No regression in functionality
5. Clean mypy output
6. All tests passing

## Documentation Updates

1. Update architecture.md:
   - Document interface usage
   - Update code examples
   - Add type safety section

2. Update state-management.md:
   - Add interface documentation
   - Update state patterns
   - Add type safety examples

3. Update flow-framework.md:
   - Document typed components
   - Update flow examples
   - Add interface usage
