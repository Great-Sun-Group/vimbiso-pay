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

### Account State
- EXISTS ONLY AT TOP LEVEL STATE
- accounts array contains ALL accounts
- active_account_id tracks current account
- NEVER store account data in flow_data
- NEVER duplicate account information
- NEVER pass account data to components
- Registration creates SINGLE personal account
- Login (and other endpoints) may return MULTIPLE accounts

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

#### State Validation Rules
- NO manual validation after state.get() (StateManager handles this)
- NO manual verification of state updates (StateManager handles this)
- NO cleanup code
- NO error recovery
- NO state fixing

#### Flow-Specific Validation
Flow implementations MAY include validation for:
- Business rules (e.g. amount > 0)
- Input formatting (e.g. "100 USD" or "USD 100")
- Data parsing (e.g. converting strings to numbers)
- Domain-specific requirements (e.g. valid denominations)

### How It Works

StateManager automatically:
- Validates state structure
- Validates before state access
- Validates critical fields including:
  - step (must be integer for framework validation)
  - current_step (must be string for flow routing)
  - flow_type (must be string for flow identification)
  - accounts (must be array at top level)
  - active_account_id (must reference valid account)
- Raises StateException for invalid state

Flow implementations:
- Validate business rules
- Parse/format input data
- Enforce domain requirements
- Provide flow-specific error messages

### Examples
```python
# CORRECT - Account access through state
def get_active_account(state_manager: Any) -> Dict[str, Any]:
    """Get active account through state validation"""
    # Get validated state data
    active_id = state_manager.get("active_account_id")
    accounts = state_manager.get("accounts")

    # Find active account (StateManager has already validated it exists)
    return next(
        account for account in accounts
        if account["accountID"] == active_id
    )

# CORRECT - Flow-specific validation
def validate_amount(amount: str) -> Dict[str, Any]:
    """Validate amount according to business rules"""
    valid_denominations = {"USD", "ZWG", "XAU"}
    parts = amount.split()

    if not amount or len(parts) > 2:
        raise StateException("Invalid format. Enter amount with optional denomination")

    # Business logic for parsing amount format
    value = float(parts[0])
    if value <= 0:
        raise StateException("Amount must be greater than 0")

    # Domain-specific denomination validation
    denom = parts[1] if len(parts) > 1 else "USD"
    if denom not in valid_denominations:
        raise StateException(f"Invalid denomination. Supported: {valid_denominations}")

    return {"amount": value, "denomination": denom}

# CORRECT - Update state through StateManager
def store_amount(state_manager: Any, amount: str) -> None:
    # Validate business rules
    amount_data = validate_amount(amount)

    # Let StateManager validate structure
    state_manager.update_state({
        "flow_data": {
            "data": {  # StateManager preserves data structure
                "amount_denom": amount_data  # StateManager validates
            }
        }
    })

    # NO manual verification after update!

# WRONG - Manual state verification
def verify_amount(state_manager: Any) -> None:
    state = state_manager.get("flow_data")
    if not state or "amount_denom" not in state:  # NO manual verification!
        raise StateException("Failed to verify state")
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
   - [ ] accounts array at top level?
   - [ ] active_account_id at top level?
   - [ ] NO account data in flow_data?
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
