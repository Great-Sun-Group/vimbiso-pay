"""User representation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional

from core.utils.exceptions import StateException
from .state_manager import StateManager

logger = logging.getLogger(__name__)


class CachedUser:
    """User representation with strict state management"""
    def __init__(self, channel_identifier: str) -> None:
        """Initialize with channel identifier"""
        logger.debug("Initializing CachedUser:")
        logger.debug(f"- Channel ID: {channel_identifier}")

        try:
            # Initialize state manager (validation handled internally)
            self._state_manager = StateManager(f"channel:{channel_identifier}")

            # Verify channel exists by accessing it (triggers internal validation)
            self._state_manager.get("channel")

            logger.debug("CachedUser initialization complete")

        except StateException as e:
            logger.error(f"CachedUser initialization error: {str(e)}")
            raise

    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update state while maintaining SINGLE SOURCE OF TRUTH"""
        try:
            # Update through state manager (validation handled internally)
            success, error = self._state_manager.update_state(updates)
            if not success:
                raise StateException(f"Failed to update state: {error}")

        except StateException as e:
            logger.error(f"State update error: {str(e)}")
            raise

    @property
    def member_id(self) -> Optional[str]:
        """Get member ID from state"""
        try:
            return self._state_manager.get("member_id")
        except StateException as e:
            logger.error(f"Member ID access error: {str(e)}")
            raise

    @member_id.setter
    def member_id(self, value: str) -> None:
        """Set member ID through state update"""
        self.update_state({"member_id": value})

    @property
    def channel_identifier(self) -> Optional[str]:
        """Get channel identifier from state"""
        try:
            channel = self._state_manager.get("channel")
            return channel.get("identifier") if channel else None
        except StateException as e:
            logger.error(f"Channel identifier access error: {str(e)}")
            raise

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
        try:
            return self._state_manager.get("jwt_token")
        except StateException as e:
            logger.error(f"JWT token access error: {str(e)}")
            raise

    @jwt_token.setter
    def jwt_token(self, value: str) -> None:
        """Set JWT token through state update"""
        self.update_state({"jwt_token": value})
