import logging
from typing import Any, Dict, List

from core.transactions import (Transaction, TransactionError, TransactionOffer,
                               TransactionType)
from services.state.service import StateStage

from ...base_handler import BaseActionHandler
from ...screens import (CONFIRM_OFFER_CREDEX, OFFER_SUCCESSFUL)
from ...types import WhatsAppMessage

logger = logging.getLogger(__name__)


class MessageHandlerMixin(BaseActionHandler):
    """Mixin for handling interactive messages and formatting responses"""

    def _handle_interactive_message(
        self,
        current_state: Dict[str, Any],
        selected_profile: Dict[str, Any]
    ) -> WhatsAppMessage:
        """Handle interactive message responses"""
        try:
            logger.debug(f"Handling interactive message type: {self.service.message_type}")
            logger.debug(f"Interactive type: {self.service.message.get('interactive', {}).get('type')}")

            if self.service.message_type == "nfm_reply":
                logger.debug("Processing form submission")
                return self._handle_form_submission(current_state, selected_profile)

            button_id = self.service.message["interactive"]["button_reply"].get("id")
            if button_id == "confirm_offer":
                return self._handle_offer_confirmation(current_state, selected_profile)
            elif button_id == "cancel_offer":
                return self._handle_offer_cancellation(current_state)
            return self._format_error_response("Invalid button response. Please try again.")
        except Exception as e:
            logger.error(f"Error handling interactive message: {str(e)}")
            return self._format_error_response(str(e))

    def _handle_offer_cancellation(self, current_state: Dict[str, Any]) -> WhatsAppMessage:
        """Handle offer cancellation with proper state cleanup"""
        try:
            # Clear offer-related state
            current_state.pop("offer_flow", None)
            current_state.pop("form_shown", None)
            current_state.pop("confirmation_shown", None)
            current_state.pop("selected_denomination", None)

            # Update state to return to menu
            # Preserve JWT token
            if self.service.credex_service.jwt_token:
                current_state["jwt_token"] = self.service.credex_service.jwt_token
            self.service.state.update_state(
                user_id=self.service.user.mobile_number,
                new_state=current_state,
                stage=StateStage.MENU.value,
                update_from="offer_cancel",
                option="handle_action_menu"
            )
            return self.get_response_template("Offer cancelled. Returning to menu.")
        except Exception as e:
            logger.error(f"Error cancelling offer: {str(e)}")
            return self._format_error_response(str(e))

    def _handle_offer_confirmation(
        self, current_state: Dict[str, Any], selected_profile: Dict[str, Any]
    ) -> WhatsAppMessage:
        """Handle offer confirmation with proper state management"""
        try:
            transaction_id = current_state.get("confirm_offer_payload", {}).get("id")
            if not transaction_id:
                return self._format_error_response("No transaction to confirm")

            # Ensure JWT token is set
            if current_state.get("jwt_token"):
                self.service.credex_service.jwt_token = current_state["jwt_token"]

            issuer_account_id = (
                self.service.message["message"]["source_account"]
                if self.service.message["type"] == "nfm_reply"
                else selected_profile.get("accountID")
            )

            result = self.transaction_service.confirm_offer(
                transaction_id=transaction_id,
                issuer_account_id=issuer_account_id
            )

            if not result.success:
                return self._format_error_response(result.error_message)

            # Clear offer flow state and update state
            current_state.pop("offer_flow", None)
            current_state.pop("selected_denomination", None)
            current_state["last_transaction"] = result.transaction.to_dict()
            # Preserve JWT token
            if self.service.credex_service.jwt_token:
                current_state["jwt_token"] = self.service.credex_service.jwt_token
            self.service.state.update_state(
                user_id=self.service.user.mobile_number,
                new_state=current_state,
                stage=StateStage.MENU.value,
                update_from="offer_confirm",
                option="handle_action_menu"
            )

            return self._format_success_response(result.transaction, selected_profile)
        except TransactionError as e:
            logger.error(f"Error confirming offer: {str(e)}")
            return self._format_error_response(str(e))

    def _format_confirmation_message(
        self,
        offer: TransactionOffer,
        current_state: Dict[str, Any],
        accounts: List[Dict[str, str]],
    ) -> WhatsAppMessage:
        """Format confirmation message for credex offer"""
        try:
            # Get account name from current_state
            account_name = current_state.get("current_account", {}).get("data", {}).get("accountName")

            return {
                "messaging_product": "whatsapp",
                "to": self.service.user.mobile_number,
                "recipient_type": "individual",
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {
                        "text": CONFIRM_OFFER_CREDEX.format(
                            party=offer.metadata.get("full_name"),
                            amount=offer.amount,
                            denomination=offer.denomination,
                            source=account_name,
                            secured="*secured*" if offer.type == TransactionType.SECURED_CREDEX else "*unsecured*"
                        )
                    },
                    "action": {
                        "buttons": [
                            {
                                "type": "reply",
                                "reply": {
                                    "id": "confirm_offer",
                                    "title": "✅ Confirm"
                                }
                            },
                            {
                                "type": "reply",
                                "reply": {
                                    "id": "cancel_offer",
                                    "title": "❌ Cancel"
                                }
                            }
                        ]
                    }
                }
            }
        except Exception as e:
            logger.error(f"Error formatting confirmation message: {str(e)}")
            return self._format_error_response(str(e))

    def _format_success_response(
        self, transaction: Transaction, selected_profile: Dict[str, Any]
    ) -> WhatsAppMessage:
        """Format success response for credex offer"""
        try:
            return self.get_response_template(
                OFFER_SUCCESSFUL.format(
                    type="Secured Credex" if transaction.offer.type == TransactionType.SECURED_CREDEX
                    else "Unsecured Credex",
                    amount=transaction.offer.amount,
                    denomination=transaction.offer.denomination,
                    recipient=transaction.metadata.get("receiverAccountName"),
                    source=selected_profile["data"]["accountName"],
                    secured="*Secured* credex" if transaction.offer.type == TransactionType.SECURED_CREDEX
                    else "*Unsecured* credex",
                )
            )
        except Exception as e:
            logger.error(f"Error formatting success response: {str(e)}")
            return self._format_error_response(str(e))

    def _format_error_response(self, message: str) -> WhatsAppMessage:
        """Format error response with proper error handling"""
        try:
            # Log the original error message for debugging
            logger.debug(f"Formatting error message: {message}")

            # Clean up the error message
            error_message = message.replace("Error:", "").strip()
            if "API error" in error_message:
                # Extract the actual error message from the API response
                error_message = error_message.split("API error")[-1].strip()
                if error_message.startswith(":"):
                    error_message = error_message[1:].strip()

            # Format for better readability
            error_message = self.format_synopsis(error_message)

            logger.debug(f"Formatted error message: {error_message}")
        except Exception as e:
            logger.error(f"Error formatting error message: {str(e)}")
            error_message = "An error occurred. Please try again."

        return self.get_response_template(error_message)
