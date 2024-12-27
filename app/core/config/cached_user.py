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

        # Validate and initialize state
        validation = StateValidator.validate_state(self._state_manager.get_state())
        if not validation.is_valid:
            logger.debug("Initializing empty state")
            self._state_manager.update_state({
                "member_id": None,
                "channel": {
                    "type": "whatsapp",
                    "identifier": channel_identifier,
                    "metadata": {}
                },
                "jwt_token": None
            })

        logger.debug("CachedUser initialization complete")

    def _validate_state_access(self, field: str) -> None:
        """Validate state before accessing a field"""
        validation = StateValidator.validate_before_access(
            self._state_manager.get_state(),
            {field}
        )
        if not validation.is_valid:
            raise ValueError(f"Invalid state access: {validation.error_message}")

    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update state while maintaining SINGLE SOURCE OF TRUTH"""
        # Validate updates
        new_state = {**self._state_manager.get_state(), **updates}
        validation = StateValidator.validate_state(new_state)
        if not validation.is_valid:
            raise ValueError(f"Invalid state update: {validation.error_message}")

        self._state_manager.update_state(updates)

    @property
    def member_id(self) -> Optional[str]:
        """Get member ID from state"""
        self._validate_state_access("member_id")
        return self._state_manager.get("member_id")

    @member_id.setter
    def member_id(self, value: str) -> None:
        """Set member ID through state update"""
        self.update_state({"member_id": value})

    @property
    def channel_identifier(self) -> Optional[str]:
        """Get channel identifier from state"""
        self._validate_state_access("channel")
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
        self._validate_state_access("jwt_token")
        return self._state_manager.get("jwt_token")

    @jwt_token.setter
    def jwt_token(self, value: str) -> None:
        """Set JWT token through state update"""
        self.update_state({"jwt_token": value})

    def get_or_create_credex_service(self) -> Any:
        """Get or create CredEx service instance"""
        return self._state_manager.get_or_create_credex_service()
