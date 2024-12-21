"""Main API client"""
import logging
from typing import Dict, Any, Tuple, Optional

from services.whatsapp.types import BotServiceInterface
from .auth import AuthManager
from .credex import CredExManager
from .dashboard import DashboardManager
from .profile import ProfileManager

logger = logging.getLogger(__name__)


class APIClient:
    """Main API client that coordinates all API operations"""

    def __init__(self, bot_service: BotServiceInterface):
        self.bot_service = bot_service
        self.auth = AuthManager(bot_service)
        self.credex = CredExManager(bot_service)
        self.dashboard = DashboardManager(bot_service)
        self.profile = ProfileManager(bot_service)

    # Auth operations
    def login(self) -> Tuple[bool, str]:
        """Handle login flow"""
        return self.auth.login()

    def register_member(self, member_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Handle member registration"""
        return self.auth.register_member(member_data)

    # Dashboard operations
    def get_dashboard(self) -> Tuple[bool, Dict[str, Any]]:
        """Fetch member's dashboard"""
        return self.dashboard.get_dashboard()

    def refresh_member_info(
        self,
        reset: bool = True,
        silent: bool = True,
        init: bool = False
    ) -> Optional[str]:
        """Refresh member information"""
        return self.dashboard.refresh_member_info(reset, silent, init)

    def validate_handle(self, handle: str) -> Tuple[bool, Dict[str, Any]]:
        """Validate member handle"""
        return self.dashboard.validate_handle(handle)

    def get_ledger(self, payload: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Get member's transaction ledger"""
        return self.dashboard.get_ledger(payload)

    # CredEx operations
    def offer_credex(self, offer_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Create a new CredEx offer"""
        return self.credex.offer_credex(offer_data)

    def accept_credex(self, credex_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Accept a CredEx offer"""
        return self.credex.accept_credex(credex_id)

    def decline_credex(self, credex_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Decline a CredEx offer"""
        return self.credex.decline_credex(credex_id)

    def cancel_credex(self, credex_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Cancel a CredEx offer"""
        return self.credex.cancel_credex(credex_id)

    def get_credex(self, credex_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Get details of a specific CredEx"""
        return self.credex.get_credex(credex_id)

    def accept_bulk_credex(self, credex_ids: list) -> Tuple[bool, Dict[str, Any]]:
        """Accept multiple CredEx offers"""
        return self.credex.accept_bulk_credex(credex_ids)

    # Profile operations
    def update_profile_from_response(
        self,
        api_response: Dict[str, Any],
        action_type: str,
        update_from: str,
        token: Optional[str] = None
    ) -> None:
        """Update profile and state from API response"""
        self.profile.update_profile_from_response(
            api_response,
            action_type,
            update_from,
            token
        )
