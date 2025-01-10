# Core Architecture

## System Overview

The Vimbiso ChatServer is built around a central flow management system that coordinates all user interactions and system operations.

### Core Components

```
core/flow/headquarters.py  <-- Central Flow Management
 ├── state/manager.py      (State Management)
 ├── components/           (Component System)
 ├── api/                  (API Integration)
 └── messaging/            (Messaging System)
```

## Central Flow Management (flow/headquarters.py)

The core of the system is the flow management module that:
1. Manages member flows through the application
2. Activates components at each step
3. Determines next steps through branching logic
4. Delegates data management to state manager
5. Delegates action management to components

### Component Activation

Components are self-contained with responsibility for their own:
- Business logic and validation
- Activation of shared utilities/helpers/services
- State access to communicate with other parts of the system
- State access for in-component loop management
- State writing to leave flow headquarters with results
- Error handling

## Core Subsystems

### 1. State Management (manager.py)
The state manager is responsible for:
- Data structure
- Data validation
- Data storage
- Data retrieval

Key Principles:
- All operations go through state_manager
- Credentials exist ONLY in state
- No direct passing of sensitive data
- State validation through updates
- Progress tracking through state
- Validation tracking through state

### 2. Component System (components/)
Components handle specific operations with clear boundaries:

- **Display Components**
  * UI and messaging
  * Format data for display
  * No state modifications

- **Input Components**
  * Input validation
  * State updates
  * Format validation

- **API Components**
  * External API calls
  * Response handling
  * State updates

- **Confirm Components**
  * User confirmations
  * Flow control
  * State updates

Standard Component Patterns:
- All operations wrapped in try/except
- All errors handled through ErrorHandler
- All results returned as ValidationResult

### 3. API Integration (api/)
Handles external service communication:
- State-based API integration
- Credential management
- Response handling
- Error management

### 4. Messaging System (messaging/)
Manages all user communication:
- Channel-agnostic messaging
- Template management
- Interactive elements
- State-based messaging

## Detailed Documentation

- [State Management](state-management.md) - Detailed state management patterns
- [Flow Framework](flow-framework.md) - Component activation and flow control
- [Service Architecture](service-architecture.md) - Service integration patterns

## Infrastructure

- [Security](infrastructure/security.md) - Security measures and best practices
- [Docker](infrastructure/docker.md) - Container configuration and services
- [Deployment](infrastructure/deployment.md) - Deployment process and infrastructure
- [Redis](infrastructure/redis-memory-management.md) - Redis configuration and management
