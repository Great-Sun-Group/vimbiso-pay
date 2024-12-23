"""Constants and cached user state management"""
import logging
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import redis
from django.conf import settings

from core.utils.flow_audit import FlowAuditLogger
from core.utils.redis_atomic import AtomicStateManager
from core.utils.state_validator import StateValidator
from services.credex.service import CredExService


logger = logging.getLogger(__name__)
audit = FlowAuditLogger()

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


def create_initial_state() -> Dict[str, Any]:
    """Create initial state with proper structure and validation context"""
    # Create base state
    base_state = {
        "jwt_token": None,
        "profile": StateValidator.ensure_profile_structure({}),
        "current_account": {},  # Initialize as empty dict
        "flow_data": None,
        "member_id": None,
        "account_id": None,
        "authenticated": False,
        "_validation_context": {},
        "_validation_state": {},
        "_previous_state": {}  # Initialize with empty dict
    }

    # First ensure validation context
    state = StateValidator.ensure_validation_context(base_state)

    # Create a copy for previous state
    previous = state.copy()
    previous.pop("_previous_state", None)  # Avoid recursive previous states

    # Set the previous state
    state["_previous_state"] = previous

    # Final validation context check
    return StateValidator.ensure_validation_context(state)


def prepare_state_update(current_state: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare state update while preserving validation context"""
    # Create a copy of current state as previous state
    previous_state = current_state.copy()
    previous_state.pop("_previous_state", None)  # Avoid recursive previous states

    # Create new state starting with current state
    new_state = current_state.copy()

    # Apply updates
    new_state.update(updates)

    # Ensure validation context
    new_state = StateValidator.ensure_validation_context(new_state)

    # Set previous state
    new_state["_previous_state"] = previous_state

    return new_state


class CachedUserState:
    """Manages user state with atomic operations"""

    def __init__(self, user) -> None:
        self.user = user
        # Use member_id as key if available, otherwise channel identifier
        self.key_prefix = str(user.member_id) if user.member_id else f"channel:{user.channel_identifier}"
        self.credex_service = None  # Store CredExService instance

        try:
            # Log initialization attempt
            audit.log_flow_event(
                "user_state",
                "initialization",
                None,
                {
                    "member_id": user.member_id,
                    "channel": {
                        "type": "whatsapp",
                        "identifier": user.channel_identifier
                    }
                },
                "in_progress"
            )

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
                audit.log_flow_event(
                    "user_state",
                    "state_retrieval_error",
                    None,
                    {"error": last_error},
                    "failure"
                )

            # Initialize state with defaults if needed
            if not state_data:
                state_data = create_initial_state()

            # Validate state structure
            validation = StateValidator.validate_state(state_data)
            if not validation.is_valid:
                audit.log_flow_event(
                    "user_state",
                    "state_validation_error",
                    None,
                    state_data,
                    "failure",
                    validation.error_message
                )
                # Attempt recovery from last valid state
                last_valid = audit.get_last_valid_state("user_state")
                if last_valid:
                    state_data = last_valid
                    audit.log_flow_event(
                        "user_state",
                        "state_recovery",
                        None,
                        state_data,
                        "success"
                    )

            # Ensure critical fields are preserved
            if state_data:
                # Log current state for debugging
                logger.debug(f"Current state before initialization: {state_data}")

                # Ensure all required fields exist
                state_data.setdefault("jwt_token", None)
                state_data.setdefault("profile", StateValidator.ensure_profile_structure({}))
                state_data.setdefault("current_account", {})  # Initialize as empty dict
                state_data.setdefault("flow_data", None)
                state_data.setdefault("member_id", None)
                state_data.setdefault("account_id", None)
                state_data.setdefault("authenticated", False)

                # Ensure validation context fields
                state_data = StateValidator.ensure_validation_context(state_data)

                # Preserve critical fields from both current and previous state
                critical_fields = ["jwt_token", "profile", "current_account", "member_id", "account_id", "authenticated"]

                # First try to get from current state
                for field in critical_fields:
                    if field in state_data and state_data[field] is not None:
                        # Special handling for current_account
                        if field == "current_account" and not isinstance(state_data[field], dict):
                            state_data[field] = {}
                        continue  # Keep current value
                    # If not in current state, try previous state
                    if "_previous_state" in state_data:
                        previous_state = state_data["_previous_state"]
                        if field in previous_state and previous_state[field] is not None:
                            # Special handling for current_account
                            if field == "current_account":
                                state_data[field] = previous_state[field] if isinstance(previous_state[field], dict) else {}
                            else:
                                state_data[field] = previous_state[field]

                # Store current state as previous for next initialization
                previous_state = state_data.copy()
                previous_state.pop("_previous_state", None)  # Avoid recursive previous states
                state_data["_previous_state"] = previous_state

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
                audit.log_flow_event(
                    "user_state",
                    "state_update_error",
                    None,
                    {"error": last_error},
                    "failure"
                )

            # Log successful initialization
            audit.log_flow_event(
                "user_state",
                "initialization",
                None,
                {
                    "member_id": user.member_id,
                    "channel": {
                        "type": "whatsapp",
                        "identifier": user.channel_identifier
                    }
                },
                "success"
            )

            # Log final state for debugging
            logger.debug(f"Final state after initialization: {self.state}")

            # Setup member_id listener if needed
            if not user.member_id:
                self._setup_member_id_listener()

        except Exception as e:
            logger.exception(f"Error initializing state: {e}")
            audit.log_flow_event(
                "user_state",
                "initialization_error",
                None,
                {"error": str(e)},
                "failure"
            )
            # Set safe defaults while preserving any existing state
            self.state = create_initial_state()
            self.jwt_token = None

    def _setup_member_id_listener(self) -> None:
        """Setup listener for member_id changes to migrate state"""
        def on_member_id_change(old_key: str, new_key: str) -> None:
            """Migrate state when member_id becomes available"""
            try:
                # Get state from old key
                state_data, error = atomic_state.atomic_get(old_key)
                if error or not state_data:
                    return

                # Update key_prefix
                self.key_prefix = new_key

                # Store state under new key
                success, error = atomic_state.atomic_update(
                    key_prefix=new_key,
                    state=state_data,
                    ttl=ACTIVITY_TTL
                )
                if success:
                    # Clean up old state
                    atomic_state.atomic_cleanup(old_key)

            except Exception as e:
                logger.error(f"Error migrating state: {str(e)}")

        # Store listener for later
        self._member_id_listener = on_member_id_change

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
            # Log state update attempt
            audit.log_flow_event(
                "user_state",
                "state_update_attempt",
                None,
                {
                    "member_id": self.user.member_id,
                    "channel": {
                        "type": "whatsapp",
                        "identifier": self.user.channel_identifier
                    },
                    "update_from": update_from
                },
                "in_progress"
            )

            # Get current state for merging
            new_state = self.state.copy()

            # Track critical fields and their sources with priority
            critical_fields = {
                "jwt_token": [
                    (state.get("jwt_token"), "update"),
                    (self.jwt_token, "instance"),
                    (new_state.get("jwt_token"), "current_state")
                ],
                "member_id": [
                    (state.get("member_id"), "update"),
                    (new_state.get("member_id"), "current_state")
                ],
                "account_id": [
                    (state.get("account_id"), "update"),
                    (new_state.get("account_id"), "current_state")
                ],
                "authenticated": [
                    (state.get("authenticated"), "update"),
                    (new_state.get("authenticated"), "current_state")
                ]
            }

            # Update critical fields based on priority
            for field, sources in critical_fields.items():
                for value, source in sources:
                    if value is not None:
                        new_state[field] = value
                        if field == "jwt_token":
                            self.jwt_token = value
                            # Update service token if needed
                            self._update_service_token(value)
                        elif field == "member_id" and value != self.user.member_id:
                            # Handle member_id change
                            old_key = self.key_prefix
                            new_key = str(value)
                            if hasattr(self, '_member_id_listener'):
                                self._member_id_listener(old_key, new_key)
                        break

            # Handle flow data state transitions
            flow_data_cleared = "flow_data" in state and state["flow_data"] is None
            current_flow_data = new_state.get("flow_data", {})
            new_flow_data = state.get("flow_data", {})

            # Preserve flow validation state during transitions
            if (not flow_data_cleared and isinstance(current_flow_data, dict)
                    and isinstance(new_flow_data, dict)):
                # Preserve validation state and previous data
                if "_validation_state" in current_flow_data:
                    new_flow_data["_validation_state"] = current_flow_data["_validation_state"]
                if "_previous_data" in current_flow_data:
                    new_flow_data["_previous_data"] = current_flow_data["_previous_data"]

            # Prepare state update with proper context preservation
            new_state = prepare_state_update(new_state, state or {})

            # Restore flow data with preserved validation state
            if not flow_data_cleared:
                new_state["flow_data"] = new_flow_data

            # Clear flow data if explicitly requested
            if flow_data_cleared:
                new_state["flow_data"] = None

            # Ensure current_account is a dictionary
            if not isinstance(new_state.get("current_account"), dict):
                new_state["current_account"] = {}

            # Validate new state
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                audit.log_flow_event(
                    "user_state",
                    "state_validation_error",
                    None,
                    new_state,
                    "failure",
                    validation.error_message
                )
                # Attempt recovery from last valid state
                last_valid = audit.get_last_valid_state("user_state")
                if last_valid:
                    new_state = last_valid
                    audit.log_flow_event(
                        "user_state",
                        "state_recovery",
                        None,
                        new_state,
                        "success"
                    )

            # Log state transition
            audit.log_state_transition(
                "user_state",
                self.state,
                new_state,
                "success"
            )

            # Update atomically
            success, error = atomic_state.atomic_update(
                key_prefix=self.key_prefix,
                state=new_state,
                ttl=ACTIVITY_TTL
            )
            if not success:
                logger.error(f"State update failed: {error}")
                audit.log_flow_event(
                    "user_state",
                    "state_update_error",
                    None,
                    {"error": error},
                    "failure"
                )
                return

            self.state = new_state

            audit.log_flow_event(
                "user_state",
                "state_update_success",
                None,
                {
                    "member_id": self.user.member_id,
                    "channel": {
                        "type": "whatsapp",
                        "identifier": self.user.channel_identifier
                    },
                    "update_from": update_from
                },
                "success"
            )

        except Exception as e:
            logger.exception(f"Error in update_state: {e}")
            audit.log_flow_event(
                "user_state",
                "state_update_error",
                None,
                {"error": str(e)},
                "failure"
            )

    def get_state(self, user) -> Dict[str, Any]:
        """Get current state with atomic operation"""
        try:
            # Log state retrieval attempt
            audit.log_flow_event(
                "user_state",
                "state_retrieval",
                None,
                {
                    "member_id": user.member_id,
                    "channel": {
                        "type": "whatsapp",
                        "identifier": user.channel_identifier
                    }
                },
                "in_progress"
            )

            # Get state with retry
            max_retries = 3
            retry_count = 0
            state_data = None
            last_error = None

            while retry_count < max_retries:
                key = str(user.member_id) if user.member_id else f"channel:{user.channel_identifier}"
                state_data, error = atomic_state.atomic_get(key)
                if not error:
                    break
                last_error = error
                retry_count += 1
                logger.warning(f"Retry {retry_count}/{max_retries} getting state in get_state: {error}")

            if last_error:
                logger.error(f"Error getting state in get_state after {max_retries} retries: {last_error}")
                audit.log_flow_event(
                    "user_state",
                    "state_retrieval_error",
                    None,
                    {"error": last_error},
                    "failure"
                )

            # If no state or error, initialize with current instance state
            if error or not state_data:
                logger.debug("Initializing new state in get_state with current instance state")
                state_data = create_initial_state()
                state_data.update({
                    "jwt_token": self.jwt_token,
                    "profile": StateValidator.ensure_profile_structure(self.state.get("profile", {})),
                    "current_account": self.state.get("current_account", {}),
                    "flow_data": self.state.get("flow_data"),
                    "member_id": self.state.get("member_id"),
                    "account_id": self.state.get("account_id"),
                    "authenticated": self.state.get("authenticated", False)
                })

            # Validate state
            validation = StateValidator.validate_state(state_data)
            if not validation.is_valid:
                audit.log_flow_event(
                    "user_state",
                    "state_validation_error",
                    None,
                    state_data,
                    "failure",
                    validation.error_message
                )
                # Attempt recovery from last valid state
                last_valid = audit.get_last_valid_state("user_state")
                if last_valid:
                    state_data = last_valid
                    audit.log_flow_event(
                        "user_state",
                        "state_recovery",
                        None,
                        state_data,
                        "success"
                    )

            logger.debug(f"Current state in get_state: {state_data}")

            audit.log_flow_event(
                "user_state",
                "state_retrieval",
                None,
                {
                    "member_id": user.member_id,
                    "channel": {
                        "type": "whatsapp",
                        "identifier": user.channel_identifier
                    }
                },
                "success"
            )

            return state_data

        except Exception as e:
            logger.exception(f"Error in get_state: {e}")
            audit.log_flow_event(
                "user_state",
                "state_retrieval_error",
                None,
                {"error": str(e)},
                "failure"
            )
            # Return safe defaults based on instance state
            return create_initial_state()

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
        try:
            # Log token update attempt
            audit.log_flow_event(
                "user_state",
                "token_update",
                None,
                {
                    "member_id": self.user.member_id,
                    "channel": {
                        "type": "whatsapp",
                        "identifier": self.user.channel_identifier
                    }
                },
                "in_progress"
            )

            if jwt_token:
                self.jwt_token = jwt_token
                current_state = self.state.copy()
                current_state["jwt_token"] = jwt_token

                # Update service token directly without using property setter
                self._update_service_token(jwt_token)

                self.update_state(current_state, "set_jwt_token")

                audit.log_flow_event(
                    "user_state",
                    "token_update",
                    None,
                    {
                        "member_id": self.user.member_id,
                        "channel": {
                            "type": "whatsapp",
                            "identifier": self.user.channel_identifier
                        }
                    },
                    "success"
                )

        except Exception as e:
            logger.error(f"Error in set_jwt_token: {str(e)}")
            audit.log_flow_event(
                "user_state",
                "token_update_error",
                None,
                {"error": str(e)},
                "failure"
            )

    def cleanup_state(self, preserve_fields: set) -> Tuple[bool, Optional[str]]:
        """Clean up state while preserving specified fields"""
        try:
            # Log cleanup attempt
            audit.log_flow_event(
                "user_state",
                "cleanup",
                None,
                {
                    "member_id": self.user.member_id,
                    "channel": {
                        "type": "whatsapp",
                        "identifier": self.user.channel_identifier
                    },
                    "preserve_fields": list(preserve_fields)
                },
                "in_progress"
            )

            # Get current state first to ensure we have all fields to preserve
            current_state = self.state.copy()

            # Perform atomic cleanup while preserving fields
            success, error = atomic_state.atomic_cleanup(
                self.key_prefix,
                preserve_fields=preserve_fields
            )

            if not success:
                audit.log_flow_event(
                    "user_state",
                    "cleanup_error",
                    None,
                    {"error": error},
                    "failure"
                )
                return False, error

            # Get preserved state after cleanup
            preserved_state, get_error = atomic_state.atomic_get(self.key_prefix)
            if get_error:
                logger.error(f"Error getting preserved state: {get_error}")
                preserved_state = {}

            # Initialize new state preserving all critical fields
            new_state = create_initial_state()
            new_state.update({
                "jwt_token": preserved_state.get("jwt_token") or current_state.get("jwt_token"),
                "profile": StateValidator.ensure_profile_structure(preserved_state.get("profile", {}) or current_state.get("profile", {})),
                "current_account": preserved_state.get("current_account", {}) or current_state.get("current_account", {}),
                "flow_data": None,  # Always reset flow data
                "member_id": preserved_state.get("member_id") or current_state.get("member_id"),
                "account_id": preserved_state.get("account_id") or current_state.get("account_id"),
                "authenticated": preserved_state.get("authenticated", False)
            })

            # Validate new state
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                audit.log_flow_event(
                    "user_state",
                    "state_validation_error",
                    None,
                    new_state,
                    "failure",
                    validation.error_message
                )
                return False, validation.error_message

            # Log state transition
            audit.log_state_transition(
                "user_state",
                current_state,
                new_state,
                "success"
            )

            # Update state atomically to ensure consistency
            update_success, update_error = atomic_state.atomic_update(
                key_prefix=self.key_prefix,
                state=new_state,
                ttl=ACTIVITY_TTL
            )

            if not update_success:
                logger.error(f"Failed to update state after cleanup: {update_error}")
                audit.log_flow_event(
                    "user_state",
                    "cleanup_error",
                    None,
                    {"error": update_error},
                    "failure"
                )
                return False, update_error

            # Update instance state
            self.state = new_state
            self.jwt_token = new_state.get("jwt_token")

            # Clear service instance
            self.credex_service = None

            audit.log_flow_event(
                "user_state",
                "cleanup",
                None,
                {
                    "member_id": self.user.member_id,
                    "channel": {
                        "type": "whatsapp",
                        "identifier": self.user.channel_identifier
                    },
                    "preserve_fields": list(preserve_fields)
                },
                "success"
            )

            return True, None

        except Exception as e:
            logger.error(f"Error in cleanup_state: {str(e)}")
            audit.log_flow_event(
                "user_state",
                "cleanup_error",
                None,
                {"error": str(e)},
                "failure"
            )
            return False, str(e)

    def reset_state(self) -> None:
        """Reset state with atomic cleanup"""
        try:
            # Log reset attempt
            audit.log_flow_event(
                "user_state",
                "reset",
                None,
                {
                    "member_id": self.user.member_id,
                    "channel": {
                        "type": "whatsapp",
                        "identifier": self.user.channel_identifier
                    }
                },
                "in_progress"
            )

            preserve_fields = {"jwt_token", "member_id", "account_id"}
            success, error = self.cleanup_state(preserve_fields)

            if not success:
                logger.error(f"State reset failed: {error}")
                audit.log_flow_event(
                    "user_state",
                    "reset_error",
                    None,
                    {"error": error},
                    "failure"
                )
                return

            audit.log_flow_event(
                "user_state",
                "reset",
                None,
                {
                    "member_id": self.user.member_id,
                    "channel": {
                        "type": "whatsapp",
                        "identifier": self.user.channel_identifier
                    }
                },
                "success"
            )

        except Exception as e:
            logger.error(f"Error in reset_state: {str(e)}")
            audit.log_flow_event(
                "user_state",
                "reset_error",
                None,
                {"error": str(e)},
                "failure"
            )


class CachedUser:
    """User representation with cached state"""
    def __init__(self, channel_identifier: str, member_id: Optional[str] = None) -> None:
        self.first_name = "Welcome"
        self.last_name = "Visitor"
        self.role = "DEFAULT"
        self.email = "customer@credex.co.zw"
        self._member_id = member_id
        self._channel_identifier = channel_identifier
        self.registration_complete = False
        self.state = CachedUserState(self)
        self.jwt_token = self.state.jwt_token

    @property
    def member_id(self) -> Optional[str]:
        """Get member ID from state if not set directly"""
        if self._member_id:
            return self._member_id
        return self.state.state.get("member_id")

    @member_id.setter
    def member_id(self, value: str) -> None:
        """Set member ID and update state"""
        self._member_id = value
        if self.state and self.state.state:
            self.state.state["member_id"] = value

    @property
    def channel_identifier(self) -> str:
        """Get channel identifier (e.g. phone number)"""
        return self._channel_identifier


# Message Templates
REGISTER = "{message}"
PROFILE_SELECTION = "> *👤 Profile*\n{message}"
INVALID_ACTION = "I'm sorry, I didn't understand that. Can you please try again?"
DELAY = "Please wait while I process your request..."
