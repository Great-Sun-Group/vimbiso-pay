"""State service interface and base implementation"""
import json
import time
from typing import Any, Dict, Optional
from .exceptions import StateNotFoundError, InvalidStateError, InvalidStageError, InvalidOptionError, InvalidUserError
from .config import RedisConfig

from redis.exceptions import RedisError

from .config import RedisConfig
from .exceptions import StateValidationError, StateOperationError


class StateService:
    """Base implementation of state management service"""

    def __init__(self, redis_client=None):
        """Initialize with optional Redis client"""
        self.redis = redis_client or RedisConfig().get_client()
        self.state_ttl = 3600  # Time-to-live for state in seconds

        # Verify Redis connection
        try:
            self.redis.ping()
        except RedisError as e:
            raise StateOperationError("Could not connect to Redis", cause=e)

    def _get_state_key(self, user_id: str) -> str:
        """Generate Redis key for user state"""
        return f"state:{user_id}"

    def _validate_user_id(self, user_id: str) -> None:
        """Validate user ID"""
        if not user_id:
            raise StateValidationError("User ID cannot be empty")

    def get_state(self, user_id: str) -> Dict[str, Any]:
        """Get current state for user"""
        self._validate_user_id(user_id)
        state_key = self._get_state_key(user_id)

        try:
            state_data = self.redis.get(state_key)
            if not state_data:
                raise StateOperationError(f"State not found for user {user_id}")
            return json.loads(state_data)
        except RedisError as e:
            raise StateOperationError("Failed to retrieve state", cause=e)
        except json.JSONDecodeError:
            raise StateOperationError("Corrupted state data")

    def update_state(
        self,
        user_id: str,
        new_state: Dict[str, Any],
        stage: str,
        update_from: str,
        option: Optional[str] = None
    ) -> None:
        """Update state with atomic operation"""
        self._validate_user_id(user_id)
        state_key = self._get_state_key(user_id)

        try:
            # Use Redis transaction for atomic update
            with self.redis.pipeline() as pipe:
                while True:
                    try:
                        # Watch key for changes
                        pipe.watch(state_key)

                        # Get current state for version tracking
                        current_data = pipe.get(state_key)
                        current_state = json.loads(current_data) if current_data else {}
                        current_version = current_state.get("version", 0)

                        # Update state metadata
                        new_state.update({
                            "stage": stage,
                            "update_from": update_from,
                            "option": option if option is not None else "",
                            "last_updated": time.time(),
                            "version": current_version + 1
                        })

                        # Execute transaction
                        pipe.multi()
                        pipe.set(state_key, json.dumps(new_state), ex=self.state_ttl)
                        pipe.execute()
                        break

                    except RedisError as e:
                        raise StateOperationError("Failed to update state", cause=e)

        except Exception as e:
            raise StateOperationError(f"Error updating state for user {user_id}: {str(e)}")

    def reset_state(self, user_id: str, preserve_auth: bool = True) -> None:
        """Reset state with optional auth preservation"""
        self._validate_user_id(user_id)
        state_key = self._get_state_key(user_id)

        try:
            with self.redis.pipeline() as pipe:
                while True:
                    try:
                        pipe.watch(state_key)

                        if preserve_auth:
                            current_data = pipe.get(state_key)
                            if current_data:
                                current_state = json.loads(current_data)
                                jwt_token = current_state.get("jwt_token")
                                current_version = current_state.get("version", 0)

                                if jwt_token:
                                    new_state = {
                                        "stage": "INIT",
                                        "option": "",
                                        "jwt_token": jwt_token,
                                        "last_updated": time.time(),
                                        "version": current_version + 1
                                    }
                                    pipe.multi()
                                    pipe.set(state_key, json.dumps(new_state), ex=self.state_ttl)
                                    pipe.execute()
                                    return

                        # If no auth to preserve or no current state
                        pipe.multi()
                        pipe.delete(state_key)
                        pipe.execute()
                        break

                    except RedisError as e:
                        raise StateOperationError("Failed to reset state", cause=e)

        except Exception as e:
            raise StateOperationError(f"Error resetting state for user {user_id}: {str(e)}")

    def get_stage(self, user_id: str) -> str:
        """Get current stage"""
        state = self.get_state(user_id)
        return state.get("stage", "INIT")

    def set_stage(self, user_id: str, stage: str) -> None:
        """Set stage with validation"""
        if not stage:
            raise StateValidationError("Stage cannot be empty")

        try:
            state = self.get_state(user_id)
            state["stage"] = stage
            self.update_state(user_id, state, stage, "set_stage")
        except Exception as e:
            raise StateOperationError(f"Error setting stage for user {user_id}: {str(e)}")

    def get_option(self, user_id: str) -> Optional[str]:
        """Get current option"""
        state = self.get_state(user_id)
        return state.get("option")

    def set_option(self, user_id: str, option: str) -> None:
        """Set option with validation"""
        if not option:
            raise StateValidationError("Option cannot be empty")

        try:
            state = self.get_state(user_id)
            state["option"] = option
            self.update_state(user_id, state, state["stage"], "set_option", option)
        except Exception as e:
            raise StateOperationError(f"Error setting option for user {user_id}: {str(e)}")

    def get_member_info(self, user_id: str) -> Dict[str, Any]:
        """Get member information"""
        state = self.get_state(user_id)
        return state.get("member", {})

    def update_member_info(self, user_id: str, new_info: Dict[str, Any]) -> None:
        """Update member information with validation"""
        if not isinstance(new_info, dict):
            raise StateValidationError("Member info must be a dictionary")

        try:
            state = self.get_state(user_id)
            current_member_info = state.get("member", {})
            current_member_info.update(new_info)
            state["member"] = current_member_info
            self.update_state(user_id, state, state["stage"], "update_member_info")
        except Exception as e:
            raise StateOperationError(f"Error updating member info for user {user_id}: {str(e)}")

    def clear_member_info(self, user_id: str) -> None:
        """Clear member information"""
        try:
            state = self.get_state(user_id)
            state["member"] = {}
            self.update_state(user_id, state, state["stage"], "clear_member_info")
        except Exception as e:
            raise StateOperationError(f"Error clearing member info for user {user_id}: {str(e)}")
