"""Core state management with SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.utils.exceptions import StateException
from core.utils.state_validator import StateValidator

from .config import ACTIVITY_TTL, atomic_state

logger = logging.getLogger(__name__)

# Critical fields that must never be transformed
CRITICAL_FIELDS = {"channel"}


class StateManager:
    """Manages state while enforcing SINGLE SOURCE OF TRUTH"""

    def __init__(self, key_prefix: str):
        """Initialize with key prefix"""
        if not key_prefix:
            raise StateException("Key prefix is required")
        if not key_prefix.startswith("channel:"):
            raise StateException("Invalid key prefix - must start with 'channel:'")

        self.key_prefix = key_prefix
        self._state = self._initialize_state()

    def _initialize_state(self) -> Dict[str, Any]:
        """Initialize state with proper structure enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Get channel ID from key prefix
            channel_id = self.key_prefix.split(":", 1)[1]
            if not channel_id:
                raise StateException("Invalid channel ID in key prefix")

            # Create valid initial state
            initial_state = {
                "channel": {
                    "type": "whatsapp",
                    "identifier": channel_id,
                    "metadata": {}
                },
                "member_id": None,
                "jwt_token": None,
                "authenticated": False,
                "account_id": None,
                "flow_data": {}  # Initialize as empty dict instead of None
            }

            # Validate initial state structure
            validation = StateValidator.validate_state(initial_state)
            if not validation.is_valid:
                raise StateException(f"Invalid initial state structure: {validation.error_message}")

            # Try to get existing state first
            logger.info(f"Getting existing state for key: {self.key_prefix}")
            state_data, get_error = atomic_state.atomic_get(self.key_prefix)
            logger.info(f"Got state data: {state_data}")

            if get_error:
                logger.error(f"Error getting state: {get_error}")
                raise StateException(f"Failed to get state: {get_error}")

            # If no existing state, use initial state
            if state_data is None:
                logger.info("No existing state found, using initial state")
                state_data = initial_state
            else:
                # Validate existing state
                logger.info("Validating existing state")
                validation = StateValidator.validate_state(state_data)
                if not validation.is_valid:
                    logger.warning(f"Invalid state structure: {validation.error_message}")
                    state_data = initial_state

            # Update state in Redis
            logger.info(f"Updating state in Redis for channel {channel_id}: {state_data}")
            success, error = atomic_state.atomic_update(self.key_prefix, state_data, ACTIVITY_TTL)
            if not success:
                raise StateException(f"Failed to update state: {error}")

            logger.info(f"Successfully initialized state for channel {channel_id}: {state_data}")
            return state_data

        except StateException as e:
            logger.error(f"State initialization error: {str(e)}")
            raise

    def update_state(self, updates: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Update state enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate at boundary
            if not isinstance(updates, dict):
                raise StateException("Updates must be a dictionary")

            # Validate only fields being updated
            fields_to_validate = set(updates.keys())
            if fields_to_validate:
                validation = StateValidator.validate_before_access(updates, fields_to_validate)
                if not validation.is_valid:
                    raise StateException(f"Invalid update: {validation.error_message}")

            # Validate critical fields are not being modified
            if any(field in updates for field in CRITICAL_FIELDS):
                raise StateException("Cannot modify critical fields")

            # Create new state without transformation
            new_state = self._state.copy()

            # Handle state updates without transformation
            for key, value in updates.items():
                if key == "flow_data" and isinstance(value, dict):
                    # Special handling for flow_data to preserve structure
                    current_flow_data = new_state.get("flow_data", {})
                    if isinstance(current_flow_data, dict):
                        # Update nested flow data while preserving structure
                        if "data" in value:
                            current_data = current_flow_data.get("data", {})
                            if isinstance(current_data, dict):
                                current_data.update(value["data"])
                                value["data"] = current_data
                        new_state["flow_data"] = {**current_flow_data, **value}
                    else:
                        new_state["flow_data"] = value
                elif isinstance(value, dict) and isinstance(new_state.get(key), dict):
                    # For other dictionary fields, update nested values
                    new_state[key].update(value)
                else:
                    # For non-dictionary fields or new fields, set directly
                    new_state[key] = value

            logger.debug(f"Updated state: {new_state}")

            # Validate complete state
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                raise StateException(f"Invalid state after update: {validation.error_message}")

            # Store validated state
            success, error = atomic_state.atomic_update(
                self.key_prefix, new_state, ACTIVITY_TTL
            )
            if not success:
                raise StateException(f"Failed to store state: {error}")

            # Update internal state
            self._state = new_state

            return True, None

        except StateException as e:
            logger.error(f"State update error: {str(e)}")
            return False, str(e)

    def get(self, key: str) -> Any:
        """Get value from state enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate at boundary
            if not key:
                raise StateException("Key is required")
            if not isinstance(key, str):
                raise StateException("Key must be a string")

            # Validate state access
            validation = StateValidator.validate_before_access(self._state, {key})
            if not validation.is_valid:
                raise StateException(f"Invalid state access: {validation.error_message}")

            # Validate critical fields
            if key == "channel" and not self._state.get(key):
                raise StateException("Required field channel not found in state")

            return self._state.get(key)

        except StateException as e:
            logger.error(f"State access error: {str(e)}")
            raise
