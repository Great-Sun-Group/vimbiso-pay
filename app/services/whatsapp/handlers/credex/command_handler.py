import logging
from typing import Any, Dict

from core.transactions import TransactionError
from services.state.service import StateStage
from ...base_handler import BaseActionHandler
from ...types import WhatsAppMessage

logger = logging.getLogger(__name__)


class CommandHandlerMixin(BaseActionHandler):
    """Mixin for handling Credex commands"""

    def _is_credex_command(self, body: str) -> bool:
        """Check if message is a credex command"""
        return ("=>" in str(body) or "->" in str(body) or
                str(body).startswith("cancel_offer_") or
                str(body).startswith("accept_offer_") or
                str(body).startswith("decline_offer_"))

    def _handle_credex_command(
        self, current_state: Dict[str, Any], selected_profile: Dict[str, Any]
    ) -> WhatsAppMessage:
        """Handle credex command processing with proper error handling"""
        try:
            # Handle cancel offer commands
            if str(self.service.body).startswith("cancel_offer_"):
                credex_id = self.service.body.replace("cancel_offer_", "")
                logger.debug(f"Handling cancel offer command for ID: {credex_id}")
                # Use the shared cancellation logic from OfferFlowMixin
                return self._handle_offer_cancellation(current_state, credex_id)

            # Handle accept offer commands
            if str(self.service.body).startswith("accept_offer_"):
                credex_id = self.service.body.replace("accept_offer_", "")
                logger.debug(f"Handling accept offer command for ID: {credex_id}")
                return self._handle_offer_acceptance(current_state, credex_id)

            # Handle decline offer commands
            if str(self.service.body).startswith("decline_offer_"):
                credex_id = self.service.body.replace("decline_offer_", "")
                logger.debug(f"Handling decline offer command for ID: {credex_id}")
                return self._handle_offer_decline(current_state, credex_id)

            # Ensure JWT token is set
            if current_state.get("jwt_token"):
                self.service.credex_service.jwt_token = current_state["jwt_token"]

            result = self.transaction_service.process_command(
                command=self.service.body,
                member_id=current_state["profile"]["data"]["action"]["details"]["memberID"],
                account_id=selected_profile["data"]["accountID"],
                denomination=selected_profile["data"]["defaultDenom"],
            )

            if not result.success:
                return self._format_error_response(result.error_message)

            # Update state with transaction details
            current_state["transaction_details"] = result.transaction.to_dict()
            # Preserve JWT token
            if self.service.credex_service.jwt_token:
                current_state["jwt_token"] = self.service.credex_service.jwt_token
            self.service.state.update_state(
                user_id=self.service.user.mobile_number,
                new_state=current_state,
                stage=StateStage.CREDEX.value,
                update_from="command_process",
                option="handle_action_offer_credex"
            )

            return self._format_confirmation_message(
                result.transaction.offer,
                current_state,
                self.transaction_service.get_available_accounts(
                    current_state["profile"]["data"]["action"]["details"]["memberID"]
                )
            )
        except TransactionError as e:
            logger.error(f"Error processing credex command: {str(e)}")
            return self._format_error_response(str(e))
