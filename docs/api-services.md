# Service & API Architecture

## Overview

The service and API architecture integrates with the central flow management system (flow/headquarters.py) through API components that handle external service communication while maintaining clear boundaries and state management.

## Core Integration

```
headquarters.py  <-- Flow Management
      ↓
API Components   <-- Service Integration
      ↓
base.py         <-- API Handling
  ├── dashboard.py  (Member State)
  └── action.py     (Operation Results)
```

## Core Principles

1. **API Response Structure**
- All responses include two sections:
  * dashboard -> Member state after operation
  * action -> Operation results and details
- Each section handled by dedicated module:
  * dashboard.py -> Updates member state
  * action.py -> Updates operation results
- Clear separation of concerns

2. **Dashboard as Source of Truth**
- dashboard.py handles member state
- All member data comes from dashboard
- Components read from dashboard
- No direct member state management
- Single source for member info

3. **Action Data Management**
- action.py handles operation results
- Components get action data for flow
- Operation details in action state
- Clear operation tracking
- Flow control through actions

4. **Flow Integration**
- API components activated by headquarters.py
- Results can determine next flow step
- Clear state boundaries
- Standard validation patterns

## Component Patterns

### API Component Pattern
1. Get member data from dashboard
2. Make API call directly
3. Let handlers update state
4. Use action data for flow control
5. Handle errors through ErrorHandler

### Display Component Pattern
1. Get display data from state
2. Send through messaging service
3. Return success
4. Handle errors through ErrorHandler

## Implementation Guide

### API Response Flow
1. headquarters.py activates API component
2. Component makes API call through base.make_api_request
3. Response contains dashboard and action sections:
```python
{
    "data": {
        "dashboard": {  # Member state after operation
            "member": { "memberID": "..." },
            "accounts": [...],
            ...
        },
        "action": {    # Operation results
            "id": "...",
            "type": "...",
            "details": {...}
        }
    }
}
```
4. base.handle_api_response routes to handlers:
   - dashboard.update_dashboard_from_response -> Updates member state
   - action.update_action_from_response -> Updates operation state
5. Component returns result to headquarters.py for flow control when necessary
6. flow/headquarters.py determines next step based on result

### State Management
1. Dashboard State (Source of Truth)
   - Member core data
   - Account information
   - Balance details
   - Updated by dashboard.py

2. Action State (Most Recent API Operation Results)
   - Operation ID
   - Operation type
   - Timestamps
   - Details/results
   - Updated by action.py

3. Component State (Minimal)
   - Reads from dashboard
   - Uses action data
   - Clear boundaries
   - No state duplication or passing


## Code Reading Guide

Before modifying service-related functionality, read these files in order:

1. core/flow/headquarters.py - Flow Management
   - How components are activated
   - How flow control works
   - How state is delegated

2. core/api/base.py - API Handling
   - How to make API calls
   - How responses are processed
   - How handlers are called

3. core/api/dashboard.py - Dashboard State
   - How member state is updated
   - How validation works
   - Single source of truth

4. core/api/action.py - Action State
   - How operation results are handled
   - How flow data is managed
   - Clear operation tracking

Common mistakes to avoid:
1. DON'T bypass headquarters.py - all flow goes through it
2. DON'T add extra API modules - make calls directly
3. DON'T add extra state validation - use handlers
4. DON'T duplicate error handling - use ValidationResult
5. DON'T mix component responsibilities

For implementation details, see:
- [Flow Framework](flow-framework.md) - Component activation and flow control
- [State Management](state-management.md) - State validation and flow control
