"""Messaging constants and command recognition patterns"""

# Greeting Commands
GREETING_COMMANDS = {
    "menu", "memu", "hi", "hie", "cancel", "home", "hy",
    "reset", "hello", "x", "c", "no", "No", "n", "N",
    "hey", "y", "yes", "retry"
}

# Action Commands
ACTION_COMMANDS = {
    "accept": {"yes", "y", "accept", "approve"},
    "decline": {"no", "n", "decline", "reject"},
    "cancel": {"x", "c", "cancel", "stop"}
}

__all__ = [
    'GREETING_COMMANDS',
    'ACTION_COMMANDS'
]
