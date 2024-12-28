# State Management Rules

These rules are ABSOLUTE and NON-NEGOTIABLE. NO EXCEPTIONS.

## 1. State Location

### Member ID
- EXISTS ONLY AT TOP LEVEL STATE
- NEVER stored in instance variables
- NEVER duplicated anywhere
- NEVER passed to other components

### Channel Info
- EXISTS ONLY AT TOP LEVEL STATE
- NEVER duplicated anywhere
- NEVER stored in parts
- NEVER passed to other components

## 2. State Access

- ONLY use state.get() for access
- NO attribute access (state.member_id)
- NO instance variables storing state
- NO state transformation
- NO state duplication
- NO passing state down
- NO manual validation of state.get() results (handled by StateManager)

## 3. Validation Through State

### Core Principle
All validation happens through state updates. If you need to validate something, update the state with it and let StateManager validate.

### Rules
- NO direct validation of values
- NO manual validation before/after state.get()
- NO validation helper functions
- NO cleanup code
- NO error recovery
- NO state fixing

### How It Works
StateManager automatically:
- Validates all state updates
- Validates before state access
- Validates critical fields
- Raises StateException for invalid state

### Examples
```python
# WRONG - Manual validation
def validate_amount(amount: str) -> bool:
    return amount.isdigit() and float(amount) > 0

# CORRECT - Validate through state update
def process_amount(state_manager: Any, amount: str) -> None:
    state_manager.update_state({
        "flow_data": {
            "input": {
                "amount": amount  # StateManager validates
            }
        }
    })

# WRONG - Manual validation after get
def get_amount(state_manager: Any) -> float:
    amount = state_manager.get("amount")
    if not amount:  # NO manual validation!
        raise ValueError("Missing amount")
    return float(amount)

# CORRECT - Let StateManager validate
def get_amount(state_manager: Any) -> float:
    return state_manager.get("flow_data")["amount"]  # StateManager validates
```

## 4. Stateless Handlers

- ONLY use pure functions
  ```python
  # CORRECT
  def handle_message(state_manager: Any, message: str) -> Response:
      return process(state_manager.get("data"))

  # WRONG
  class MessageHandler:
      def __init__(self, state_manager):
          self.state = state_manager  # NO instance state!
  ```

- NO class state/instance variables
  ```python
  # CORRECT
  def get_channel_id(state_manager: Any) -> str:
      return state_manager.get("channel")["identifier"]

  # WRONG
  class Handler:
      def __init__(self, state_manager):
          self.channel = state_manager.get("channel")  # NO stored state!
  ```

- NO handler instantiation
  ```python
  # CORRECT
  result = message_handler.process_message(state_manager, text)

  # WRONG
  handler = MessageHandler(state_manager)  # NO instantiation!
  result = handler.process_message(text)
  ```

- State manager is ONLY shared component
  ```python
  # CORRECT
  def handle_action(state_manager: Any) -> Response:
      # Only state_manager is passed between components
      return process_action(state_manager)

  # WRONG
  def handle_action(state_manager, stored_data):  # NO extra state!
      return process_action(state_manager, stored_data)
  ```

- Clear module boundaries
  ```python
  # auth_handlers.py - Authentication functions
  def handle_login(state_manager: Any): pass

  # message_handler.py - Message processing
  def process_message(state_manager: Any): pass
  ```

## 5. Error Handling

- Fix ROOT CAUSES only
- NO symptom fixes
- NO partial fixes
- NO error hiding
- Clear error messages
- Fail fast and clearly

## Pre-Change Checklist

STOP and verify before ANY code change:

1. State Location
   - [ ] member_id ONLY at top level?
   - [ ] channel info ONLY at top level?
   - [ ] NO new state duplication?

2. State Access
   - [ ] ONLY using state.get()?
   - [ ] NO attribute access?
   - [ ] NO instance variables?

3. State Changes
   - [ ] NO state duplication?
   - [ ] NO state transformation?
   - [ ] NO state passing?

4. Handler Implementation
   - [ ] Using pure functions?
   - [ ] NO class state?
   - [ ] NO handler instantiation?
   - [ ] Clear module boundaries?

5. Validation
   - [ ] Validating at boundaries?
   - [ ] Validating before access?
   - [ ] NO cleanup code?

6. Error Handling
   - [ ] Fixing root cause?
   - [ ] NO symptom fixes?
   - [ ] Clear error messages?


## Enforcement

These rules are enforced through:
1. Code review
2. Static analysis
3. Runtime validation
4. Logging/monitoring
5. Error tracking

NO EXCEPTIONS. NO SPECIAL CASES. NO COMPROMISES.
