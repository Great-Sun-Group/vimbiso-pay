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
        self._jwt_token = None

        # Log initialization
        logger.debug("Initializing CachedUser:")
        logger.debug(f"- Channel ID: {channel_identifier}")
        logger.debug(f"- Member ID: {member_id}")

        # Initialize state through property
        current_state = self.state.state or {}

        # Ensure channel info is set in state
        if not current_state.get("channel", {}).get("identifier"):
            logger.debug("Setting initial channel info")
            self.state.update_state({
                "channel": {
                    "type": "whatsapp",
                    "identifier": channel_identifier,
                    "metadata": {}
                }
            })

        # Set initial JWT token through property
        self._jwt_token = self.state.jwt_token
        logger.debug(f"Initial JWT token set: {bool(self._jwt_token)}")

        # Log final state
        logger.debug("CachedUser initialization complete:")
        logger.debug(f"- Final state: {self.state.state}")
        logger.debug(f"- Has JWT token: {bool(self._jwt_token)}")

    @property
    def state(self):
        """Access state consistently"""
        if not hasattr(self, '_state_manager'):
            # Initialize state manager if not exists
            self._state_manager = StateManager(
                str(self._member_id) if self._member_id else f"channel:{self._channel_identifier}"
            )
        return self._state_manager

    @property
    def member_id(self) -> Optional[str]:
        """Get member ID from state if not set directly"""
        if self._member_id:
            return self._member_id
        return self.state.state.get("member_id")

    @member_id.setter
    def member_id(self, value: str) -> None:
        """Set member ID and update state"""
        self._member_id = value
        self.state.update_state({"member_id": value})

    @property
    def channel_identifier(self) -> str:
        """Get channel identifier"""
        return self._channel_identifier

    @channel_identifier.setter
    def channel_identifier(self, value: str) -> None:
        """Set channel identifier"""
        self._channel_identifier = value
        # Update state if it exists
        if hasattr(self, '_state_manager'):
            current_state = self.state.state or {}
            if not current_state.get("channel", {}).get("identifier"):
                self.state.update_state({
                    "channel": {
                        "type": "whatsapp",
                        "identifier": value,
                        "metadata": {}
                    }
                })

    @property
    def jwt_token(self) -> Optional[str]:
        """Get JWT token from state"""
        return self.state.jwt_token

    @jwt_token.setter
    def jwt_token(self, value: str) -> None:
        """Set JWT token and update state"""
        # Update token in state
        self.state.jwt_token = value
        # Force state update to ensure token is saved
        current_state = self.state.state or {}
        self.state.update_state({
            **current_state,
            "jwt_token": value
        })

    def get_or_create_credex_service(self):
        """Get or create CredEx service instance"""
        return self.state.get_or_create_credex_service()
