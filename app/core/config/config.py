"""Redis configuration and basic constants"""
import logging
from datetime import datetime, timedelta

from core.utils.exceptions import SystemException
from core.utils.redis_atomic import AtomicStateManager
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Cache Configuration
try:
    # Test cache connection
    cache.set('test_key', 'test_value', timeout=5)
    if cache.get('test_key') != 'test_value':
        raise SystemException(
            message="Cache test failed",
            code="CACHE_TEST_ERROR",
            service="config",
            action="test_cache"
        )
    logger.info("Cache connection established successfully")

except Exception as e:
    logger.error(
        "Cache connection error",
        extra={"error": str(e)}
    )
    raise SystemException(
        message="Failed to connect to cache",
        code="CACHE_CONNECT_ERROR",
        service="config",
        action="initialize_cache"
    ) from e

# Initialize atomic state manager
atomic_state = AtomicStateManager(cache)

# TTL Constants
ACTIVITY_TTL = 300  # 5 minutes

# Command Recognition
GREETINGS = {
    "menu", "memu", "hi", "hie", "cancel", "home", "hy",
    "reset", "hello", "x", "c", "no", "No", "n", "N",
    "hey", "y", "yes", "retry"
}

# Message Templates
REGISTER = "{message}"
PROFILE_SELECTION = "> *👤 Profile*\n{message}"
INVALID_ACTION = "I'm sorry, I didn't understand that. Can you please try again?"
DELAY = "Please wait while I process your request..."


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
        logger.error(
            "Greeting generation error",
            extra={
                "error": str(e),
                "name": name,
                "hour": hour if 'hour' in locals() else None
            }
        )
        raise SystemException(
            message="Failed to generate greeting",
            code="GREETING_ERROR",
            service="config",
            action="get_greeting"
        ) from e
