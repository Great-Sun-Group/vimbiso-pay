# State Management

## Code Reading Guide
Before modifying state management, read these files in order:

1. core/config/state_manager.py - Understand central state management
   - Learn state access patterns
   - Understand state updates
   - Review state validation

2. core/utils/state_validator.py - Learn validation rules
   - Understand state validation
   - Learn validation patterns
   - Review validation rules

3. core/messaging/base.py - Understand state usage
   - Learn state integration
   - Understand state flow
   - Review state patterns

4. core/config/atomic_state.py - Learn atomic operations
   - Understand state atomicity
   - Learn transaction patterns
   - Review rollback handling

Common mistakes to avoid:
1. DON'T modify state without understanding validation
2. DON'T bypass state manager for direct access
3. DON'T mix state responsibilities
4. DON'T duplicate state across components

## Core Principles

1. **Single Source of Truth**
- Channel info accessed through get_channel_id()
- JWT token accessed through flow_data auth
- Member data accessed through dashboard state
- Messaging service accessed through state_manager.messaging
- NO direct state access
- NO state passing
- NO transformation

2. **Messaging Service Integration**
- MessagingService sets up bidirectional relationship:
  ```python
  def __init__(self, channel_service: BaseMessagingService, state_manager: Any):
      self.channel_service = channel_service
      self.state_manager = state_manager
      if state_manager:
          # Set up bidirectional relationship
          self.channel_service.state_manager = state_manager
          state_manager.messaging = self
  ```
- Components access messaging through state_manager:
  ```python
  # Send message through messaging service
  self.state_manager.messaging.send_text(
      recipient=recipient,
      text=message_text
  )
  ```
- Error handling through ErrorHandler:
  ```python
  try:
      self.state_manager.messaging.send_text(...)
  except Exception as e:
      error_response = ErrorHandler.handle_component_error(
          component=self.type,
          field="messaging",
          value=str(message_text),
          message=str(e)
      )
      return ValidationResult.failure(message=error_response["error"]["message"])
  ```

3. **Component Responsibilities**
- Components handle their own operations:
  * API calls through make_api_request
  * Message sending through state_manager.messaging
  * Error handling through ErrorHandler
  * State updates with validation
- Clear boundaries between components:
  * Display components -> UI and messaging
  * Input components -> Validation and state updates
  * API components -> External calls and state updates
  * Confirm components -> User confirmation flows
- Standard validation and error handling:
  * All operations wrapped in try/except
  * All errors handled through ErrorHandler
  * All results returned as ValidationResult

3. **Pure Functions**
- Stateless operations
- Clear validation
- Standard updates
- NO stored state
- NO side effects
- NO manual handling

4. **Central Management**
- Single state manager
- Standard validation
- Clear boundaries
- Context tracking
- NO manual updates
- NO local state

## State Structure

### 1. Core Identity

### Component Integration

Each component type has specific state integration patterns:

1. **Display Components**
- Access state through state_manager
- Read-only state access
- Format state data for display
- No state modifications
- Example:
```python
class ViewLedger(DisplayComponent):
    def validate_display(self, value: Any) -> ValidationResult:
        active_account_id = self.state_manager.get("active_account_id")
        dashboard = self.state_manager.get("dashboard")
        # Format for display...
```

2. **Input Components**
- Validate input format
- Update state with validated input
- Track validation attempts
- No direct state reads
- Example:
```python
class AmountInput(InputComponent):
    def validate(self, value: Any) -> ValidationResult:
        # Validate format...
        self.update_state(str(amount), ValidationResult.success(amount))
```

3. **API Components**
- Get member data from dashboard
- Make API call with proper data
- Let handlers manage state updates:
  * dashboard.py -> Updates member state
  * action.py -> Updates operation state
- Use action data for flow control
- Example:
```python
class UpgradeMemberApiCall(ApiComponent):
    def validate(self, value: Any) -> ValidationResult:
        # Get member data from dashboard
        dashboard = self.state_manager.get("dashboard")
        member_id = dashboard.get("member", {}).get("memberID")

        # Make API call
        response = make_api_request(url, headers, payload)

        # Let handlers update state
        response_data, error = handle_api_response(
            response=response,
            state_manager=self.state_manager
        )

        # Use action data for flow
        flow_data = self.state_manager.get_flow_state()
        action_data = flow_data.get("action", {})
        return ValidationResult.success({"action": action_data})
```

4. **Confirm Components**
- Access state for confirmation context
- Update state with confirmation result
- Context-aware validation
- Track confirmation attempts
- Example:
```python
class ConfirmUpgrade(ConfirmBase):
    def handle_confirmation(self, value: bool) -> ValidationResult:
        # Get member data from dashboard
        dashboard = self.state_manager.get("dashboard")
        member_id = dashboard.get("member", {}).get("memberID")

        # Get confirmation data from flow
        flow_data = self.state_manager.get_flow_state()
        confirm_data = flow_data.get("data", {})

        # Validate and update state...
        return ValidationResult.success({
            "confirmed": value,
            "member_id": member_id,
            "data": confirm_data
        })
```

Common mistakes to avoid:
1. DON'T mix component responsibilities
   - Display components shouldn't modify state
   - Input components shouldn't read unrelated state
   - API components shouldn't format for display
   - Confirm components shouldn't make API calls

2. DON'T bypass component boundaries
   - Use proper base component
   - Implement required methods
   - Follow component patterns
   - Maintain clear responsibilities

3. DON'T duplicate state access
   - Use base component methods
   - Follow standard patterns
   - Maintain single source of truth
   - Keep state access focused

4. DON'T lose validation context
   - Track all attempts
   - Include error details
   - Maintain validation state
   - Follow validation patterns

1. DON'T create new patterns when existing ones exist
2. DON'T bypass state manager
3. DON'T mix validation responsibilities
4. DON'T duplicate validation logic

## Architecture Rules

Key principles that must be followed:

1. State Manager is Single Source of Truth
   - All state access through manager
   - No direct state modification
   - No state duplication

2. Proper State Validation
   - All updates validated
   - No invalid state
   - No validation bypass

3. Atomic State Updates
   - Use atomic operations
   - Handle rollbacks properly
   - Maintain consistency

4. Clear State Boundaries
   - State properly isolated
   - No mixed responsibilities
   - No cross-boundary access

5. Secure State Handling
   - Credentials properly managed
   - No sensitive data exposure
   - No security bypass

Common mistakes to avoid:
1. DON'T access state directly
2. DON'T bypass validation
3. DON'T break atomicity
4. DON'T mix state responsibilities

## State Management

### State Access
- Use proper accessor methods
- Validate all access
- Track access patterns

### State Updates
- Use atomic operations
- Include validation
- Track all updates

### Validation State
- Track all validation
- Include timestamps
- Maintain context

### State History
- Track state changes
- Maintain timestamps
- Record context

Common mistakes to avoid:
1. DON'T access state directly
2. DON'T update without validation
3. DON'T bypass atomicity
4. DON'T lose state history
