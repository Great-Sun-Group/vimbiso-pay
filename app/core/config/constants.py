"""Constants and configuration exports

This module exports all constants and configurations used across the application.
Follows proper layering to avoid circular dependencies:
1. timing.py - Basic timing constants
2. recognition.py - Command recognition patterns
3. state_manager.py - State management
4. Utility functions
"""
from typing import Dict, Any

from .timing import (
    ACTIVITY_TTL,
    API_TIMEOUT,
    API_RETRY_DELAY,
    MAX_API_RETRIES,
    FLOW_TIMEOUT,
    MAX_FLOW_RETRIES,
    RATE_LIMIT_WINDOW,
    MAX_REQUESTS_PER_WINDOW
)
from .recognition import (
    GREETING_COMMANDS,
    ACTION_COMMANDS
)
from .config import get_greeting

# Credex action configuration
CREDEX_ACTIONS: Dict[str, Dict[str, Any]] = {
    "accept": {
        "service_method": "accept_credex",
        "confirm_prompt": "accept",
        "cancel_message": "Acceptance cancelled",
        "complete_message": "✅ Offer accepted successfully.",
        "error_prefix": "accept"
    },
    "decline": {
        "service_method": "decline_credex",
        "confirm_prompt": "decline",
        "cancel_message": "Decline cancelled",
        "complete_message": "✅ Offer declined successfully.",
        "error_prefix": "decline"
    },
    "cancel": {
        "service_method": "cancel_credex",
        "confirm_prompt": "cancel",
        "cancel_message": "Cancellation cancelled",
        "complete_message": "✅ Offer cancelled successfully.",
        "error_prefix": "cancel"
    }
}

__all__ = [
    # Timing constants
    'ACTIVITY_TTL',
    'API_TIMEOUT',
    'API_RETRY_DELAY',
    'MAX_API_RETRIES',
    'FLOW_TIMEOUT',
    'MAX_FLOW_RETRIES',
    'RATE_LIMIT_WINDOW',
    'MAX_REQUESTS_PER_WINDOW',

    # Recognition patterns
    'GREETING_COMMANDS',
    'ACTION_COMMANDS',

    # Action configurations
    'CREDEX_ACTIONS',

    # Utility functions
    'get_greeting'
]
