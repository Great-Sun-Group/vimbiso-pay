import logging
from typing import Any, Dict, Optional
from enum import Enum
import json
import time

from .exceptions import (
    InvalidOptionError,
    InvalidStateError,
    InvalidStageError,
    InvalidUserError,
    StateNotFoundError,
)
from .interface import StateServiceInterface

logger = logging.getLogger(__name__)


class StateStage(Enum):
    """Valid state stages"""
    INIT = "init"
    AUTH = "auth"
    MENU = "menu"
    CREDEX = "credex"
    ACCOUNT = "account"


class StateTransition:
    """Represents valid state transitions"""
    VALID_TRANSITIONS = {
        StateStage.INIT: [StateStage.AUTH, StateStage.MENU],
        StateStage.AUTH: [StateStage.MENU],
        StateStage.MENU: [StateStage.CREDEX, StateStage.ACCOUNT, StateStage.AUTH],
        StateStage.CREDEX: [StateStage.MENU],
        StateStage.ACCOUNT: [StateStage.MENU]
    }

    @classmethod
    def is_valid_transition(cls, from_stage: str, to_stage: str) -> bool:
        """Check if state transition is valid"""
        try:
            from_enum = StateStage(from_stage)
            to_enum = StateStage(to_stage)
            return to_enum in cls.VALID_TRANSITIONS.get(from_enum, [])
        except ValueError:
            return False


class StateService(StateServiceInterface):
    """Implementation of the state management service with proper state machine"""

    def __init__(self, redis_client):
        """Initialize the state service with a Redis client"""
        self.redis = redis_client
        self.state_key_prefix = "user_state:"
        self.state_lock_prefix = "user_state_lock:"
        self.state_ttl = 3600  # 1 hour TTL for state

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
        """Acquire lock for state updates with timeout"""
        lock_key = self._get_lock_key(user_id)
        end_time = time.time() + timeout

        while time.time() < end_time:
            if self.redis.setnx(lock_key, "1"):
                self.redis.expire(lock_key, 30)  # Lock expires after 30 seconds
                return True
            time.sleep(0.1)
        return False

    def _release_lock(self, user_id: str) -> None:
        """Release state update lock"""
        self.redis.delete(self._get_lock_key(user_id))

    def _validate_state_data(self, state_data: Dict[str, Any]) -> None:
        """Validate state data structure and required fields"""
        required_fields = {"stage", "option"}
        if not isinstance(state_data, dict):
            raise InvalidStateError("State must be a dictionary")
        if not all(field in state_data for field in required_fields):
            raise InvalidStateError(f"State must contain fields: {required_fields}")

    def _preserve_auth_token(self, user_id: str, new_state: Dict[str, Any]) -> Dict[str, Any]:
        """Preserve JWT token when updating state"""
        try:
            current_state = self.get_state(user_id)
            if "jwt_token" in current_state and "jwt_token" not in new_state:
                new_state["jwt_token"] = current_state["jwt_token"]
        except StateNotFoundError:
            pass
        return new_state

    def get_state(self, user_id: str) -> Dict[str, Any]:
        """Retrieve the current state for a user"""
        self._validate_user_id(user_id)

        try:
            state_key = self._get_state_key(user_id)
            state_json = self.redis.get(state_key)

            if not state_json:
                logger.warning(f"No state found for user {user_id}")
                raise StateNotFoundError(f"No state found for user {user_id}")

            return json.loads(state_json)
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
        """Update the state for a user with proper locking and validation"""
        self._validate_user_id(user_id)
        self._validate_state_data(new_state)

        if not self._acquire_lock(user_id):
            raise InvalidStateError("Could not acquire state lock")

        try:
            state_key = self._get_state_key(user_id)
            current_state = self.get_state(user_id)

            # Validate state transition
            if not StateTransition.is_valid_transition(current_state.get("stage"), stage):
                raise InvalidStageError(f"Invalid state transition from {current_state.get('stage')} to {stage}")

            # Preserve auth token
            new_state = self._preserve_auth_token(user_id, new_state)

            # Update state with new values
            new_state.update({
                "stage": stage,
                "update_from": update_from,
                "option": option if option is not None else "",
                "last_updated": time.time()
            })

            # Store in Redis with TTL
            self.redis.setex(
                state_key,
                self.state_ttl,
                json.dumps(new_state)
            )
            logger.info(f"Updated state for user {user_id}: stage={stage}, update_from={update_from}")
        except Exception as e:
            logger.error(f"Error updating state for user {user_id}: {str(e)}")
            raise
        finally:
            self._release_lock(user_id)

    def reset_state(self, user_id: str, preserve_auth: bool = True) -> None:
        """Reset the state for a user with option to preserve auth token"""
        self._validate_user_id(user_id)

        if not self._acquire_lock(user_id):
            raise InvalidStateError("Could not acquire state lock")

        try:
            state_key = self._get_state_key(user_id)

            if preserve_auth:
                current_state = self.get_state(user_id)
                jwt_token = current_state.get("jwt_token")

                if jwt_token:
                    new_state = {
                        "stage": StateStage.INIT.value,
                        "option": "",
                        "jwt_token": jwt_token,
                        "last_updated": time.time()
                    }
                    self.redis.setex(
                        state_key,
                        self.state_ttl,
                        json.dumps(new_state)
                    )
                    logger.info(f"Reset state for user {user_id} preserving JWT token")
                    return

            self.redis.delete(state_key)
            logger.info(f"Reset state for user {user_id}")
        except Exception as e:
            logger.error(f"Error resetting state for user {user_id}: {str(e)}")
            raise
        finally:
            self._release_lock(user_id)

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

            # Validate state transition
            if not StateTransition.is_valid_transition(state.get("stage"), stage):
                raise InvalidStageError(f"Invalid state transition from {state.get('stage')} to {stage}")

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
