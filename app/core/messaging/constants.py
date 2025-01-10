"""Messaging constants and command recognition patterns"""

# Action Commands for message handling
ACTION_COMMANDS = {
    "accept": {"yes", "y", "accept", "approve"},
    "decline": {"no", "n", "decline", "reject"},
    "cancel": {"x", "c", "cancel", "stop"}
}

__all__ = [
    'ACTION_COMMANDS'
]
