"""Constants and state management exports"""
from typing import Dict, Any

from .config import (
    get_greeting,
    atomic_state,
)
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
from .state_manager import StateManager
from .state_utils import merge_updates, get_channel_info

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
    'get_greeting',
    'atomic_state',
    'StateManager',
    'merge_updates',
    'get_channel_info',
]
