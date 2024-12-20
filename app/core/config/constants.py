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

        try:
            # Get initial state atomically with retry
            max_retries = 3
            retry_count = 0
            state_data = None
            last_error = None

            while retry_count < max_retries:
                state_data, error = atomic_state.atomic_get(self.key_prefix)
                if not error:
                    break
                last_error = error
                retry_count += 1
                logger.warning(f"Retry {retry_count}/{max_retries} getting state: {error}")

            if last_error:
                logger.error(f"Error getting initial state after {max_retries} retries: {last_error}")

            # Initialize state with defaults if needed
            if not state_data:
                state_data = {
                    "jwt_token": None,
                    "profile": {},
                    "current_account": None,
                    "flow_data": None,
                    "member_id": None,
                    "account_id": None
                }

            # Ensure critical fields are preserved
            if state_data:
                # Log current state for debugging
                logger.debug(f"Current state before initialization: {state_data}")

                # Ensure all required fields exist
                state_data.setdefault("jwt_token", None)
                state_data.setdefault("profile", {})
                state_data.setdefault("current_account", None)
                state_data.setdefault("flow_data", None)
                state_data.setdefault("member_id", None)
                state_data.setdefault("account_id", None)

                # Preserve critical fields from both current and previous state
                critical_fields = ["jwt_token", "profile", "current_account", "member_id", "account_id"]

                # First try to get from current state
                for field in critical_fields:
                    if field in state_data and state_data[field] is not None:
                        continue  # Keep current value
                    # If not in current state, try previous state
                    if "_previous_state" in state_data:
                        previous_state = state_data["_previous_state"]
                        if field in previous_state and previous_state[field] is not None:
                            state_data[field] = previous_state[field]

                # Store current state as previous for next initialization
                state_data["_previous_state"] = state_data.copy()
                state_data["_previous_state"].pop("_previous_state", None)

            # Set instance variables
            self.state = state_data
            self.jwt_token = state_data.get("jwt_token")

            # Update state atomically with retry
            retry_count = 0
            success = False
            last_error = None

            while retry_count < max_retries:
                success, error = atomic_state.atomic_update(
                    key_prefix=self.key_prefix,
                    state=state_data,
                    ttl=ACTIVITY_TTL
                )
                if success:
                    break
                last_error = error
                retry_count += 1
                logger.warning(f"Retry {retry_count}/{max_retries} updating state: {error}")

            if not success:
                logger.error(f"Initial state update failed after {max_retries} retries: {last_error}")

            # Log final state for debugging
            logger.debug(f"Final state after initialization: {self.state}")

        except Exception as e:
            logger.exception(f"Error initializing state: {e}")
            # Set safe defaults while preserving any existing state
            self.state = {
                "jwt_token": None,
                "profile": {},
                "current_account": None,
                "flow_data": None,
                "member_id": None,
                "account_id": None,
                "_previous_state": {}  # Empty but present to maintain structure
            }
            self.jwt_token = None

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
        try:
            # Get state with retry
            max_retries = 3
            retry_count = 0
            state_data = None
            last_error = None

            while retry_count < max_retries:
                state_data, error = atomic_state.atomic_get(str(user.mobile_number))
                if not error:
                    break
                last_error = error
                retry_count += 1
                logger.warning(f"Retry {retry_count}/{max_retries} getting state in get_state: {error}")

            if last_error:
                logger.error(f"Error getting state in get_state after {max_retries} retries: {last_error}")

            # If no state or error, initialize with current instance state
            if error or not state_data:
                logger.debug("Initializing new state in get_state with current instance state")
                state_data = {
                    "jwt_token": self.jwt_token,
                    "profile": self.state.get("profile", {}),
                    "current_account": self.state.get("current_account"),
                    "flow_data": self.state.get("flow_data"),
                    "member_id": self.state.get("member_id"),
                    "account_id": self.state.get("account_id")
                }

            logger.debug(f"Current state in get_state: {state_data}")
            return state_data

        except Exception as e:
            logger.exception(f"Error in get_state: {e}")
            # Return safe defaults based on instance state
            return {
                "jwt_token": self.jwt_token,
                "profile": self.state.get("profile", {}),
                "current_account": self.state.get("current_account"),
                "flow_data": self.state.get("flow_data"),
                "member_id": self.state.get("member_id"),
                "account_id": self.state.get("account_id")
            }

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
        try:
            # Get current state first to ensure we have all fields to preserve
            current_state = self.state.copy()

            # Perform atomic cleanup while preserving fields
            success, error = atomic_state.atomic_cleanup(
                self.key_prefix,
                preserve_fields=preserve_fields
            )

            if not success:
                return False, error

            # Get preserved state after cleanup
            preserved_state, get_error = atomic_state.atomic_get(self.key_prefix)
            if get_error:
                logger.error(f"Error getting preserved state: {get_error}")
                preserved_state = {}

            # Initialize new state preserving all critical fields
            new_state = {
                "jwt_token": preserved_state.get("jwt_token") or current_state.get("jwt_token"),
                "profile": preserved_state.get("profile", {}) or current_state.get("profile", {}),
                "current_account": preserved_state.get("current_account") or current_state.get("current_account"),
                "flow_data": None,  # Always reset flow data
                "member_id": preserved_state.get("member_id") or current_state.get("member_id"),
                "account_id": preserved_state.get("account_id") or current_state.get("account_id")
            }

            # Update state atomically to ensure consistency
            update_success, update_error = atomic_state.atomic_update(
                key_prefix=self.key_prefix,
                state=new_state,
                ttl=ACTIVITY_TTL
            )

            if not update_success:
                logger.error(f"Failed to update state after cleanup: {update_error}")
                return False, update_error

            # Update instance state
            self.state = new_state
            self.jwt_token = new_state.get("jwt_token")

            # Clear service instance
            self.credex_service = None

            return True, None

        except Exception as e:
            logger.error(f"Error in cleanup_state: {str(e)}")
            return False, str(e)

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
