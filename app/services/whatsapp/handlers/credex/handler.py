import logging

from core.transactions import create_transaction_service
from ...base_handler import BaseActionHandler
from ...types import WhatsAppMessage

from .profile import ProfileMixin
from .offer_flow import OfferFlowMixin
from .message_handler import MessageHandlerMixin
from .command_handler import CommandHandlerMixin

logger = logging.getLogger(__name__)


class CredexActionHandler(
    ProfileMixin,
    OfferFlowMixin,
    MessageHandlerMixin,
    CommandHandlerMixin,
    BaseActionHandler
):
    """Handler for Credex-related actions"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.transaction_service = create_transaction_service(
            api_client=self.service.credex_service
        )
        # Ensure JWT token is set from state
        if self.service.current_state.get("jwt_token"):
            self.service.credex_service.jwt_token = self.service.current_state["jwt_token"]

    def handle_action_offer_credex(self) -> WhatsAppMessage:
        """Handle credex offer creation with proper state management"""
        try:
            # Validate and get profile data
            profile_result = self._validate_and_get_profile()
            if isinstance(profile_result, WhatsAppMessage):
                return profile_result

            current_state, selected_profile = profile_result

            # Handle offer flow states
            if current_state.get("offer_flow"):
                return self._handle_offer_flow(current_state, selected_profile)

            # Start new offer flow
            return self._start_offer_flow(current_state)

        except Exception as e:
            logger.error(f"Error handling credex offer: {str(e)}")
            # Use _format_error_response to properly format the error message
            return self._format_error_response(str(e))
