"""User representation with cached state"""
import logging
from typing import Optional

from .state_manager import StateManager

logger = logging.getLogger(__name__)


class CachedUser:
    """User representation with cached state"""
    def __init__(self, channel_identifier: str, member_id: Optional[str] = None) -> None:
        # Basic user info
        self.first_name = "Welcome"
        self.last_name = "Visitor"
        self.role = "DEFAULT"
        self.email = "customer@credex.co.zw"
        self.registration_complete = False

        # Internal state
        self._member_id = member_id
        self._channel_identifier = channel_identifier

        # Initialize state with proper key prefix
        key_prefix = str(member_id) if member_id else f"channel:{channel_identifier}"
        self._state = StateManager(key_prefix)

        # Log initial state
        logger.debug("Initializing CachedUser:")
        logger.debug(f"- Channel ID: {channel_identifier}")
        logger.debug(f"- Member ID: {member_id}")
        logger.debug(f"- Key prefix: {key_prefix}")
        logger.debug(f"- Initial state: {self._state.state}")

        # Ensure channel info is set in state
        current_state = self._state.state or {}
        if not current_state.get("channel", {}).get("identifier"):
            logger.debug("Setting initial channel info")
            self._state.update_state({
                "channel": {
                    "type": "whatsapp",
                    "identifier": channel_identifier,
                    "metadata": {}
                }
            })

        # Set initial JWT token
        self._jwt_token = self._state.jwt_token
        logger.debug(f"Initial JWT token set: {bool(self._jwt_token)}")

        # Log final state
        logger.debug("CachedUser initialization complete:")
        logger.debug(f"- Final state: {self._state.state}")
        logger.debug(f"- Has JWT token: {bool(self._jwt_token)}")

    @property
    def state(self):
        """Access state consistently"""
        return self._state

    @property
    def member_id(self) -> Optional[str]:
        """Get member ID from state if not set directly"""
        if self._member_id:
            return self._member_id
        return self._state.state.get("member_id")

    @member_id.setter
    def member_id(self, value: str) -> None:
        """Set member ID and update state"""
        self._member_id = value
        if self._state and self._state.state:
            self._state.update_state({"member_id": value})

    @property
    def channel_identifier(self) -> str:
        """Get channel identifier"""
        return self._channel_identifier

    @property
    def jwt_token(self) -> Optional[str]:
        """Get JWT token from state"""
        return self._state.jwt_token

    @jwt_token.setter
    def jwt_token(self, value: str) -> None:
        """Set JWT token and update state"""
        if self._state:
            # Update token in state
            self._state.jwt_token = value
            # Force state update to ensure token is saved
            current_state = self._state.state or {}
            self._state.update_state({
                **current_state,
                "jwt_token": value
            })

    def get_or_create_credex_service(self):
        """Get or create CredEx service instance"""
        return self._state.get_or_create_credex_service()
