# Action Handler Refactoring Plan

## Current Issues

1. **Code Organization**
   - Single large file (action_handlers.py) with multiple responsibilities
   - Methods are too long and complex
   - Hard to maintain and test
   - No clear separation of concerns

2. **Technical Debt**
   - Star imports make dependencies unclear
   - Undefined types and missing type hints
   - Inconsistent error handling
   - Repeated code patterns
   - Large nested if-else blocks
   - Documentation mixed with code

3. **State Management**
   - State logic scattered throughout handlers
   - Inconsistent state update patterns
   - No clear state lifecycle

## Proposed Architecture

### 1. Module Structure
```
app/core/message_handling/
├── handlers/
│   ├── __init__.py
│   ├── base.py           # Base handler with common functionality
│   ├── credex.py         # Credex-specific actions
│   ├── profile.py        # Profile management
│   └── transaction.py    # Transaction handling
├── models/
│   ├── __init__.py
│   ├── state.py          # State management models
│   ├── credex.py         # Credex-related models
│   └── profile.py        # Profile-related models
├── services/
│   ├── __init__.py
│   ├── state.py          # State management service
│   └── error.py          # Error handling service
└── utils/
    ├── __init__.py
    ├── decorators.py     # Common decorators (e.g., error handling)
    └── validators.py     # Input validation
```

### 2. Key Components

#### BaseActionHandler
```python
class BaseActionHandler:
    def __init__(self, service: CredexBotService):
        self.service = service
        self.state_manager = StateManager()
        self.error_handler = ErrorHandler()

    @error_handler
    def handle_action(self, action: str) -> ActionResponse:
        pass

    def update_state(self, new_state: State) -> None:
        pass
```

#### State Management
```python
@dataclass
class State:
    profile: Optional[Profile]
    current_account: Optional[Account]
    stage: str
    option: str

class StateManager:
    def update_state(self, state: State) -> None:
        pass

    def get_state(self) -> State:
        pass
```

#### Error Handling
```python
class ErrorHandler:
    def handle_error(self, error: Exception) -> ActionResponse:
        pass

@dataclass
class ActionResponse:
    success: bool
    message: str
    data: Optional[Dict]
```

## Implementation Plan

### Phase 1: Foundation
1. Create new module structure
2. Set up base classes and interfaces
3. Define core models and types
4. Implement state management service

### Phase 2: Handler Migration
1. Create BaseActionHandler
2. Migrate Credex actions to CredexActionHandler
3. Migrate Profile actions to ProfileActionHandler
4. Migrate Transaction actions to TransactionActionHandler

### Phase 3: Error Handling
1. Implement ErrorHandler service
2. Add error handling decorators
3. Update handlers to use new error handling

### Phase 4: State Management
1. Implement StateManager service
2. Update handlers to use new state management
3. Add state validation and type checking

### Phase 5: Testing & Documentation
1. Add unit tests for all new components
2. Add integration tests for handlers
3. Update documentation
4. Add type hints and docstrings

### Proposed Solutions

#### 1. Type-Safe Models
```python
@dataclass
class CredexOffer:
    credex_id: str
    initial_amount: str
    counterparty_name: str
    secured: bool

@dataclass
class BulkAcceptPayload:
    signer_id: str
    credex_ids: List[str]

    @classmethod
    def from_offers(cls, signer_id: str, offers: List[CredexOffer]) -> 'BulkAcceptPayload':
        return cls(
            signer_id=signer_id,
            credex_ids=[offer.credex_id for offer in offers]
        )
```

#### 2. Improved Error Handling
```python
class CredexActionHandler(BaseActionHandler):
    @error_handler
    async def accept_all_incoming_offers(self) -> ActionResponse:
        # Get current state with validation
        state = await self.state_manager.get_validated_state()

        # Ensure profile exists
        if not state.profile:
            return ActionResponse(
                success=False,
                message="Profile information missing. Please try again.",
                error_code="PROFILE_MISSING"
            )

        # Get pending offers with validation
        offers = await self.get_pending_offers(state.current_account)
        if not offers:
            return ActionResponse(
                success=False,
                message="No pending offers found.",
                error_code="NO_PENDING_OFFERS"
            )

        # Create validated payload
        payload = BulkAcceptPayload.from_offers(
            signer_id=state.profile.member_id,
            offers=offers
        )

        # Execute bulk accept with proper error handling
        try:
            result = await self.api_interactions.accept_bulk_credex(payload)
            return self.format_success_response(result)
        except ApiError as e:
            return self.format_error_response(e)
```

#### 3. State Management
```python
class StateManager:
    async def get_validated_state(self) -> State:
        """Get current state with validation and auto-refresh if needed"""
        state = await self.get_state()

        if not state.is_valid():
            # Attempt to refresh state
            await self.refresh_state()
            state = await self.get_state()

            if not state.is_valid():
                raise StateValidationError("Unable to obtain valid state")

        return state

    def is_valid(self) -> bool:
        """Check if current state is valid for operations"""
        return (
            self.profile is not None and
            self.current_account is not None and
            self.profile.member_id is not None
        )
```

#### 4. Response Formatting
```python
class CredexResponseFormatter:
    def format_success_response(self, api_result: Dict) -> ActionResponse:
        """Format successful bulk accept response"""
        return ActionResponse(
            success=True,
            message=self.format_success_message(api_result),
            data={
                "accepted_count": len(api_result.get("accepted", [])),
                "failed_count": len(api_result.get("failed", [])),
                "balance_update": self.format_balance_update(api_result)
            }
        )

    def format_error_response(self, error: ApiError) -> ActionResponse:
        """Format error response with helpful message"""
        return ActionResponse(
            success=False,
            message=self.get_user_friendly_error_message(error),
            error_code=error.code,
            data={
                "error_details": error.details,
                "retry_allowed": error.is_retryable
            }
        )
```

## Benefits

1. **Maintainability**
   - Clear separation of concerns
   - Smaller, focused modules
   - Easier to test and debug
   - Better code organization

2. **Type Safety**
   - Full type hints coverage
   - Runtime type checking
   - Better IDE support
   - Easier to catch bugs early

3. **Error Handling**
   - Consistent error handling patterns
   - Better error messages
   - Centralized error management
   - Easier debugging

4. **State Management**
   - Clear state lifecycle
   - Type-safe state updates
   - Better state validation
   - Easier to track state changes

5. **Testing**
   - Easier to write unit tests
   - Better test coverage
   - Isolated components
   - Mockable dependencies

## Migration Strategy

1. **Incremental Approach**
   - Implement new structure alongside existing code
   - Migrate one handler at a time
   - Keep backwards compatibility
   - Roll out gradually

2. **Testing Strategy**
   - Write tests before migration
   - Ensure feature parity
   - Compare old vs new behavior
   - Automated testing

3. **Rollback Plan**
   - Keep old code until fully migrated
   - Feature flags for new code
   - Easy rollback mechanism
   - Monitor for issues

## Success Metrics

1. **Code Quality**
   - Reduced cyclomatic complexity
   - Improved test coverage
   - Fewer dependencies
   - Better type safety

2. **Maintenance**
   - Faster bug fixes
   - Easier feature additions
   - Better documentation
   - Clearer code ownership

3. **Performance**
   - Reduced memory usage
   - Better error handling
   - Faster state updates
   - Improved response times

## Next Steps

1. Review and approve refactoring plan
2. Set up new module structure
3. Begin Phase 1 implementation
4. Schedule regular progress reviews
5. Plan deployment strategy
