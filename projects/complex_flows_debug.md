# Complex Flow Patterns Debug Reference

## CredEx Offer Flow Example

The CredEx Offer Flow (`app/services/whatsapp/handlers/credex/offer_flow_v2.py`) demonstrates advanced patterns for complex WhatsApp interactions.

### Flow Architecture

```
┌─────────────────────┐
│   CredEx Flow      │
├─────────────────────┤
│ - Transaction Svc  │
│ - CredEx Svc      │
│ - State Svc       │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│     Flow Steps      │
├─────────────────────┤
│ 1. Amount Input    │
│ 2. Handle Input    │
│ 3. Confirmation    │
└─────────────────────┘
```

## Common Issues & Debug Steps

### 1. Service Initialization Issues

**Symptoms:**
- Service not initialized errors
- Missing service functionality
- Null service references
- Failed service operations

**Debug Steps:**
```python
def debug_services(flow: CredexOfferFlow) -> None:
    """Debug service initialization"""
    print("Service Status:")
    print(f"Transaction Service: {bool(flow.transaction_service)}")
    print(f"CredEx Service: {bool(flow.credex_service)}")
    print(f"State Service: {bool(flow.state_service)}")

    # Test service operations
    if flow.credex_service:
        try:
            # Test basic operation
            success, _ = flow.credex_service._member.validate_handle("test")
            print(f"CredEx Service Test: {success}")
        except Exception as e:
            print(f"CredEx Service Error: {str(e)}")
```

### 2. Profile Data Issues

**Symptoms:**
- Missing member ID
- Invalid account info
- Failed initialization
- State corruption

**Debug Steps:**
```python
def debug_profile_initialization(flow: CredexOfferFlow, profile_data: Dict) -> None:
    """Debug profile initialization"""
    # Test member ID extraction
    member_id = flow._extract_member_id(profile_data)
    print(f"Member ID: {member_id}")

    # Test account info extraction
    account_id, account_name = flow._extract_sender_account_info(profile_data)
    print(f"Account ID: {account_id}")
    print(f"Account Name: {account_name}")

    # Check state updates
    print("\nState after initialization:")
    print(f"Authorizer ID: {flow.state.get('authorizer_member_id')}")
    print(f"Sender Account: {flow.state.get('sender_account')}")
```

### 3. Input Processing Issues

**Symptoms:**
- Invalid amount formats
- Handle validation failures
- Transform errors
- Missing data

**Debug Steps:**
```python
def debug_input_processing(flow: CredexOfferFlow) -> None:
    """Debug input processing"""
    # Test amount validation
    test_amounts = ["100", "USD 100", "invalid", "XAU 1.5"]
    print("Amount Validation:")
    for amount in test_amounts:
        valid = flow._validate_amount(amount)
        print(f"'{amount}': {valid}")
        if valid:
            transformed = flow._transform_amount(amount)
            print(f"Transformed: {transformed}")

    # Test handle validation
    test_handles = ["valid_handle", "invalid handle", "123456789"]
    print("\nHandle Validation:")
    for handle in test_handles:
        valid = flow._validate_handle(handle)
        print(f"'{handle}': {valid}")
```

## Implementation Patterns

### 1. Service Injection Pattern
```python
class CredexOfferFlow(Flow):
    """Service injection pattern"""
    def __init__(self, id: str, steps: list):
        super().__init__(id, self._create_steps())
        # Services injected after initialization
        self.transaction_service = None
        self.credex_service = None
        self.state_service = None
```

### 2. Profile Initialization Pattern
```python
def initialize_from_profile(self, profile_data: Dict[str, Any]) -> None:
    """Profile initialization pattern"""
    if not profile_data:
        return

    # Extract and validate member ID
    member_id = self._extract_member_id(profile_data)
    if member_id:
        current_state = self.state
        current_state["authorizer_member_id"] = member_id
        self.state = current_state

    # Extract and validate account info
    account_id, account_name = self._extract_sender_account_info(profile_data)
    if account_id:
        current_state = self.state
        current_state["sender_account_id"] = account_id
        self.state = current_state
```

### 3. State Update Pattern
```python
def _update_service_state(self, data: Dict[str, Any], update_from: str = None) -> None:
    """State update pattern"""
    try:
        if self.state_service and self.state.get("phone"):
            # Create new state with essential data
            current_state = {
                "profile": data,
                "last_refresh": True
            }

            # Get preserved fields
            clean_state = self._get_clean_state()
            current_state.update(clean_state)

            # Update with proper context
            self.state_service.update_state(
                user_id=self.state.get("phone"),
                new_state=current_state,
                stage=StateStage.MENU.value,
                update_from=update_from
            )
    except Exception as e:
        logger.error(f"State update error: {str(e)}")
```

## Testing Strategy

### 1. Service Integration Tests
```python
def test_service_integration():
    """Test service integration"""
    flow = CredexOfferFlow("test", [])

    # Test service injection
    flow.credex_service = MockCredexService()
    flow.state_service = MockStateService()

    # Test basic operations
    success, _ = flow.credex_service._member.validate_handle("test")
    assert success

    # Test state updates
    flow.state = {"phone": "1234567890"}
    flow._update_service_state({"test": "data"})
    assert flow.state_service.get_state("1234567890")
```

### 2. Profile Initialization Tests
```python
def test_profile_initialization():
    """Test profile initialization"""
    flow = CredexOfferFlow("test", [])

    # Test with valid profile
    profile = {
        "action": {
            "details": {"memberID": "test_member"}
        },
        "dashboard": {
            "accounts": [{
                "success": True,
                "data": {
                    "accountID": "test_account",
                    "accountName": "Test Account"
                }
            }]
        }
    }

    flow.initialize_from_profile(profile)
    assert flow.state.get("authorizer_member_id") == "test_member"
    assert flow.state.get("sender_account_id") == "test_account"
```

### 3. Transaction Creation Tests
```python
def test_transaction_creation():
    """Test transaction creation"""
    flow = CredexOfferFlow("test", [])

    # Set up required state
    flow.state = {
        "amount": {"amount": 100, "denomination": "USD"},
        "handle": {
            "handle": "test_handle",
            "receiver_account_id": "receiver_123",
            "recipient_name": "Test Recipient"
        },
        "authorizer_member_id": "auth_123",
        "sender_account_id": "sender_123",
        "confirm": {"confirmed": True}
    }

    # Test transaction creation
    offer = flow.create_transaction()
    assert offer is not None
    assert offer.amount == 100
    assert offer.denomination == "USD"
    assert offer.receiver_account_id == "receiver_123"
