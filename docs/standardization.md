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

## 3. Validation

- Validate at boundaries ONLY
- Validate BEFORE accessing state
- NO partial validation
- NO cleanup code
- NO state fixing
- NO error recovery

## 4. Error Handling

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

4. Validation
   - [ ] Validating at boundaries?
   - [ ] Validating before access?
   - [ ] NO cleanup code?

5. Error Handling
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
