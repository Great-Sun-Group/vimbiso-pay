"""User representation with cached state"""
from typing import Optional

from .state_manager import StateManager


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
        self._state = StateManager(str(member_id) if member_id else f"channel:{channel_identifier}")
        self.jwt_token = self._state.jwt_token

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

    def get_or_create_credex_service(self):
        """Get or create CredEx service instance"""
        return self._state.get_or_create_credex_service()
