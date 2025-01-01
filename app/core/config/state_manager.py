"""Core state management with SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.utils.exceptions import StateException
from core.utils.state_validator import StateValidator

from .config import atomic_state
from .state_utils import _update_state_core

logger = logging.getLogger(__name__)


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
                "accounts": [],
                "active_account_id": None,
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
                    # Only reset flow data on validation failure
                    logger.warning(f"Invalid state structure: {validation.error_message}")
                    state_data["flow_data"] = {}

            logger.info(f"Successfully loaded state for channel {channel_id}: {state_data}")
            return state_data

        except StateException as e:
            logger.error(f"State initialization error: {str(e)}")
            raise

    def update_state(self, updates: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Update state enforcing SINGLE SOURCE OF TRUTH

        This is the main entry point for all state updates. It detects the type of update
        and routes to the appropriate utility function.

        Args:
            updates: Dictionary of updates to apply. The structure determines the type of update:

            1. Flow State Update:
            {
                "flow_data": {
                    "flow_type": str,
                    "step": int,
                    "current_step": str
                }
            }

            2. Flow Data Update:
            {
                "flow_data": {
                    "data": Dict[str, Any]
                }
            }

            3. Flow Advance:
            {
                "flow_data": {
                    "next_step": str,
                    "data": Dict[str, Any] (optional)
                }
            }

            4. Direct State Update:
            Any other structure will be treated as a direct state update

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Validate at boundary
            if not isinstance(updates, dict):
                raise StateException("Updates must be a dictionary")

            # Handle flow data updates first
            if "flow_data" in updates:
                flow_data = updates["flow_data"]
                if not isinstance(flow_data, dict):
                    raise StateException("flow_data must be a dictionary")

                # Get current flow data
                current_flow = self.get("flow_data") or {}

                # Handle empty flow_data
                if not flow_data:
                    new_flow = {}
                else:
                    new_flow = {}
                    # Get current flow type
                    flow_type = flow_data.get("flow_type", current_flow.get("flow_type"))
                    if not flow_type:
                        raise StateException("flow_type is required")

                    # Get step info
                    step = flow_data.get("step")
                    current_step = flow_data.get("current_step")

                    # If step or current_step changes, clean old data
                    if (step is not None and step != current_flow.get("step")) or \
                       (current_step is not None and current_step != current_flow.get("current_step")):
                        # New step - only keep required previous data
                        new_flow["flow_type"] = flow_type
                        new_flow["step"] = step if step is not None else current_flow.get("step", 0)
                        new_flow["current_step"] = current_step if current_step is not None else current_flow.get("current_step", "")

                        # Clean data based on step requirements
                        if current_step in StateValidator.STEP_DATA_FIELDS:
                            required_fields = StateValidator.STEP_DATA_FIELDS[current_step]
                            old_data = current_flow.get("data", {})
                            new_data = {}
                            # Keep only required fields from previous step
                            for field in required_fields:
                                if field in old_data:
                                    new_data[field] = old_data[field]
                            new_flow["data"] = new_data
                    else:
                        # Same step - preserve current flow state
                        new_flow["flow_type"] = flow_type
                        new_flow["step"] = current_flow.get("step", 0)
                        new_flow["current_step"] = current_flow.get("current_step", "")
                        if current_flow.get("data"):
                            new_flow["data"] = current_flow["data"]

                    # Update with new data if provided
                    if "data" in flow_data:
                        if not isinstance(flow_data["data"], dict):
                            raise StateException("flow_data.data must be a dictionary")
                        new_flow["data"] = {
                            **(new_flow.get("data", {})),
                            **flow_data["data"]
                        }

                # Validate flow data structure
                validation = StateValidator._validate_flow_data(new_flow, self._state)
                if not validation.is_valid:
                    raise StateException(f"Invalid flow data: {validation.error_message}")

                # Update atomically
                return _update_state_core(self, {"flow_data": new_flow})

            # Create merged state for direct updates
            merged_state = self._state.copy()
            for key, value in updates.items():
                if isinstance(value, dict) and isinstance(merged_state.get(key), dict):
                    merged_state[key] = {**merged_state[key], **value}
                else:
                    merged_state[key] = value

            # Validate complete state
            validation = StateValidator.validate_state(merged_state)
            if not validation.is_valid:
                raise StateException(f"Invalid state after update: {validation.error_message}")

            # Update atomically
            return _update_state_core(self, updates)

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

            return self._state.get(key)

        except StateException as e:
            logger.error(f"State access error: {str(e)}")
            raise

    def get_flow_data(self) -> Dict[str, Any]:
        """Get flow data with validation"""
        flow_data = self.get("flow_data")
        if not flow_data:
            return {}
        return flow_data

    def get_flow_type(self) -> Optional[str]:
        """Get current flow type"""
        flow_data = self.get_flow_data()
        return flow_data.get("flow_type")

    def get_current_step(self) -> Optional[str]:
        """Get current flow step"""
        flow_data = self.get_flow_data()
        return flow_data.get("current_step")

    def get_flow_step_data(self) -> Dict[str, Any]:
        """Get flow step data"""
        flow_data = self.get_flow_data()
        return flow_data.get("data", {})

    def get_channel_id(self) -> str:
        """Get channel identifier enforcing SINGLE SOURCE OF TRUTH"""
        channel = self.get("channel")
        if not channel or not channel.get("identifier"):
            raise StateException("Channel identifier not found")
        return channel["identifier"]

    def get_member_id(self) -> Optional[str]:
        """Get member ID enforcing SINGLE SOURCE OF TRUTH"""
        return self.get("member_id")

    def get_active_account(self) -> Optional[Dict[str, Any]]:
        """Get active account enforcing SINGLE SOURCE OF TRUTH"""
        accounts = self.get("accounts")
        active_id = self.get("active_account_id")
        if not accounts or not active_id:
            return None
        return next(
            (account for account in accounts if account["accountID"] == active_id),
            None
        )
