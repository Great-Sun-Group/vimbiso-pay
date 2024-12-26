"""Core state management functionality"""
import logging
from typing import Any, Dict, Optional

from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator
from services.credex.service import CredExService

from .config import ACTIVITY_TTL, atomic_state
from .state_utils import (create_initial_state, prepare_state_update,
                          update_critical_fields)

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class StateManager:
    """Manages atomic state operations"""
    def __init__(self, key_prefix: str):
        self.key_prefix = key_prefix
        self.state = None
        self.jwt_token = None
        self._initialize_state()
        self._credex_service = None

    def _initialize_state(self) -> None:
        """Initialize state with atomic operations"""
        # Log initialization start
        logger.debug(f"Initializing state for key prefix: {self.key_prefix}")

        # Get existing state
        state_data, error = atomic_state.atomic_get(self.key_prefix)
        if error:
            logger.error(f"Error getting state: {error}")

        # Create initial state if none exists
        if not state_data:
            state_data = create_initial_state()
            logger.debug("Created initial state")

        # Extract channel ID from key prefix
        channel_id = None
        if self.key_prefix.startswith("channel:"):
            channel_id = self.key_prefix.split(":", 1)[1]
            logger.debug(f"Extracted channel ID from key prefix: {channel_id}")

        # Ensure channel info is present and valid
        if not state_data.get("channel") or not isinstance(state_data["channel"], dict):
            state_data["channel"] = {
                "type": "whatsapp",
                "identifier": channel_id,
                "metadata": {}
            }
            logger.debug("Added missing channel info to state")
        elif channel_id and state_data["channel"].get("identifier") != channel_id:
            state_data["channel"]["identifier"] = channel_id
            logger.debug("Updated channel identifier in state")

        # Validate state
        validation = StateValidator.validate_state(state_data)
        if not validation.is_valid:
            logger.warning(f"State validation failed: {validation.error_message}")
            last_valid = audit.get_last_valid_state("user_state")
            if last_valid:
                logger.debug("Using last valid state")
                state_data = last_valid
            else:
                logger.debug("Creating new initial state")
                state_data = create_initial_state()

            # Ensure channel info is present in fallback state
            if channel_id:
                state_data["channel"] = {
                    "type": "whatsapp",
                    "identifier": channel_id,
                    "metadata": {}
                }
                logger.debug("Added channel info to fallback state")

        # Set state and token
        self.state = state_data
        self.jwt_token = state_data.get("jwt_token")
        logger.debug(f"State initialized with JWT token: {bool(self.jwt_token)}")

        # Update state in Redis
        success, error = atomic_state.atomic_update(self.key_prefix, state_data, ACTIVITY_TTL)
        if not success:
            logger.error(f"Failed to update state in Redis: {error}")
        else:
            logger.debug("State successfully updated in Redis")

    def update_state(self, updates: Dict[str, Any], operation: Optional[str] = None) -> None:
        """Update state with new values"""
        try:
            new_state = update_critical_fields(self.state.copy(), updates)
            new_state = prepare_state_update(new_state, updates)

            if atomic_state.atomic_update(self.key_prefix, new_state, ACTIVITY_TTL)[0]:
                self.state = new_state
                self.jwt_token = new_state.get("jwt_token")
                if self._credex_service:
                    self._update_service_token(self.jwt_token)
                if operation:
                    logger.debug(f"State updated for operation: {operation}")
        except Exception:
            logger.exception("State update error")

    def get_or_create_credex_service(self) -> CredExService:
        """Get or create CredEx service instance"""
        if not self._credex_service:
            # Create service with state dictionary
            self._credex_service = CredExService(user={"state": self.state})

            # Log service creation
            logger.debug("Creating new CredEx service:")
            logger.debug(f"- Has user: {bool(self._credex_service.user)}")
            logger.debug(f"- User state: {bool(self._credex_service.user['state'])}")

            # Set token if available
            if self.jwt_token:
                self._update_service_token(self.jwt_token)
                logger.debug(f"- Token set: {bool(self._credex_service._jwt_token)}")

        return self._credex_service

    def set_jwt_token(self, jwt_token: str) -> None:
        """Set JWT token and update state"""
        self.jwt_token = jwt_token
        if self.state:
            self.update_state({"jwt_token": jwt_token})

    def _update_service_token(self, jwt_token: str) -> None:
        """Update service token"""
        if not self._credex_service:
            return
        self._credex_service._jwt_token = jwt_token
        for service in ['_auth', '_member', '_offers', '_recurring']:
            if hasattr(self._credex_service, service):
                setattr(getattr(self._credex_service, service), '_jwt_token', jwt_token)

    def cleanup(self, preserve_fields: set = None) -> bool:
        """Clean up state preserving specified fields"""
        preserve_fields = preserve_fields or {"jwt_token", "member_id", "account_id"}
        success, _ = atomic_state.atomic_cleanup(self.key_prefix, preserve_fields)
        if success:
            self._initialize_state()
        return success
