"""User representation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional

from core.utils.state_validator import StateValidator
from .state_manager import StateManager

logger = logging.getLogger(__name__)


class CachedUser:
    """User representation with strict state management"""
    def __init__(self, channel_identifier: str) -> None:
        """Initialize with channel identifier"""
        logger.debug("Initializing CachedUser:")
        logger.debug(f"- Channel ID: {channel_identifier}")

        # Initialize state manager
        self._state_manager = StateManager(f"channel:{channel_identifier}")

        # Validate state at boundary
        validation = StateValidator.validate_state(self._state_manager._state)
        if not validation.is_valid:
            logger.error(f"Invalid state: {validation.error_message}")
            raise ValueError(f"Invalid state: {validation.error_message}")

        logger.debug("CachedUser initialization complete")

    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update state while maintaining SINGLE SOURCE OF TRUTH"""
        # Validate updates at boundary
        validation = StateValidator.validate_state(updates)
        if not validation.is_valid:
            raise ValueError(f"Invalid state update: {validation.error_message}")

        # Update through state manager
        success, error = self._state_manager.update_state(updates)
        if not success:
            raise ValueError(f"Failed to update state: {error}")

    @property
    def member_id(self) -> Optional[str]:
        """Get member ID from state"""
        # Validate at boundary
        validation = StateValidator.validate_before_access(
            {"member_id": self._state_manager.get("member_id")},
            {"member_id"}
        )
        if not validation.is_valid:
            raise ValueError(f"Invalid state access: {validation.error_message}")
        return self._state_manager.get("member_id")

    @member_id.setter
    def member_id(self, value: str) -> None:
        """Set member ID through state update"""
        self.update_state({"member_id": value})

    @property
    def channel_identifier(self) -> Optional[str]:
        """Get channel identifier from state"""
        # Validate at boundary
        validation = StateValidator.validate_before_access(
            {"channel": self._state_manager.get("channel")},
            {"channel"}
        )
        if not validation.is_valid:
            raise ValueError(f"Invalid state access: {validation.error_message}")
        channel = self._state_manager.get("channel")
        return channel.get("identifier") if channel else None

    @channel_identifier.setter
    def channel_identifier(self, value: str) -> None:
        """Set channel identifier through state update"""
        self.update_state({
            "channel": {
                "type": "whatsapp",
                "identifier": value,
                "metadata": {}
            }
        })

    @property
    def jwt_token(self) -> Optional[str]:
        """Get JWT token from state"""
        # Validate at boundary
        validation = StateValidator.validate_before_access(
            {"jwt_token": self._state_manager.get("jwt_token")},
            {"jwt_token"}
        )
        if not validation.is_valid:
            raise ValueError(f"Invalid state access: {validation.error_message}")
        return self._state_manager.get("jwt_token")

    @jwt_token.setter
    def jwt_token(self, value: str) -> None:
        """Set JWT token through state update"""
        self.update_state({"jwt_token": value})

    def get_or_create_credex_service(self) -> Any:
        """Get or create CredEx service instance"""
        return self._state_manager.get_or_create_credex_service()
