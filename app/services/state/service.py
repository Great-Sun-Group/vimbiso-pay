import logging
from typing import Any, Dict, Optional
from enum import Enum
import json
import time
from redis.exceptions import WatchError

from .exceptions import (
    InvalidOptionError,
    InvalidStateError,
    InvalidStageError,
    InvalidUserError,
)

logger = logging.getLogger(__name__)


class StateStage(Enum):
    """Valid state stages"""
    INIT = "init"
    AUTH = "auth"
    MENU = "menu"
    CREDEX = "credex"
    ACCOUNT = "account"
    REGISTRATION = "registration"  # Added for member registration


class StateTransition:
    """Represents valid state transitions"""
    VALID_TRANSITIONS = {
        StateStage.INIT: [StateStage.AUTH, StateStage.MENU, StateStage.REGISTRATION],
        StateStage.AUTH: [StateStage.MENU, StateStage.REGISTRATION],
        StateStage.MENU: [StateStage.CREDEX, StateStage.ACCOUNT, StateStage.AUTH, StateStage.MENU],
        StateStage.CREDEX: [StateStage.MENU],
        StateStage.ACCOUNT: [StateStage.MENU],
        StateStage.REGISTRATION: [StateStage.MENU]  # Registration can transition to menu
    }

    @classmethod
    def is_valid_transition(cls, from_stage: str, to_stage: str) -> bool:
        """Check if state transition is valid"""
        try:
            # Handle initial state case
            if from_stage is None:
                return True

            # Handle action commands
            if to_stage.startswith("handle_action_"):
                # Split the action command
                parts = to_stage.split("_")
                if len(parts) >= 3:
                    # Allow all handle_action transitions
                    return True

            # Handle credex-specific transitions
            if from_stage == "handle_action_offer_credex" and to_stage == "credex":
                return True

            from_enum = StateStage(from_stage)
            to_enum = StateStage(to_stage)

            # Allow same stage transitions
            if from_enum == to_enum:
                return True

            return to_enum in cls.VALID_TRANSITIONS.get(from_enum, [])
        except ValueError:
            # Allow transitions for custom stages not in enum
            return True


