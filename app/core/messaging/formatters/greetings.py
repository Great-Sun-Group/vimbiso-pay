"""Greeting message formatting

This module handles the generation of time-appropriate greeting messages.
Used by display components and message formatters.
"""

import logging
from datetime import datetime, timedelta

from core.error.exceptions import SystemException

logger = logging.getLogger(__name__)


def get_greeting(name: str) -> str:
    """Get time-appropriate greeting

    Args:
        name: User's name to include in greeting

    Returns:
        Time-appropriate greeting message

    Raises:
        SystemException: If greeting generation fails
    """
    try:
        current_time = datetime.now() + timedelta(hours=2)
        hour = current_time.hour

        if 5 <= hour < 12:
            return f"Good Morning {name} 🌅"
        elif 12 <= hour < 18:
            return f"Good Afternoon {name} ☀️"
        elif 18 <= hour < 22:
            return f"Good Evening {name} 🌆"
        else:
            return f"Hello There {name} 🌙"

    except Exception as e:
        logger.error(f"Failed to generate greeting: {str(e)}")
        raise SystemException(
            message="Failed to generate greeting",
            code="GREETING_ERROR",
            service="messaging.formatters",
            action="get_greeting"
        ) from e
