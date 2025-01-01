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

            # Create minimal initial state with only required fields
            initial_state = {
                "channel": {
                    "type": "whatsapp",
                    "identifier": channel_id
                }
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

                # Start with current flow state
                new_flow = current_flow.copy()

                # Handle empty flow_data
                if not flow_data:
                    new_flow = {}
                else:
                    # Update flow type if provided
                    if "flow_type" in flow_data:
                        new_flow["flow_type"] = flow_data["flow_type"]
                    elif not new_flow.get("flow_type"):
                        raise StateException("flow_type is required")

                    # Update step info if provided
                    if "step" in flow_data:
                        new_flow["step"] = flow_data["step"]
                    if "current_step" in flow_data:
                        new_flow["current_step"] = flow_data["current_step"]

                    # Update data if provided
                    if "data" in flow_data:
                        if not isinstance(flow_data["data"], dict):
                            raise StateException("flow_data.data must be a dictionary")
                        # Merge new data with existing
                        new_flow["data"] = {
                            **(new_flow.get("data", {})),
                            **flow_data["data"]
                        }

                    # Clean data based on step requirements if step changed
                    if ("step" in flow_data or "current_step" in flow_data) and \
                       new_flow.get("current_step") in StateValidator.STEP_DATA_FIELDS:
                        required_fields = StateValidator.STEP_DATA_FIELDS[new_flow["current_step"]]
                        old_data = new_flow.get("data", {})
                        clean_data = {}
                        # Keep only required fields
                        for field in required_fields:
                            if field in old_data:
                                clean_data[field] = old_data[field]
                        new_flow["data"] = clean_data

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

            # Only validate access for required fields
            if key in StateValidator.CRITICAL_FIELDS:
                validation = StateValidator.validate_before_access(self._state, {key})
                if not validation.is_valid:
                    raise StateException(f"Invalid state access: {validation.error_message}")

            # Return None for missing optional fields
            return self._state.get(key)

        except StateException as e:
            logger.error(f"State access error: {str(e)}")
            raise

    def get_flow_state(self) -> Dict[str, Any]:
        """Get validated flow state"""
        flow_data = self.get("flow_data")
        if not flow_data:
            return {}

        # Validate flow state
        validation = StateValidator._validate_flow_data(flow_data, self._state)
        if not validation.is_valid:
            raise StateException(f"Invalid flow state: {validation.error_message}")

        return flow_data

    def get_flow_type(self) -> Optional[str]:
        """Get current flow type"""
        flow_state = self.get_flow_state()
        return flow_state.get("flow_type")

    def get_current_step(self) -> Optional[str]:
        """Get current flow step"""
        flow_state = self.get_flow_state()
        return flow_state.get("current_step")

    def get_flow_step_data(self) -> Dict[str, Any]:
        """Get validated flow step data"""
        flow_state = self.get_flow_state()
        return flow_state.get("data", {})

    def get_channel_data(self) -> Dict[str, Any]:
        """Get validated channel data"""
        channel = self.get("channel")
        if not channel:
            raise StateException("Channel data not found")

        # Validate channel data
        validation = StateValidator._validate_channel_data(channel)
        if not validation.is_valid:
            raise StateException(f"Invalid channel data: {validation.error_message}")

        return channel

    def get_amount_data(self) -> Dict[str, Any]:
        """Get validated amount data"""
        flow_data = self.get_flow_step_data()
        amount_data = flow_data.get("amount")
        if not amount_data:
            raise StateException("Amount data not found")

        # Validate amount data
        validation = StateValidator._validate_amount_data(amount_data)
        if not validation.is_valid:
            raise StateException(f"Invalid amount data: {validation.error_message}")

        return amount_data

    def get_handle_data(self) -> Dict[str, Any]:
        """Get validated handle data"""
        flow_data = self.get_flow_step_data()
        handle_data = flow_data.get("handle")
        if not handle_data:
            raise StateException("Handle data not found")

        # Validate handle data
        validation = StateValidator._validate_handle_data(handle_data)
        if not validation.is_valid:
            raise StateException(f"Invalid handle data: {validation.error_message}")

        return handle_data

    def get_confirmation_data(self) -> Dict[str, Any]:
        """Get validated confirmation data"""
        flow_data = self.get_flow_step_data()
        confirmation_data = flow_data.get("confirmation")
        if not confirmation_data:
            raise StateException("Confirmation data not found")

        # Validate confirmation data
        validation = StateValidator._validate_confirmation_data(confirmation_data)
        if not validation.is_valid:
            raise StateException(f"Invalid confirmation data: {validation.error_message}")

        return confirmation_data

    def get_offer_id(self) -> str:
        """Get validated offer ID"""
        flow_data = self.get_flow_step_data()
        offer_id = flow_data.get("offer_id")
        if not offer_id:
            raise StateException("Offer ID not found")

        # Validate offer ID
        validation = StateValidator._validate_offer_id(offer_id)
        if not validation.is_valid:
            raise StateException(f"Invalid offer ID: {validation.error_message}")

        return offer_id

    def get_auth_data(self) -> Dict[str, Any]:
        """Get validated auth data"""
        auth_data = {
            "token": self.get("jwt_token"),
            "authenticated": self.get("authenticated")
        }

        # Validate auth data
        validation = StateValidator._validate_auth_data(auth_data)
        if not validation.is_valid:
            raise StateException(f"Invalid auth data: {validation.error_message}")

        return auth_data

    def get_service_data(self) -> Dict[str, Any]:
        """Get validated service data"""
        flow_data = self.get_flow_step_data()
        service_data = flow_data.get("service")
        if not service_data:
            raise StateException("Service data not found")

        # Validate service data
        validation = StateValidator._validate_service_data(service_data)
        if not validation.is_valid:
            raise StateException(f"Invalid service data: {validation.error_message}")

        return service_data

    def get_step_data(self) -> Dict[str, Any]:
        """Get validated step data"""
        flow_data = self.get_flow_step_data()
        step_data = flow_data.get("step")
        if not step_data:
            raise StateException("Step data not found")

        # Validate step data
        validation = StateValidator._validate_step_data(step_data)
        if not validation.is_valid:
            raise StateException(f"Invalid step data: {validation.error_message}")

        return step_data

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
