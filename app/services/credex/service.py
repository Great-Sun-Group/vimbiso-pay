from typing import Any, Dict, List, Optional, Tuple

from .auth import CredExAuthService
from .config import CredExConfig
from .interface import CredExServiceInterface
from .member import CredExMemberService
from .offers import CredExOffersService


class CredExService(CredExServiceInterface):
    """Main CredEx service that combines all operations"""

    def __init__(self, config: Optional[CredExConfig] = None):
        """Initialize the CredEx service with all sub-services"""
        self.config = config or CredExConfig.from_env()
        self._auth = CredExAuthService(config=self.config)
        self._member = CredExMemberService(config=self.config)
        self._offers = CredExOffersService(config=self.config)

    def login(self, phone: str) -> Tuple[bool, str]:
        """Authenticate user with the CredEx API"""
        return self._auth.login(phone)

    def register_member(self, member_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Register a new member"""
        return self._auth.register_member(member_data)

    def get_dashboard(self, phone: str) -> Tuple[bool, Dict[str, Any]]:
        """Fetch member's dashboard information"""
        return self._member.get_dashboard(phone)

    def validate_handle(self, handle: str) -> Tuple[bool, Dict[str, Any]]:
        """Validate a CredEx handle"""
        return self._member.validate_handle(handle)

    def offer_credex(self, offer_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Create a new CredEx offer"""
        return self._offers.offer_credex(offer_data)

    def accept_credex(self, offer_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Accept a CredEx offer"""
        return self._offers.accept_credex(offer_id)

    def accept_bulk_credex(self, offer_ids: List[str]) -> Tuple[bool, Dict[str, Any]]:
        """Accept multiple CredEx offers"""
        return self._offers.accept_bulk_credex(offer_ids)

    def decline_credex(self, offer_id: str) -> Tuple[bool, str]:
        """Decline a CredEx offer"""
        return self._offers.decline_credex(offer_id)

    def cancel_credex(self, offer_id: str) -> Tuple[bool, str]:
        """Cancel a CredEx offer"""
        return self._offers.cancel_credex(offer_id)

    def get_credex(self, offer_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Get details of a specific CredEx offer"""
        return self._offers.get_credex(offer_id)

    def get_ledger(self, member_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Get member's ledger information"""
        return self._offers.get_ledger(member_id)

    def refresh_member_info(
        self, phone: str, reset: bool = True, silent: bool = True, init: bool = False
    ) -> Optional[str]:
        """Refresh member information"""
        return self._member.refresh_member_info(phone, reset, silent, init)

    @property
    def jwt_token(self) -> Optional[str]:
        """Get the current JWT token"""
        return self._auth.jwt_token

    @jwt_token.setter
    def jwt_token(self, value: str):
        """Set the JWT token across all services"""
        self._auth.jwt_token = value
        self._member.jwt_token = value
        self._offers.jwt_token = value
