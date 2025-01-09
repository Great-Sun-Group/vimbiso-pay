"""Core configuration and state management

This module provides the high-level state management interface.
All state operations should go through StateManager, which:
1. Manages atomic operations
2. Handles state validation
3. Controls flow state
4. Manages channel operations

The architecture follows these principles:
- Single source of truth through StateManager
- Clear boundaries between components
- Strong validation at all levels
- Atomic operations handled internally

Import order matters to avoid circular dependencies:
1. timing.py - Basic timing constants
2. state_manager.py - State management interface
3. config.py - Utility functions
"""

from .timing import (
    ACTIVITY_TTL,
    API_TIMEOUT,
    API_RETRY_DELAY,
    MAX_API_RETRIES,
    FLOW_TIMEOUT,
    MAX_FLOW_RETRIES
)
from .state_manager import StateManager
from .config import get_greeting

__all__ = [
    'StateManager',
    'get_greeting',
    'ACTIVITY_TTL',
    'API_TIMEOUT',
    'API_RETRY_DELAY',
    'MAX_API_RETRIES',
    'FLOW_TIMEOUT',
    'MAX_FLOW_RETRIES'
]
