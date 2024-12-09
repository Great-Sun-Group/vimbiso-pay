import logging
from typing import Any, Dict, Optional

from .exceptions import (
    InvalidOptionError,
    InvalidStateError,
    InvalidStageError,
    InvalidUserError,
    StateNotFoundError,
)
from .interface import StateServiceInterface

logger = logging.getLogger(__name__)


class StateService(StateServiceInterface):
    """Implementation of the state management service"""

    def __init__(self, redis_client):
        """Initialize the state service with a Redis client"""
        self.redis = redis_client
        self.state_key_prefix = "user_state:"

    def _validate_user_id(self, user_id: str) -> None:
        """Validate user ID"""
        if not user_id or not isinstance(user_id, str):
            logger.error(f"Invalid user ID provided: {user_id}")
            raise InvalidUserError(f"Invalid user ID: {user_id}")

    def _get_state_key(self, user_id: str) -> str:
        """Generate Redis key for user state"""
        return f"{self.state_key_prefix}{user_id}"

    def _validate_state_data(self, state_data: Dict[str, Any]) -> None:
        """Validate state data structure"""
        required_fields = {"stage", "option"}
        if not isinstance(state_data, dict):
            raise InvalidStateError("State must be a dictionary")
        if not all(field in state_data for field in required_fields):
            raise InvalidStateError(f"State must contain fields: {required_fields}")

    def get_state(self, user_id: str) -> Dict[str, Any]:
        """Retrieve the current state for a user"""
        self._validate_user_id(user_id)

        try:
            state_key = self._get_state_key(user_id)
            state = self.redis.hgetall(state_key)

            if not state:
                logger.warning(f"No state found for user {user_id}")
                raise StateNotFoundError(f"No state found for user {user_id}")

            return state
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
        """Update the state for a user"""
        self._validate_user_id(user_id)
        self._validate_state_data(new_state)

        try:
            state_key = self._get_state_key(user_id)

            # Update state with new values
            new_state.update({
                "stage": stage,
                "update_from": update_from,
                "option": option if option is not None else ""
            })

            # Store in Redis
            self.redis.hmset(state_key, new_state)
            logger.info(f"Updated state for user {user_id}: stage={stage}, update_from={update_from}")
        except Exception as e:
            logger.error(f"Error updating state for user {user_id}: {str(e)}")
            raise

    def reset_state(self, user_id: str) -> None:
        """Reset the state for a user"""
        self._validate_user_id(user_id)

        try:
            state_key = self._get_state_key(user_id)
            self.redis.delete(state_key)
            logger.info(f"Reset state for user {user_id}")
        except Exception as e:
            logger.error(f"Error resetting state for user {user_id}: {str(e)}")
            raise

    def get_stage(self, user_id: str) -> str:
        """Get the current stage for a user"""
        state = self.get_state(user_id)
        return state.get("stage", "")

    def set_stage(self, user_id: str, stage: str) -> None:
        """Set the current stage for a user"""
        if not stage:
            raise InvalidStageError("Stage cannot be empty")

        try:
            state = self.get_state(user_id)
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
