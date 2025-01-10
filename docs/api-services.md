# API Services and Architecture

The API service architecture integrates with the central flow management system  through API components that handle external service communication while maintaining clear boundaries and state management.

## Core Integration

```
flow/headquarters.py  <-- Flow Management & Component Orchestration
           ↓
components/api/  <-- API Components (login, onboard, etc.)
           ↓
      base.py  <-- API Request Handling & Response Processing
           ↓
  api_response.py  <-- Unified State Management
           ↓
     State Updates
     ├── Dashboard Section  <-- Member State (accounts, profile, etc.)
     └── Action Section    <-- Operation Results (status, details, etc.)
```

## Core Principles

1. **API Response Structure**
- All responses include two sections:
  * dashboard -> Member state after operation
  * action -> Operation results and details
- Both sections handled by api_response.py:
  * Updates member state from dashboard section
  * Updates operation results from action section
- Clear validation and state management

2. **Dashboard as Source of Truth**
- Member state managed through api_response.py
- All member data comes from dashboard section
- Components read from dashboard state
- No direct member state management
- Single source for member info

3. **Action Data Management**
- Operation results managed through api_response.py
- Components get action data for flow
- Operation details in action state
- Clear operation tracking
- Flow control through actions

4. **Flow Integration**
- API components activated by headquarters.py
- Results can determine next flow step
- Clear state boundaries
- Standard validation patterns

## API Component Pattern
1. Get member data from dashboard
2. Make API call directly
3. Let handler update state
4. Use action data for flow control
5. Handle errors through ErrorHandler

## Implementation Guide

### API Response Flow
1. headquarters.py activates API component
2. Component makes API call through base.make_api_request
3. Response contains dashboard and action sections
4. base.handle_api_response routes to api_response.py:
   - update_state_from_response -> Updates both dashboard and action data
5. Component returns result to headquarters.py for flow control when necessary
6. flow/headquarters.py determines next step based on result

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

3. core/api/api_response.py - State Management
   - How member and operation state is updated
   - How validation works
   - Single source of truth for both dashboard and action data

# #Mistakes to avoid:
1. DON'T bypass headquarters.py - all flow goes through it
2. DON'T add extra API modules - make calls directly
3. DON'T add extra state validation - use handlers
4. DON'T duplicate error handling - use ValidationResult
5. DON'T mix component responsibilities
