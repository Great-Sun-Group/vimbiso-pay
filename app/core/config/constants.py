"""Constants and cached user state management"""
import logging
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import redis
from core.utils.redis_atomic import AtomicStateManager
from django.conf import settings
from services.credex.service import CredExService

logger = logging.getLogger(__name__)

# Redis Configuration
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

# Initialize atomic state manager
atomic_state = AtomicStateManager(state_redis)

# TTL Constants
ACTIVITY_TTL = 300  # 5 minutes
ABSOLUTE_JWT_TTL = 21600  # 6 hours

# Command Recognition
GREETINGS = {
    "menu", "memu", "hi", "hie", "cancel", "home", "hy",
    "reset", "hello", "x", "c", "no", "No", "n", "N",
    "hey", "y", "yes", "retry"
}


def get_greeting(name: str) -> str:
    """Get time-appropriate greeting"""
    from datetime import datetime, timedelta
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


class CachedUserState:
    """Manages user state with atomic operations"""

    def __init__(self, user) -> None:
        self.user = user
        self.key_prefix = str(user.mobile_number)
        self.credex_service = None  # Store CredExService instance

        # Get initial state atomically
        state_data, error = atomic_state.atomic_get(self.key_prefix)
        if error:
            logger.error(f"Error getting initial state: {error}")
            state_data = None

        # Initialize state
        if not state_data:
            state_data = {
                "jwt_token": None,
                "profile": {},
                "current_account": None,
                "flow_data": None,
                "member_id": None,  # Added member_id
                "account_id": None  # Added account_id
            }

        # Set instance variables
        self.state = state_data
        self.jwt_token = state_data.get("jwt_token")

        # Update state atomically
        success, error = atomic_state.atomic_update(
            key_prefix=self.key_prefix,
            state=state_data,
            ttl=ACTIVITY_TTL
        )
        if not success:
            logger.error(f"Initial state update failed: {error}")

    def get_or_create_credex_service(self) -> CredExService:
        """Get existing CredExService or create new one"""
        if not self.credex_service:
            self.credex_service = CredExService(user=self.user)
            # Initialize token from state if available
            if self.jwt_token:
                self._update_service_token(self.jwt_token)
        return self.credex_service

    def update_state(self, state: Dict[str, Any], update_from: str) -> None:
        """Update state with atomic operations"""
        try:
            # Merge with existing state
            new_state = self.state.copy()

            # Preserve critical fields
            critical_fields = {
                "jwt_token": self.jwt_token,
                "member_id": new_state.get("member_id"),
                "account_id": new_state.get("account_id")
            }

            # Handle flow_data specially - if it's explicitly set to None, respect that
            flow_data_cleared = "flow_data" in state and state["flow_data"] is None

            # Update with new state
            new_state.update(state or {})

            # Ensure critical fields are preserved
            for field, value in critical_fields.items():
                if value is not None:
                    new_state[field] = value
                    # Only update flow_data jwt_token if flow_data wasn't explicitly cleared
                    if field == "jwt_token" and not flow_data_cleared and "flow_data" in new_state and isinstance(new_state["flow_data"], dict):
                        new_state["flow_data"]["jwt_token"] = value

            # Ensure flow_data stays None if it was explicitly cleared
            if flow_data_cleared:
                new_state["flow_data"] = None

            # Update atomically
            success, error = atomic_state.atomic_update(
                key_prefix=self.key_prefix,
                state=new_state,
                ttl=ACTIVITY_TTL
            )
            if not success:
                logger.error(f"State update failed: {error}")
                return

            self.state = new_state

        except Exception as e:
            logger.exception(f"Error in update_state: {e}")

    def get_state(self, user) -> Dict[str, Any]:
        """Get current state with atomic operation"""
        state_data, error = atomic_state.atomic_get(str(user.mobile_number))

        if error or not state_data:
            state_data = {
                "jwt_token": self.jwt_token,
                "profile": {},
                "current_account": None,
                "flow_data": None,
                "member_id": None,  # Added member_id
                "account_id": None  # Added account_id
            }

        return state_data

    def _update_service_token(self, jwt_token: str) -> None:
        """Update service token without triggering recursion"""
        if self.credex_service:
            self.credex_service._jwt_token = jwt_token
            # Update sub-services
            if hasattr(self.credex_service, '_auth'):
                self.credex_service._auth._jwt_token = jwt_token
            if hasattr(self.credex_service, '_member'):
                self.credex_service._member._jwt_token = jwt_token
            if hasattr(self.credex_service, '_offers'):
                self.credex_service._offers._jwt_token = jwt_token
            if hasattr(self.credex_service, '_recurring'):
                self.credex_service._recurring._jwt_token = jwt_token

    def set_jwt_token(self, jwt_token: str) -> None:
        """Set JWT token with atomic update"""
        if jwt_token:
            self.jwt_token = jwt_token
            current_state = self.state.copy()
            current_state["jwt_token"] = jwt_token

            if "flow_data" in current_state and isinstance(current_state["flow_data"], dict):
                current_state["flow_data"]["jwt_token"] = jwt_token

            # Update service token directly without using property setter
            self._update_service_token(jwt_token)

            self.update_state(current_state, "set_jwt_token")

    def cleanup_state(self, preserve_fields: set) -> Tuple[bool, Optional[str]]:
        """Clean up state while preserving specified fields"""
        success, error = atomic_state.atomic_cleanup(
            self.key_prefix,
            preserve_fields=preserve_fields
        )

        if success:
            # Reset instance state
            self.state = None
            # Clear service instance
            self.credex_service = None

        return success, error

    def reset_state(self) -> None:
        """Reset state with atomic cleanup"""
        preserve_fields = {"jwt_token", "member_id", "account_id"}
        success, error = self.cleanup_state(preserve_fields)

        if not success:
            logger.error(f"State reset failed: {error}")


class CachedUser:
    """User representation with cached state"""
    def __init__(self, mobile_number: str) -> None:
        self.first_name = "Welcome"
        self.last_name = "Visitor"
        self.role = "DEFAULT"
        self.email = "customer@credex.co.zw"
        self.mobile_number = mobile_number
        self.registration_complete = False
        self.state = CachedUserState(self)
        self.jwt_token = self.state.jwt_token


# Message Templates
REGISTER = "{message}"
PROFILE_SELECTION = "> *👤 Profile*\n{message}"
INVALID_ACTION = "I'm sorry, I didn't understand that. Can you please try again?"
DELAY = "Please wait while I process your request..."
