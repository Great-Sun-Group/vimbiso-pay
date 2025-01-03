# Components

## Core Principles

1. **Clear Boundaries**
- Components handle validation
- Components convert data
- Components manage errors
- NO business logic
- NO state management
- NO flow control

2. **Simple Structure**
- Minimal interfaces
- Clear validation
- Standard conversion
- NO complex hierarchies
- NO redundant wrapping
- NO state duplication

3. **Pure Functions**
- Stateless validation
- Clear conversion
- Standard errors
- NO stored state
- NO side effects
- NO manual handling

4. **Central Registry**
- Single component registry
- Standard validation
- Clear interfaces
- NO manual creation
- NO local state
- NO mixed concerns

## Component Types

```python
class ComponentRegistry:
    """Central component management"""

    COMPONENTS = {
        # Input components
        "AmountInput": {
            "type": "input",
            "validates": ["amount"],
            "converts_to": ["amount", "denomination"]
        },
        "HandleInput": {
            "type": "input",
            "validates": ["handle"],
            "converts_to": ["handle"]
        },
        "SelectInput": {
            "type": "input",
            "validates": ["selection"],
            "converts_to": ["selected_id"]
        },
        "ConfirmInput": {
            "type": "input",
            "validates": ["confirmation"],
            "converts_to": ["confirmed"]
        }
    }
```

## Implementation

### 1. Base Component
```python
class Component:
    """Base component interface with validation tracking"""

    def __init__(self, component_type: str):
        self.type = component_type
        self.validation_state = {
            "in_progress": False,
            "error": None,
            "attempts": 0,
            "last_attempt": None
        }

    def validate(self, value: Any) -> ValidationResult:
        """Validate component input with tracking

        Args:
            value: Value to validate

        Returns:
            ValidationResult with validation state

        Example:
            >>> component = TextInput()
            >>> result = component.validate("test")
            >>> result.valid
            True
            >>> result.value
            'test'
            >>> component.validation_state["attempts"]
            1
        """
        # Track validation attempt
        self.validation_state["attempts"] += 1
        self.validation_state["last_attempt"] = value
        self.validation_state["in_progress"] = True

        try:
            # Validate input (implemented by subclasses)
            result = self._validate_input(value)

            # Update validation state
            self.validation_state.update({
                "in_progress": False,
                "error": None if result.valid else result.error
            })

            return result

        except Exception as e:
            # Handle validation error
            self.validation_state.update({
                "in_progress": False,
                "error": {
                    "message": str(e),
                    "details": {
                        "type": "validation_error",
                        "attempts": self.validation_state["attempts"]
                    }
                }
            })
            return ValidationResult.failure(
                message=str(e),
                field="value",
                details={"attempts": self.validation_state["attempts"]}
            )

    def _validate_input(self, value: Any) -> ValidationResult:
        """Validate input (implemented by subclasses)"""
        raise NotImplementedError

    def get_ui_state(self) -> Dict[str, Any]:
        """Get component UI state with validation"""
        return {
            "type": self.type,
            "validation": self.validation_state
        }

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified data with validation state"""
        if self.validation_state["error"]:
            raise ValueError("Cannot convert invalid data")
        return self._convert_value(value)

    def _convert_value(self, value: Any) -> Dict:
        """Convert value (implemented by subclasses)"""
        raise NotImplementedError
```

### 2. Input Components
```python
class AmountInput(Component):
    """Amount input with validation tracking"""

    def _validate_input(self, value: Any) -> ValidationResult:
        """Validate amount with tracking"""
        try:
            # Type validation
            if not isinstance(value, (str, int, float)):
                return ValidationResult.failure(
                    message="Invalid amount type",
                    field="amount",
                    details={
                        "expected_type": "number",
                        "actual_type": type(value).__name__,
                        "attempts": self.validation_state["attempts"]
                    }
                )

            # Convert to float
            amount = float(value)

            # Value validation
            if amount <= 0:
                return ValidationResult.failure(
                    message="Amount must be positive",
                    field="amount",
                    details={
                        "value": amount,
                        "attempts": self.validation_state["attempts"]
                    }
                )

            return ValidationResult.success(amount)

        except ValueError:
            return ValidationResult.failure(
                message="Invalid amount format",
                field="amount",
                details={
                    "value": value,
                    "attempts": self.validation_state["attempts"]
                }
            )

    def _convert_value(self, value: Any) -> Dict:
        """Convert amount with validation"""
        return {
            "amount": float(value),
            "validation": {
                "attempts": self.validation_state["attempts"],
                "last_valid": datetime.utcnow().isoformat()
            }
        }


class HandleInput(Component):
    """Handle input with validation"""

    def validate(self, value: Any) -> Dict:
        if not isinstance(value, str):
            return ErrorHandler.handle_component_error(
                component="handle_input",
                field="handle",
                value=value,
                message="Handle must be text"
            )

        handle = value.strip()
        if not handle:
            return ErrorHandler.handle_component_error(
                component="handle_input",
                field="handle",
                value=value,
                message="Handle required"
            )

        return {"valid": True}

    def to_verified_data(self, value: Any) -> Dict:
        return {
            "handle": value.strip()
        }


class SelectInput(Component):
    """Selection input with validation"""

    def validate(self, value: Any) -> Dict:
        if not isinstance(value, str):
            return ErrorHandler.handle_component_error(
                component="select_input",
                field="selection",
                value=value,
                message="Selection must be text"
            )

        if value not in self.options:
            return ErrorHandler.handle_component_error(
                component="select_input",
                field="selection",
                value=value,
                message="Invalid selection"
            )

        return {"valid": True}

    def to_verified_data(self, value: Any) -> Dict:
        return {
            "selected_id": value
        }


class ConfirmInput(Component):
    """Confirmation input with validation"""

    def validate(self, value: Any) -> Dict:
        if not isinstance(value, bool):
            return ErrorHandler.handle_component_error(
                component="confirm_input",
                field="confirmation",
                value=value,
                message="Confirmation must be boolean"
            )

        return {"valid": True}

    def to_verified_data(self, value: Any) -> Dict:
        return {
            "confirmed": value
        }
```

### 3. Component Factory
```python
def create_component(component_type: str) -> Component:
    """Create component instance"""
    if component_type not in ComponentRegistry.COMPONENTS:
        raise ValueError(f"Unknown component type: {component_type}")

    component_class = globals()[component_type]
    return component_class(component_type)
```

## Component Usage

```python
# Create component
component = create_component("AmountInput")

# Validate input
result = component.validate("100.00")
if "error" in result:
    return result

# Convert to verified data
verified = component.to_verified_data("100.00")
```

## Best Practices

1. **Component Design**
- Single responsibility
- Clear validation
- Standard conversion
- NO business logic
- NO state management
- NO flow control

2. **Error Handling**
- Use ErrorHandler
- Clear boundaries
- Standard formats
- NO manual handling
- NO local recovery
- NO state fixing

3. **Data Conversion**
- Clear conversion
- Type safety
- Standard formats
- NO business logic
- NO validation
- NO state changes

4. **Integration**
- Use component factory
- Standard interfaces
- Clear boundaries
- NO manual creation
- NO state access
- NO flow control

## Integration

Components integrate with:
- Flow framework
- State management
- Error handling
- Message templates
- Input validation

For more details on:
- Flow Framework: [Flow Framework](flow-framework.md)
- State Management: [State Management](state-management.md)
- Error Handling: [Error Handling](error-handling.md)
