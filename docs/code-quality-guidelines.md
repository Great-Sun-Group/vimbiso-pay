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

- Member ID ONLY at top level
- Channel info ONLY at top level
- NO state duplication
- NO state transformation
- NO state passing
- NO manual validation

## 4. Error Handling Rules

- Let StateManager validate
- NO manual validation
- NO error recovery
- NO state fixing
- NO cleanup code
- Clear error messages

## 5. Code Organization Rules

- Keep related code together
- Use clear type hints
- Document key decisions
- Follow consistent patterns
- NO validation helpers
- NO error recovery

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

### Bad: Manual Validation

```python
# WRONG - Manual validation
def validate_state(state: Dict[str, Any]) -> bool:
    if not state.get("member_id"):
        return False
    if not isinstance(state.get("data"), dict):
        return False
    return True

# WRONG - Error recovery
def process_state(state: Dict[str, Any]) -> None:
    if not validate_state(state):
        state["member_id"] = "default"
        state["data"] = {}
```

### Good: StateManager Validation

```python
def process_state(state_manager: Any) -> None:
    """Process state through StateManager validation

    Args:
        state_manager: State manager instance

    Raises:
        StateException: If validation fails
    """
    # Let StateManager validate state
    state_manager.update_state({
        "member_id": "unique_id",  # ONLY at top level
        "data": {
            "field": "value"
        }
    })
```

## Benefits

Following these guidelines ensures:

- More reliable code
- Fewer bugs and regressions
- Better maintainability
- Clearer implementation intent
- More efficient development
