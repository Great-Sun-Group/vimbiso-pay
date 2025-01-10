# Messaging System

The messaging system provides a channel-agnostic way to handle all user communication through a layered architecture:

```
core/messaging/           <-- Core Messaging System
├── service.py               (Service Orchestration)
├── base.py                  (Base Implementation)
├── interface.py             (Core Interface)
└── types.py                (Message Types)
```

## Core Architecture

### 1. Service Orchestration (service.py)
Coordinates channel-specific implementations and maintains the layered architecture by:
- Routing messages to appropriate channels
- Managing service lifecycle and state integration
- Providing consistent error handling patterns

### 2. Base Implementation (base.py)
Provides common functionality and standard patterns for:
- Message handling and validation
- Error management
- State integration

### 3. Core Interface (interface.py)
Defines the messaging contract and boundaries for:
- Message operations
- Validation requirements
- Error handling patterns

### 4. Message Types (types.py)
Defines core message structures including:
- Complete message formats
- Recipient specifications
- Content type definitions
- Required metadata

## Message Types

### 1. Text Messages
Simple text content with URL preview options and format validation

### 2. Interactive Messages
Messages with interactive elements like:
- Button actions
- List selections
- Header/footer components

### 3. Template Messages
Pre-defined message templates supporting:
- Named template definitions
- Multi-language support
- Dynamic content insertion
- Parameter validation

## Channel Implementations

The system supports multiple messaging channels through dedicated service implementations:

```
app/services/
├── sms/                 <-- SMS Channel Implementation
└── whatsapp/           <-- WhatsApp Channel Implementation
```

Each channel implementation:
- Extends the base messaging service
- Implements channel-specific formatting
- Handles platform-specific requirements
- Maintains consistent validation patterns

### WhatsApp Service
Located in `app/services/whatsapp/`, provides:
- Rich message formatting
- Interactive components
- Template message support
- Media handling

### SMS Service
Located in `app/services/sms/`, not yet implemented, will handle formatting of higher-complexity messages into SMS structures, and message delivery.

## Core Principles

### 1. Channel Agnostic Design
- Abstract message types for consistency
- Channel-specific implementations for platform requirements
- Standardized validation across channels

### 2. State Management
- Centralized state access through state_manager
- Consistent validation patterns
- Clear state boundaries

### 3. Error Handling
- Standard error patterns with clear context
- Proper error tracking
- Complete validation coverage

## Implementation Guidelines

1. Use appropriate message types and validate content
2. Extend base service for new channels
3. Maintain state integration through proper utils
4. Follow standard error handling patterns
5. Implement complete validation coverage
