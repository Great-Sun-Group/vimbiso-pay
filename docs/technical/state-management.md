# State Management

## Overview

VimbisoPay implements a Redis-based state management service to handle:
- User context and conversation state
- Session management with timeouts
- JWT token management
- Conversation flow control

## Architecture

State management is implemented as a dedicated service:
```
app/services/state/
├── interface.py    # Service interface definition
├── service.py      # Main implementation
├── exceptions.py   # Custom exceptions
└── config.py      # Redis configuration
```

## Core Components

### State Service
- Provides interface for state operations (get, set, update, delete)
- Handles Redis interactions and timeouts
- Manages session expiry and cleanup

### User State
- Tracks conversation stage and direction
- Stores user profile and preferences
- Manages authentication tokens
- Handles menu navigation state

## Redis Structure

- User-specific keys with 5-minute timeout
- Stores conversation state and context
- Manages JWT tokens
- Handles session data

## Service Integration

The state service integrates with:
- WhatsApp service for conversation handling
- Transaction service for operation context
- Account service for user data
- Core messaging service for communication

## Error Handling

- Automatic session cleanup on timeout
- State validation on updates
- Recovery mechanisms for failed operations
- Comprehensive error logging

## Security

- 5-minute session timeouts
- Secure token storage
- State isolation per user
- Input validation
