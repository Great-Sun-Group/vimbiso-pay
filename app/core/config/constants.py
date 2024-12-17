"""Constants and cached user state management"""
from django.conf import settings
from datetime import datetime, timedelta
import os
import redis
import logging
from urllib.parse import urlparse
from typing import Dict, Any, Optional

from core.utils.state_validator import StateValidator
from core.utils.redis_atomic import AtomicStateManager

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

# Initialize managers
atomic_state = AtomicStateManager(state_redis)

# TTL Constants
ACTIVITY_TTL = 300  # 5 minutes
ABSOLUTE_JWT_TTL = 21600  # 6 hours

# Feature flags
USE_PROGRESSIVE_FLOW = os.environ.get('USE_PROGRESSIVE_FLOW', 'False') == 'True'

# Command Recognition
GREETINGS = {
    "menu", "memu", "hi", "hie", "cancel", "home", "hy",
    "reset", "hello", "x", "c", "no", "No", "n", "N",
    "hey", "y", "yes", "retry"
}


def get_greeting(name: str) -> str:
    """Get time-appropriate greeting"""
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
    """Manages user state with atomic operations and validation"""

    def __init__(self, user) -> None:
        self.user = user
        self.key_prefix = str(user.mobile_number)

        # Get initial state atomically
        state_data, error = atomic_state.atomic_get(self.key_prefix)
        if error:
            logger.error(f"Error getting initial state: {error}")
            state_data = None

        # Initialize state
        if not state_data:
            state_data = self._create_initial_state()
        else:
            # Ensure profile structure
            state_data["profile"] = StateValidator.ensure_profile_structure(
                state_data.get("profile", {})
            )

        # Set instance variables
        self.state = state_data
        self.stage = state_data.get("stage", "handle_action_menu")
        self.option = state_data.get("option")
        self.direction = state_data.get("direction", "OUT")
        self.jwt_token = state_data.get("jwt_token")

        # Validate and update state
        success, error = atomic_state.atomic_update(
            key_prefix=self.key_prefix,
            state=state_data,
            ttl=ACTIVITY_TTL,
            stage=self.stage,
            option=self.option,
            direction=self.direction
        )
        if not success:
            logger.error(f"Initial state update failed: {error}")

    def _create_initial_state(self) -> Dict[str, Any]:
        """Create initial state structure"""
        return {
            "stage": "handle_action_menu",
            "option": None,
            "direction": "OUT",
            "profile": StateValidator.ensure_profile_structure({}),
            "current_account": None,
            "flow_data": None
        }

    def update_state(
        self,
        state: Dict[str, Any],
        update_from: str,
        stage: Optional[str] = None,
        option: Optional[str] = None,
        direction: Optional[str] = None
    ) -> None:
        """Update state with validation and atomic operations"""
        try:
            # Update local variables
            if stage:
                self.stage = stage
            if option:
                self.option = option
            if direction:
                self.direction = direction

            # Merge with existing state
            new_state = self.state.copy()
            new_state.update(state or {})

            # Ensure profile structure
            if "profile" in new_state:
                new_state["profile"] = StateValidator.ensure_profile_structure(
                    new_state["profile"]
                )

            # Preserve JWT token
            if self.jwt_token:
                new_state["jwt_token"] = self.jwt_token
                if "flow_data" in new_state and isinstance(new_state["flow_data"], dict):
                    new_state["flow_data"]["jwt_token"] = self.jwt_token

            # Validate state
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                logger.error(f"State validation failed: {validation.error_message}")
                new_state = self._create_initial_state()
                if self.jwt_token:
                    new_state["jwt_token"] = self.jwt_token

            # Update atomically
            success, error = atomic_state.atomic_update(
                key_prefix=self.key_prefix,
                state=new_state,
                ttl=ACTIVITY_TTL,
                stage=self.stage,
                option=self.option,
                direction=self.direction
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
            state_data = self._create_initial_state()
            if self.jwt_token:
                state_data["jwt_token"] = self.jwt_token

        return state_data

    def set_jwt_token(self, jwt_token: str) -> None:
        """Set JWT token with atomic update"""
        if jwt_token:
            self.jwt_token = jwt_token
            current_state = self.state.copy()
            current_state["jwt_token"] = jwt_token

            if "flow_data" in current_state and isinstance(current_state["flow_data"], dict):
                current_state["flow_data"]["jwt_token"] = jwt_token

            self.update_state(current_state, "set_jwt_token")

    def reset_state(self) -> None:
        """Reset state with atomic cleanup"""
        preserve_fields = {"jwt_token"} if self.jwt_token else None

        success, error = atomic_state.atomic_cleanup(
            self.key_prefix,
            preserve_fields=preserve_fields
        )

        if not success:
            logger.error(f"State reset failed: {error}")

        # Reset instance state
        initial_state = self._create_initial_state()
        if self.jwt_token:
            initial_state["jwt_token"] = self.jwt_token

        self.state = initial_state
        self.stage = initial_state["stage"]
        self.option = initial_state["option"]
        self.direction = initial_state["direction"]

    def __getattr__(self, name: str) -> Any:
        """Handle attribute access for state data"""
        if name in self.state:
            return self.state[name]
        raise AttributeError(f"'CachedUserState' object has no attribute '{name}'")


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


# Menu Options
MENU_OPTIONS_1 = {
    # Main menu options
    "handle_action_offer_credex": "handle_action_offer_credex",
    "handle_action_accept_offers": "handle_action_accept_offers",
    "handle_action_decline_offers": "handle_action_decline_offers",
    "handle_action_pending_offers_out": "handle_action_pending_offers_out",
    "handle_action_transactions": "handle_action_transactions",
}

MENU_OPTIONS_2 = {
    # Main menu options
    "handle_action_offer_credex": "handle_action_offer_credex",
    "handle_action_accept_offers": "handle_action_accept_offers",
    "handle_action_decline_offers": "handle_action_decline_offers",
    "handle_action_pending_offers_out": "handle_action_pending_offers_out",
    "handle_action_transactions": "handle_action_transactions",
    "handle_action_authorize_member": "handle_action_authorize_member",
    "handle_action_notifications": "handle_action_notifications",
}

# Message Templates
REGISTER = "{message}"
PROFILE_SELECTION = "> *👤 Profile*\n{message}"
INVALID_ACTION = "I'm sorry, I didn't understand that. Can you please try again?"
DELAY = "Please wait while I process your request..."
