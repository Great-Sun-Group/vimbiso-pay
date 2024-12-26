"""Core state management with SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional, Tuple

from services.credex.service import CredExService
from .config import ACTIVITY_TTL, atomic_state
from .state_utils import create_initial_state, prepare_state_update, update_critical_fields

logger = logging.getLogger(__name__)


class StateManager:
    """Manages state while enforcing SINGLE SOURCE OF TRUTH"""

    def __init__(self, key_prefix: str):
        """Initialize with key prefix"""
        self.key_prefix = key_prefix
        self._credex_service = None
        self.state = self._initialize_state()

    def _initialize_state(self) -> Dict[str, Any]:
        """Initialize state with proper structure"""
        # Get existing state
        state_data, error = atomic_state.atomic_get(self.key_prefix)
        if error:
            logger.error(f"Error getting state: {error}")
            state_data = None

        # Create initial state if none exists
        if not state_data:
            state_data = create_initial_state()

        # Extract channel ID from key prefix
        if self.key_prefix.startswith("channel:"):
            channel_id = self.key_prefix.split(":", 1)[1]
            # Update channel identifier
            if not state_data.get("channel"):
                state_data["channel"] = {
                    "type": "whatsapp",
                    "identifier": None,
                    "metadata": {}
                }
            state_data["channel"]["identifier"] = channel_id

        # Store state in Redis
        atomic_state.atomic_update(self.key_prefix, state_data, ACTIVITY_TTL)
        return state_data

    def update_state(self, updates: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Update state while maintaining SINGLE SOURCE OF TRUTH"""
        try:
            # First update critical fields (member_id, channel, jwt_token)
            new_state = update_critical_fields(self.state, updates)
            # Then handle other updates
            new_state = prepare_state_update(new_state, updates)

            # Store in Redis
            success, error = atomic_state.atomic_update(
                self.key_prefix, new_state, ACTIVITY_TTL
            )
            if success:
                self.state = new_state
                # Update service token if needed
                if self._credex_service and new_state.get("jwt_token"):
                    self._update_service_token(new_state["jwt_token"])
            return success, error

        except Exception as e:
            logger.error(f"State update error: {str(e)}")
            return False, str(e)

    def get_state(self) -> Dict[str, Any]:
        """Get current state"""
        return self.state.copy()

    @property
    def jwt_token(self) -> Optional[str]:
        """Get JWT token from state (SINGLE SOURCE OF TRUTH)"""
        return self.state.get("jwt_token")

    def get_or_create_credex_service(self) -> CredExService:
        """Get or create CredEx service instance"""
        if not self._credex_service:
            self._credex_service = CredExService(state_manager=self)
            if self.jwt_token:
                self._update_service_token(self.jwt_token)
        return self._credex_service

    def _update_service_token(self, jwt_token: str) -> None:
        """Update service token"""
        if not self._credex_service:
            return
        # Update token in all services
        for service in self._credex_service.services.values():
            service._jwt_token = jwt_token
