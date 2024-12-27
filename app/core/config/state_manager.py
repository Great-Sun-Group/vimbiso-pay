"""Core state management with SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional, Tuple

from services.credex.service import create_credex_service

from core.utils.state_validator import StateValidator

from .config import ACTIVITY_TTL, atomic_state
from .state_utils import prepare_state_update

logger = logging.getLogger(__name__)


class StateManager:
    """Manages state while enforcing SINGLE SOURCE OF TRUTH"""

    def __init__(self, key_prefix: str):
        """Initialize with key prefix"""
        self.key_prefix = key_prefix
        self._state = self._initialize_state()
        self._credex_service = None

    def _initialize_state(self) -> Dict[str, Any]:
        """Initialize state with proper structure enforcing SINGLE SOURCE OF TRUTH"""
        # Validate at boundary
        if not self.key_prefix:
            raise ValueError("Key prefix is required")

        # Get existing state
        state_data, error = atomic_state.atomic_get(self.key_prefix)
        if error:
            logger.error(f"Error getting state: {error}")
            raise ValueError(f"Failed to get state: {error}")

        # Validate key prefix and get channel ID
        if not self.key_prefix.startswith("channel:"):
            logger.error("Invalid key prefix format")
            raise ValueError("Invalid key prefix - must start with 'channel:'")

        channel_id = self.key_prefix.split(":", 1)[1]
        if not channel_id:
            logger.error("Invalid channel ID in key prefix")
            raise ValueError("Invalid channel ID in key prefix")

        # Initialize or update state with required fields
        if not state_data or not isinstance(state_data, dict):
            state_data = {}

        # Ensure all required fields exist (SINGLE SOURCE OF TRUTH)
        state_data.update({
            "channel": {
                "type": "whatsapp",
                "identifier": channel_id,
                "metadata": state_data.get("channel", {}).get("metadata", {})
            },
            "member_id": state_data.get("member_id", None),
            "jwt_token": state_data.get("jwt_token", None),
            "authenticated": state_data.get("authenticated", False),
            "flow_data": state_data.get("flow_data", None)
        })

        # Validate complete state
        validation = StateValidator.validate_state(state_data)
        if not validation.is_valid:
            logger.error(f"Invalid state structure: {validation.error_message}")
            raise ValueError(f"Invalid state structure: {validation.error_message}")

        # Store validated state
        success, error = atomic_state.atomic_update(self.key_prefix, state_data, ACTIVITY_TTL)
        if not success:
            logger.error(f"Failed to store state: {error}")
            raise ValueError(f"Failed to store state: {error}")

        logger.info(f"Initialized state for channel: {channel_id}")

        return state_data

    def update_state(self, updates: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Update state enforcing SINGLE SOURCE OF TRUTH"""
        # Validate at boundary
        if not isinstance(updates, dict):
            raise ValueError("Updates must be a dictionary")

        try:
            # Validate only fields being updated
            fields_to_validate = set(updates.keys())
            if fields_to_validate:
                validation = StateValidator.validate_before_access(updates, fields_to_validate)
                if not validation.is_valid:
                    raise ValueError(f"Invalid update: {validation.error_message}")

            # Prepare state update (validation handled by state_utils)
            new_state = prepare_state_update(self._state, updates)
            if not new_state:
                raise ValueError("Failed to prepare state update")

            # Store in Redis
            success, error = atomic_state.atomic_update(
                self.key_prefix, new_state, ACTIVITY_TTL
            )
            if not success:
                raise ValueError(f"Failed to store state: {error}")

            # Update internal state
            self._state = new_state

            return True, None

        except ValueError as e:
            logger.error(f"State update error: {str(e)}")
            return False, str(e)

    def get(self, key: str) -> Any:
        """Get value from state enforcing SINGLE SOURCE OF TRUTH"""
        # Validate at boundary
        if not key:
            raise ValueError("Key is required")
        if not isinstance(key, str):
            raise ValueError("Key must be a string")

        # Validate state access
        validation = StateValidator.validate_before_access(self._state, {key})
        if not validation.is_valid:
            raise ValueError(f"Invalid state access: {validation.error_message}")

        # Validate critical fields
        if key == "channel" and not self._state.get(key):
            raise ValueError("Required field channel not found in state")

        return self._state.get(key)

    def get_or_create_credex_service(self) -> Dict[str, Any]:
        """Get or create CredEx service instance with proper state access"""
        if not self._credex_service:
            # Create service with state access functions
            self._credex_service = create_credex_service(
                get_token=lambda: self.get("jwt_token"),
                get_member_id=lambda: self.get("member_id"),
                get_channel=lambda: self.get("channel"),
                on_token_update=lambda token: self.update_state({"jwt_token": token})
            )

        return self._credex_service
