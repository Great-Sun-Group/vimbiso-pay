"""Core state management with SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional, Tuple

from services.credex.service import CredExService

from core.utils.state_validator import StateValidator

from .config import ACTIVITY_TTL, atomic_state
from .state_utils import (create_initial_state, prepare_state_update,
                          update_critical_fields)

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

        # Create initial state if none exists
        if not state_data:
            state_data = create_initial_state()
            if not state_data:
                raise ValueError("Failed to create initial state")

        # Extract channel ID from key prefix
        if self.key_prefix.startswith("channel:"):
            channel_id = self.key_prefix.split(":", 1)[1]
            if not channel_id:
                raise ValueError("Invalid channel ID in key prefix")

            # Validate channel structure
            if not isinstance(state_data.get("channel"), dict):
                raise ValueError("Invalid channel structure")

            # Update channel identifier (SINGLE SOURCE OF TRUTH)
            state_data["channel"] = {
                "type": "whatsapp",
                "identifier": channel_id,
                "metadata": state_data.get("channel", {}).get("metadata", {})
            }

        # Validate complete state
        validation = StateValidator.validate_state(state_data)
        if not validation.is_valid:
            raise ValueError(f"Invalid initial state: {validation.error_message}")

        # Store state in Redis
        success, error = atomic_state.atomic_update(self.key_prefix, state_data, ACTIVITY_TTL)
        if not success:
            raise ValueError(f"Failed to store state: {error}")

        return state_data

    def update_state(self, updates: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Update state enforcing SINGLE SOURCE OF TRUTH"""
        # Validate at boundary
        if not isinstance(updates, dict):
            raise ValueError("Updates must be a dictionary")

        try:
            # Validate updates before processing
            validation = StateValidator.validate_state(updates)
            if not validation.is_valid:
                raise ValueError(f"Invalid state update: {validation.error_message}")

            # Validate critical fields
            for field in ["member_id", "channel"]:
                if field in updates:
                    validation = StateValidator.validate_before_access(updates, {field})
                    if not validation.is_valid:
                        raise ValueError(f"Invalid {field} update: {validation.error_message}")

            # Update critical fields first (SINGLE SOURCE OF TRUTH)
            new_state = update_critical_fields(self._state, updates)
            if not new_state:
                raise ValueError("Failed to update critical fields")

            # Handle remaining updates
            new_state = prepare_state_update(new_state, updates)
            if not new_state:
                raise ValueError("Failed to prepare state update")

            # Validate complete state
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                raise ValueError(f"Invalid resulting state: {validation.error_message}")

            # Store in Redis
            success, error = atomic_state.atomic_update(
                self.key_prefix, new_state, ACTIVITY_TTL
            )
            if not success:
                raise ValueError(f"Failed to store state: {error}")

            # Update internal state
            self._state = new_state

            # Update service token if needed (SINGLE SOURCE OF TRUTH)
            if self._credex_service and "jwt_token" in updates:
                self._credex_service.update_token(updates["jwt_token"])

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
        if key in ["member_id", "channel"]:
            if not self._state.get(key):
                raise ValueError(f"Required field {key} not found in state")

        return self._state.get(key)

    def get_or_create_credex_service(self) -> CredExService:
        """Get or create CredEx service instance with proper state access"""
        if not self._credex_service:
            # Create service with state access functions
            self._credex_service = CredExService(
                get_token=lambda: self.get("jwt_token"),
                get_member_id=lambda: self.get("member_id"),
                get_channel=lambda: self.get("channel"),
                on_token_update=lambda token: self.update_state({"jwt_token": token})
            )

        return self._credex_service