class StateService:
    """Implementation of the state management service with proper state machine"""

    def __init__(self, redis_client):
        """Initialize the state service with a Redis client"""
        self.redis = redis_client
        self.state_key_prefix = "user_state:"
        self.state_lock_prefix = "user_state_lock:"
        self.state_ttl = 3600  # 1 hour TTL for state
        self.lock_timeout = 30  # 30 seconds lock timeout

    def _validate_user_id(self, user_id: str) -> None:
        """Validate user ID"""
        if not user_id or not isinstance(user_id, str):
            logger.error(f"Invalid user ID provided: {user_id}")
            raise InvalidUserError(f"Invalid user ID: {user_id}")

    def _get_state_key(self, user_id: str) -> str:
        """Generate Redis key for user state"""
        return f"{self.state_key_prefix}{user_id}"

    def _get_lock_key(self, user_id: str) -> str:
        """Generate Redis key for state lock"""
        return f"{self.state_lock_prefix}{user_id}"

    def _acquire_lock(self, user_id: str, timeout: int = 10) -> bool:
        """Acquire lock for state updates with timeout and proper expiry"""
        lock_key = self._get_lock_key(user_id)
        end_time = time.time() + timeout

        while time.time() < end_time:
            # Use SET NX with expiry to ensure atomic lock acquisition
            if self.redis.set(lock_key, "1", nx=True, ex=self.lock_timeout):
                return True
            time.sleep(0.1)
        return False

    def _release_lock(self, user_id: str) -> None:
        """Release state update lock"""
        self.redis.delete(self._get_lock_key(user_id))

    def _validate_state_data(self, state_data: Dict[str, Any]) -> None:
        """Validate state data structure and required fields"""
        if not isinstance(state_data, dict):
            raise InvalidStateError("State must be a dictionary")

        required_fields = {"stage", "option"}
        missing_fields = required_fields - set(state_data.keys())
        if missing_fields:
            raise InvalidStateError(f"State missing required fields: {missing_fields}")

        # Validate nested structures
        if "flow_data" in state_data:
            flow_data = state_data["flow_data"]
            if not isinstance(flow_data, dict):
                raise InvalidStateError("Flow data must be a dictionary")
            required_flow_fields = {"id", "current_step", "data"}
            missing_flow_fields = required_flow_fields - set(flow_data.keys())
            if missing_flow_fields:
                raise InvalidStateError(f"Flow data missing required fields: {missing_flow_fields}")

    def _preserve_state_data(self, current_state: Dict[str, Any], new_state: Dict[str, Any]) -> Dict[str, Any]:
        """Preserve essential state data during updates"""
        preserved_fields = {
            "jwt_token",
            "profile",
            "current_account",
            "member",
            "flow_data"
        }

        result = new_state.copy()
        for field in preserved_fields:
            if field in current_state and field not in new_state:
                result[field] = current_state[field]

        return result

    def get_state(self, user_id: str) -> Dict[str, Any]:
        """Retrieve the current state for a user with proper error handling"""
        self._validate_user_id(user_id)

        try:
            state_key = self._get_state_key(user_id)
            state_json = self.redis.get(state_key)

            if not state_json:
                logger.warning(f"No state found for user {user_id}, creating new state")
                new_state = {
                    "stage": StateStage.INIT.value,
                    "option": "",
                    "last_updated": time.time(),
                    "version": 1  # Add version tracking
                }
                self.redis.set(state_key, json.dumps(new_state), self.state_ttl)
                return new_state

            try:
                state = json.loads(state_json)
                self._validate_state_data(state)
                return state
            except json.JSONDecodeError:
                logger.error(f"Corrupted state data for user {user_id}")
                raise InvalidStateError("Corrupted state data")

        except Exception as e:
            logger.error(f"Error retrieving state for user {user_id}: {str(e)}")
            raise

    def update_state(
        self,
        user_id: str,
        new_state: Dict[str, Any],
        stage: str,
        update_from: str,
        option: Optional[str] = None
    ) -> None:
        """Update the state for a user with atomic operations and validation"""
        self._validate_user_id(user_id)
        self._validate_state_data(new_state)

        state_key = self._get_state_key(user_id)

        # Use Redis transaction for atomic updates
        with self.redis.pipeline() as pipe:
            while True:
                try:
                    # Watch the state key for changes
                    pipe.watch(state_key)

                    # Get current state
                    current_state_json = pipe.get(state_key)
                    current_state = json.loads(current_state_json) if current_state_json else None
                    current_stage = current_state.get("stage") if current_state else None

                    # Validate state transition
                    if not StateTransition.is_valid_transition(current_stage, stage):
                        raise InvalidStageError(f"Invalid state transition from {current_stage} to {stage}")

                    # Start transaction
                    pipe.multi()

                    # Preserve essential data and prepare new state
                    if current_state:
                        new_state = self._preserve_state_data(current_state, new_state)

                    # Update state metadata
                    new_state.update({
                        "stage": stage,
                        "update_from": update_from,
                        "option": option if option is not None else "",
                        "last_updated": time.time(),
                        "version": (current_state.get("version", 0) + 1) if current_state else 1
                    })

                    # Store updated state
                    pipe.set(state_key, json.dumps(new_state), self.state_ttl)

                    # Execute transaction
                    pipe.execute()
                    logger.info(f"Updated state for user {user_id}: stage={stage}, update_from={update_from}")
                    break

                except WatchError:
                    # Key changed during transaction, retry
                    logger.warning(f"Concurrent state update detected for user {user_id}, retrying")
                    continue
                except Exception as e:
                    logger.error(f"Error updating state for user {user_id}: {str(e)}")
                    raise

    def reset_state(self, user_id: str, preserve_auth: bool = True) -> None:
        """Reset the state for a user with atomic operations"""
        self._validate_user_id(user_id)
        state_key = self._get_state_key(user_id)

        with self.redis.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(state_key)

                    if preserve_auth:
                        current_state_json = pipe.get(state_key)
                        if current_state_json:
                            current_state = json.loads(current_state_json)
                            jwt_token = current_state.get("jwt_token")

                            if jwt_token:
                                pipe.multi()
                                new_state = {
                                    "stage": StateStage.INIT.value,
                                    "option": "",
                                    "jwt_token": jwt_token,
                                    "last_updated": time.time(),
                                    "version": current_state.get("version", 0) + 1
                                }
                                pipe.set(state_key, json.dumps(new_state), self.state_ttl)
                                pipe.execute()
                                logger.info(f"Reset state for user {user_id} preserving JWT token")
                                return

                    # If no auth to preserve or no current state, delete the key
                    pipe.multi()
                    pipe.delete(state_key)
                    pipe.execute()
                    logger.info(f"Reset state for user {user_id}")
                    break

                except WatchError:
                    continue
                except Exception as e:
                    logger.error(f"Error resetting state for user {user_id}: {str(e)}")
                    raise

    def get_stage(self, user_id: str) -> str:
        """Get the current stage for a user"""
        state = self.get_state(user_id)
        return state.get("stage", StateStage.INIT.value)

    def set_stage(self, user_id: str, stage: str) -> None:
        """Set the current stage for a user with transition validation"""
        if not stage:
            raise InvalidStageError("Stage cannot be empty")

        try:
            state = self.get_state(user_id)
            current_stage = state.get("stage")

            # Validate state transition
            if not StateTransition.is_valid_transition(current_stage, stage):
                raise InvalidStageError(f"Invalid state transition from {current_stage} to {stage}")

            state["stage"] = stage
            self.update_state(
                user_id=user_id,
                new_state=state,
                stage=stage,
                update_from="set_stage"
            )
            logger.info(f"Set stage for user {user_id} to {stage}")
        except Exception as e:
            logger.error(f"Error setting stage for user {user_id}: {str(e)}")
            raise

    def get_option(self, user_id: str) -> Optional[str]:
        """Get the current option for a user"""
        state = self.get_state(user_id)
        return state.get("option")

    def set_option(self, user_id: str, option: str) -> None:
        """Set the current option for a user"""
        if not option:
            raise InvalidOptionError("Option cannot be empty")

        try:
            state = self.get_state(user_id)
            state["option"] = option
            self.update_state(
                user_id=user_id,
                new_state=state,
                stage=state["stage"],
                update_from="set_option",
                option=option
            )
            logger.info(f"Set option for user {user_id} to {option}")
        except Exception as e:
            logger.error(f"Error setting option for user {user_id}: {str(e)}")
            raise

    def get_member_info(self, user_id: str) -> Dict[str, Any]:
        """Get member information for a user"""
        state = self.get_state(user_id)
        return state.get("member", {})

    def update_member_info(self, user_id: str, new_info: Dict[str, Any]) -> None:
        """Update member information for a user"""
        if not isinstance(new_info, dict):
            raise InvalidStateError("Member info must be a dictionary")

        try:
            state = self.get_state(user_id)
            current_member_info = state.get("member", {})
            current_member_info.update(new_info)
            state["member"] = current_member_info

            self.update_state(
                user_id=user_id,
                new_state=state,
                stage=state["stage"],
                update_from="update_member_info"
            )
            logger.info(f"Updated member info for user {user_id}")
        except Exception as e:
            logger.error(f"Error updating member info for user {user_id}: {str(e)}")
            raise

    def clear_member_info(self, user_id: str) -> None:
        """Clear member information for a user"""
        try:
            state = self.get_state(user_id)
            state["member"] = {}

            self.update_state(
                user_id=user_id,
                new_state=state,
                stage=state["stage"],
                update_from="clear_member_info"
            )
            logger.info(f"Cleared member info for user {user_id}")
        except Exception as e:
            logger.error(f"Error clearing member info for user {user_id}: {str(e)}")
            raise
