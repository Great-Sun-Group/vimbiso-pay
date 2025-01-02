import logging
from typing import Any, Dict, Optional, Tuple

from core.utils.exceptions import StateException
from core.utils.state_validator import StateValidator
from core.config.atomic_state import AtomicStateManager
from .state_utils import _update_state_core
from django.core.cache import cache

logger = logging.getLogger(__name__)

class StateManager:
    """Manages state while enforcing SINGLE SOURCE OF TRUTH"""


    def __init__(self, key_prefix: str):
        """Initialize with key prefix"""
        self.atomic_state = AtomicStateManager(cache)
        if not key_prefix or not key_prefix.startswith("channel:"):
            raise StateException("Invalid key prefix - must start with 'channel:'")
        self.key_prefix = key_prefix
        self._state = self._initialize_state()

    def _initialize_state(self) -> Dict[str, Any]:
        """Initialize state with proper structure enforcing SINGLE SOURCE OF TRUTH"""
        channel_id = self.key_prefix.split(":", 1)[1]
        initial_state = {"channel": {"type": "whatsapp", "identifier": channel_id}}
        state_data, get_error = self.atomic_state.atomic_get(self.key_prefix)
        print(get_error)
        if get_error:
            raise StateException(f"Failed to get state: {get_error}")
        if state_data is None:
            state_data = initial_state
        validation = StateValidator.validate_state(state_data)
        if not validation.is_valid:
            state_data["flow_data"] = {}
        return state_data

    def update_state(self, updates: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Update state enforcing SINGLE SOURCE OF TRUTH"""
        if not isinstance(updates, dict):
            raise StateException("Updates must be a dictionary")
        merged_state = {**self._state, **updates}
        validation = StateValidator.validate_state(merged_state)
        if not validation.is_valid:
            raise StateException(f"Invalid state after update: {validation.error_message}")
        return _update_state_core(self, updates)

    def get(self, key: str) -> Any:
        """Get value from state enforcing SINGLE SOURCE OF TRUTH"""
        if not key or not isinstance(key, str):
            raise StateException("Key must be a non-empty string")
        if key in StateValidator.CRITICAL_FIELDS:
            validation = StateValidator.validate_before_access(self._state, {key})
            if not validation.is_valid:
                raise StateException(f"Invalid state access: {validation.error_message}")
        return self._state.get(key)

    def get_flow_type(self) -> Optional[str]:
        """Get flow type"""
        flow_data = self.get("flow_data") or {}
        return flow_data.get("flow_type")


    def get_flow_state(self) -> Dict[str, Any]:
        """Get validated flow state"""
        flow_data = self.get("flow_data") or {}
        validation = StateValidator._validate_flow_data(flow_data, self._state)
        if not validation.is_valid:
            raise StateException(f"Invalid flow state: {validation.error_message}")
        return flow_data

    def get_channel_data(self) -> Dict[str, Any]:
        """Get validated channel data"""
        channel = self.get("channel")
        validation = StateValidator._validate_channel_data(channel)
        if not validation.is_valid:
            raise StateException(f"Invalid channel data: {validation.error_message}")
        return channel

    def get_flow_step_data(self) -> Dict[str, Any]:
        """Get validated flow step data"""
        flow_data = self.get_flow_state()
        return flow_data.get("data", {})

    def get_channel_id(self) -> str:
        """Get channel identifier enforcing SINGLE SOURCE OF TRUTH"""
        channel = self.get("channel")
        if not channel or not channel.get("identifier"):
            raise StateException("Channel identifier not found")
        return channel["identifier"]

    def get_active_account(self) -> Optional[Dict[str, Any]]:
        """Get active account enforcing SINGLE SOURCE OF TRUTH"""
        accounts = self.get("accounts")
        active_id = self.get("active_account_id")
        if not accounts or not active_id:
            return None
        return next((account for account in accounts if account["accountID"] == active_id), None)

    def get_current_step(self) -> Optional[str]:
        """Get current flow step"""
        flow_data = self.get("flow_data") or {}
        return flow_data.get("current_step")