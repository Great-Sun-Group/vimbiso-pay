import json
import time
import redis
from typing import Any, Dict, Optional
from .exceptions import StateNotFoundError, InvalidStateError, InvalidStageError, InvalidOptionError, InvalidUserError
from .config import RedisConfig

class StateService:
    """Implementation of the StateServiceInterface"""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client or RedisConfig().get_client()
        self.state_ttl = 3600  # Time-to-live for state in seconds

    def _get_state_key(self, user_id: str) -> str:
        return f"state:{user_id}"

    def _validate_user_id(self, user_id: str) -> None:
        if not user_id:
            raise InvalidUserError("User ID cannot be empty")

    def _acquire_lock(self, user_id: str) -> bool:
        # Implement lock acquisition logic
        return True

    def _release_lock(self, user_id: str) -> None:
        # Implement lock release logic
        pass

    def get_state(self, user_id: str) -> Dict[str, Any]:
        self._validate_user_id(user_id)
        state_key = self._get_state_key(user_id)
        state_data = self.redis.get(state_key)
        if not state_data:
            raise StateNotFoundError(f"State not found for user {user_id}")
        return json.loads(state_data)

    def update_state(
        self,
        user_id: str,
        new_state: Dict[str, Any],
        stage: str,
        update_from: str,
        option: Optional[str] = None
    ) -> None:
        self._validate_user_id(user_id)
        if not self._acquire_lock(user_id):
            raise InvalidStateError("Could not acquire state lock")

        try:
            state_key = self._get_state_key(user_id)
            new_state.update({
                "stage": stage,
                "update_from": update_from,
                "option": option if option is not None else "",
                "last_updated": time.time()
            })
            self.redis.set(state_key, json.dumps(new_state), ex=self.state_ttl)
        except Exception as e:
            raise InvalidStateError(f"Error updating state for user {user_id}: {str(e)}")
        finally:
            self._release_lock(user_id)

    def reset_state(self, user_id: str, preserve_auth: bool = True) -> None:
        self._validate_user_id(user_id)
        if not self._acquire_lock(user_id):
            raise InvalidStateError("Could not acquire state lock")

        try:
            state_key = self._get_state_key(user_id)
            if preserve_auth:
                try:
                    current_state = self.get_state(user_id)
                    jwt_token = current_state.get("jwt_token")
                    if jwt_token:
                        new_state = {
                            "stage": "INIT",
                            "option": "",
                            "jwt_token": jwt_token,
                            "last_updated": time.time()
                        }
                        self.redis.set(state_key, json.dumps(new_state), ex=self.state_ttl)
                        return
                except StateNotFoundError:
                    pass
            self.redis.delete(state_key)
        except Exception as e:
            raise InvalidStateError(f"Error resetting state for user {user_id}: {str(e)}")
        finally:
            self._release_lock(user_id)

    def get_stage(self, user_id: str) -> str:
        state = self.get_state(user_id)
        return state.get("stage", "INIT")

    def set_stage(self, user_id: str, stage: str) -> None:
        if not stage:
            raise InvalidStageError("Stage cannot be empty")

        try:
            state = self.get_state(user_id)
            current_stage = state.get("stage")
            if not self._is_valid_transition(current_stage, stage):
                raise InvalidStageError(f"Invalid state transition from {current_stage} to {stage}")
            state["stage"] = stage
            self.update_state(user_id, state, stage, "set_stage")
        except Exception as e:
            raise InvalidStageError(f"Error setting stage for user {user_id}: {str(e)}")

    def get_option(self, user_id: str) -> Optional[str]:
        state = self.get_state(user_id)
        return state.get("option")

    def set_option(self, user_id: str, option: str) -> None:
        if not option:
            raise InvalidOptionError("Option cannot be empty")

        try:
            state = self.get_state(user_id)
            state["option"] = option
            self.update_state(user_id, state, state["stage"], "set_option", option)
        except Exception as e:
            raise InvalidOptionError(f"Error setting option for user {user_id}: {str(e)}")

    def get_member_info(self, user_id: str) -> Dict[str, Any]:
        state = self.get_state(user_id)
        return state.get("member", {})

    def update_member_info(self, user_id: str, new_info: Dict[str, Any]) -> None:
        if not isinstance(new_info, dict):
            raise InvalidStateError("Member info must be a dictionary")

        try:
            state = self.get_state(user_id)
            current_member_info = state.get("member", {})
            current_member_info.update(new_info)
            state["member"] = current_member_info
            self.update_state(user_id, state, state["stage"], "update_member_info")
        except Exception as e:
            raise InvalidStateError(f"Error updating member info for user {user_id}: {str(e)}")

    def clear_member_info(self, user_id: str) -> None:
        try:
            state = self.get_state(user_id)
            state["member"] = {}
            self.update_state(user_id, state, state["stage"], "clear_member_info")
        except Exception as e:
            raise InvalidStateError(f"Error clearing member info for user {user_id}: {str(e)}")

    def _is_valid_transition(self, current_stage: str, new_stage: str) -> bool:
        # Implement state transition validation logic
        return True