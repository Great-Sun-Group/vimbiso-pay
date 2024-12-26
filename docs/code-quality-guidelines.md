# Code Quality Guidelines

## 1. Complete Analysis Before Changes

- Map the entire problem space first
- Identify all affected components
- Plan one comprehensive change
- Consider all edge cases and interactions

## 2. Single File Edit Rule

- No partial/incremental changes
- Write complete solution in one edit
- Include all imports, types, error handling
- Test full flow path

## 3. State Management Rules

- Maintain single source of truth
- Use consistent types throughout
- Handle all edge cases upfront
- Ensure clean state transitions
- Validate state at boundaries

## 4. Error Handling Rules

- Fix root causes not symptoms
- Add proper error context
- Log meaningful messages
- Enable recovery paths

## 5. Code Organization Rules

- Keep related code together
- Use clear type hints
- Document key decisions
- Follow consistent patterns

## Implementation

When implementing changes:

1. First analyze the complete problem:
   - Read all relevant documentation
   - Map dependencies and interactions
   - Identify potential edge cases
   - Consider error scenarios

2. Plan the complete solution:
   - Design full implementation upfront
   - Include all necessary components
   - Consider all state transitions
   - Plan error handling strategy

3. Write the complete change:
   - Make all changes in one edit
   - Include all imports and types
   - Add comprehensive error handling
   - Document key decisions

4. Verify the implementation:
   - Test full flow path
   - Validate state transitions
   - Check error handling
   - Verify logging and monitoring

## Examples

### Bad: Incremental Changes

```python
# Change 1: Add new field
class State:
    id: str

# Change 2: Add type hint
class State:
    id: str
    data: Dict[str, Any]

# Change 3: Add validation
class State:
    id: str
    data: Dict[str, Any]

    def validate(self):
        if not self.id:
            raise ValueError("Missing id")
```

### Good: Complete Change

```python
class State:
    """State management with validation

    Attributes:
        id: Unique identifier
        data: State data dictionary
    """
    def __init__(self, id: str, data: Dict[str, Any]):
        self.id = id
        self.data = data
        self.validate()

    def validate(self) -> None:
        """Validate state invariants

        Raises:
            ValueError: If validation fails
        """
        if not self.id:
            raise ValueError("Missing id")
        if not isinstance(self.data, dict):
            raise ValueError("Data must be dictionary")
```

## Benefits

Following these guidelines ensures:

- More reliable code
- Fewer bugs and regressions
- Better maintainability
- Clearer implementation intent
- More efficient development
