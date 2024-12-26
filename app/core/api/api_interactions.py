import logging
from typing import Optional, Tuple, Dict, Any
from django.core.cache import cache
from services.whatsapp.types import BotServiceInterface

from .auth_client import AuthClient
from .dashboard_client import DashboardClient
from .credex_client import CredexClient
from ..config.constants import CachedUser
from ..utils.utils import CredexWhatsappService

logger = logging.getLogger(__name__)


class APIInteractions:
    """Main class for handling API interactions, delegating to specialized clients"""

    def __init__(self, bot_service: BotServiceInterface):
        self.bot_service = bot_service
        self.auth_client = AuthClient()
        self.dashboard_client = DashboardClient()
        self.credex_client = CredexClient()

    def refresh_dashboard(self) -> Optional[Dict[str, Any]]:
        """Refreshes the member's dashboard"""
        logger.info("Refreshing dashboard")
        success, data = self.get_dashboard()
        if success:
            user = CachedUser(self.bot_service.user.channel_identifier)
            current_state = user.state.get_state(user)

            if not isinstance(current_state, dict):
                current_state = current_state.state
            return self.dashboard_client.process_dashboard_response(current_state, data)
        return None

    def refresh_member_info(self, reset: bool = True, silent: bool = True, init: bool = False) -> Optional[Dict[str, Any]]:
        """Refreshes member info by making an API call to CredEx"""
        logger.info("Refreshing member info")

        user = CachedUser(self.bot_service.user.channel_identifier)
        current_state = user.state.get_state(user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        self._handle_reset_and_init(reset, silent, init)

        try:
            success, data = self.get_dashboard()
            if not success:
                error_msg = data.get("message", "")
                if any(msg in error_msg for msg in [
                    "Member not found",
                    "Could not retrieve member dashboard",
                    "Invalid token"
                ]):
                    return self.bot_service.action_handler.handle_action_register(register=True)
                return None

            return self.dashboard_client.process_dashboard_response(current_state, data)

        except Exception as e:
            logger.exception(f"Error during refresh: {str(e)}")
            return None

    def login(self) -> Tuple[bool, str]:
        """Sends a login request to the CredEx API"""
        return self.auth_client.login(self.bot_service.user.channel_identifier)

    def register_member(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Sends a registration request to the CredEx API"""
        return self.auth_client.register_member(payload, self.bot_service.user.state.jwt_token)

    def get_dashboard(self) -> Tuple[bool, Dict[str, Any]]:
        """Fetches the member's dashboard from the CredEx API"""
        return self.dashboard_client.get_dashboard(
            self.bot_service.user.mobile_number,
            self.bot_service.user.state.jwt_token
        )

    def validate_handle(self, handle: str) -> Tuple[bool, Dict[str, Any]]:
        """Validates a handle by making an API call to CredEx"""
        return self.dashboard_client.validate_handle(handle, self.bot_service.user.state.jwt_token)

    def offer_credex(self, payload: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Sends an offer to the CredEx API"""
        return self.credex_client.offer_credex(payload, self.bot_service.user.state.jwt_token)

    def accept_bulk_credex(self, payload: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Accepts multiple CredEx offers"""
        return self.credex_client.accept_bulk_credex(payload, self.bot_service.user.state.jwt_token)

    def accept_credex(self, payload: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Accepts a CredEx offer"""
        return self.credex_client.accept_credex(payload, self.bot_service.user.state.jwt_token)

    def decline_credex(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Declines a CredEx offer"""
        return self.credex_client.decline_credex(payload, self.bot_service.user.state.jwt_token)

    def cancel_credex(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Cancels a CredEx offer"""
        return self.credex_client.cancel_credex(payload, self.bot_service.user.state.jwt_token)

    def get_credex(self, payload: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Fetches a specific CredEx offer"""
        return self.credex_client.get_credex(payload, self.bot_service.user.state.jwt_token)

    def get_ledger(self, payload: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Fetches ledger information"""
        return self.dashboard_client.get_ledger(payload, self.bot_service.user.state.jwt_token)

    def _handle_reset_and_init(self, reset: bool, silent: bool, init: bool) -> None:
        """Handles reset and initialization logic"""
        if reset and not silent or init:
            self._send_delay_message()
            self._send_first_message()

    def _send_delay_message(self) -> None:
        """Sends a delay message to the user"""
        if (
            self.bot_service.state.stage != "handle_action_register"
            and not cache.get(f"{self.bot_service.user.mobile_number}_interracted")
        ):
            CredexWhatsappService(
                payload={
                    "messaging_product": "whatsapp",
                    "preview_url": False,
                    "recipient_type": "individual",
                    "to": self.bot_service.user.mobile_number,
                    "type": "text",
                    "text": {"body": "Please wait while we process your request..."},
                }
            ).send_message()
            cache.set(f"{self.bot_service.user.mobile_number}_interracted", True, 60 * 15)

    def _send_first_message(self) -> None:
        """Sends the first message to the user"""
        first_message = "Welcome to CredEx! How can I assist you today?"
        CredexWhatsappService(
            payload={
                "messaging_product": "whatsapp",
                "preview_url": False,
                "recipient_type": "individual",
                "to": self.bot_service.user.mobile_number,
                "type": "text",
                "text": {"body": first_message},
            }
        ).send_message()
