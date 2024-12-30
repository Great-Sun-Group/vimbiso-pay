"""Redis configuration and basic constants"""
import logging
from datetime import datetime, timedelta
from urllib.parse import urlparse

import redis
from core.utils.error_handler import ErrorContext
from core.utils.exceptions import StateException
from core.utils.redis_atomic import AtomicStateManager
from django.conf import settings

logger = logging.getLogger(__name__)

# Redis Configuration
try:
    redis_url = urlparse(settings.REDIS_STATE_URL)
    state_redis = redis.Redis(
        host=redis_url.hostname or 'localhost',
        port=redis_url.port or 6380,
        db=int(redis_url.path[1:]) if redis_url.path else 0,
        password=redis_url.password,
        decode_responses=True,
        socket_timeout=30,
        socket_connect_timeout=30,
        retry_on_timeout=True
    )

    # Test connection
    state_redis.ping()
    logger.info("Redis connection established successfully")

except Exception as e:
    error_context = ErrorContext(
        error_type="system",
        message="Failed to connect to Redis",
        details={
            "host": redis_url.hostname or 'localhost',
            "port": redis_url.port or 6380,
            "error": str(e)
        }
    )
    logger.error(
        "Redis connection error",
        extra={
            "error": str(e),
            "error_context": error_context.__dict__
        }
    )
    raise StateException("Redis connection failed") from e

# Initialize atomic state manager
atomic_state = AtomicStateManager(state_redis)

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
        StateException: If greeting generation fails
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
        error_context = ErrorContext(
            error_type="system",
            message="Failed to generate greeting",
            details={
                "name": name,
                "hour": hour if 'hour' in locals() else None,
                "error": str(e)
            }
        )
        logger.error(
            "Greeting generation error",
            extra={
                "error": str(e),
                "error_context": error_context.__dict__
            }
        )
        raise StateException("Failed to generate greeting") from e
