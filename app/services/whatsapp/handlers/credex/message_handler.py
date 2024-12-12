"""Message handler mixin for credex handlers"""
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
            logger.debug(f"Handling message type: {self.service.message_type}")
            logger.debug(f"Full message: {self.service.message}")

            # Handle button responses
            if self.service.message_type == "button":
                button_payload = self.service.message["button"].get("payload")
                logger.debug(f"Processing button payload: {button_payload}")

                # Handle offer confirmation/cancellation
                if button_payload == "confirm_offer":
                    return self._handle_offer_confirmation(current_state, selected_profile)
                elif button_payload == "cancel_offer":
                    return self._handle_offer_cancellation(current_state)

                # Handle dashboard action buttons
                elif button_payload.startswith(("accept_", "decline_", "cancel_")):
                    action, credex_id = self._parse_action_button(button_payload)
                    if action and credex_id:
                        offer_data = self._get_offer_data(credex_id, selected_profile)
                        if offer_data:
                            return self._handle_credex_action(action, credex_id, offer_data)
                    return self._format_error_response("Invalid action button. Please try again.")

                return self._format_error_response("Invalid button response. Please try again.")

            # Handle list responses
            elif self.service.message_type == "interactive":
                interactive_type = self.service.message.get("interactive", {}).get("type")
                if interactive_type == "list_reply":
                    selected_id = self.service.message["interactive"]["list_reply"].get("id")
                    logger.debug(f"Processing list selection: {selected_id}")

                    # Handle menu action selections
                    if selected_id in ["handle_action_accept_offers", "handle_action_decline_offers", "handle_action_pending_offers_out"]:
                        action = selected_id.replace("handle_action_", "").replace("_offers", "")
                        if action in ["accept", "decline", "pending_offers_out"]:
                            # Map pending_offers_out to cancel
                            action = "cancel" if action == "pending_offers_out" else action
                            # Get offers based on action type
                            offers = self._get_offers_for_action(action, selected_profile)
                            if offers:
                                return self._create_offers_list(action, offers)
                            return self.get_response_template(f"No {action} offers available.")

                    # Handle offer selection from list
                    elif selected_id:
                        action, credex_id = self._parse_action_button(selected_id)
                        if action and credex_id:
                            offer_data = self._get_offer_data(credex_id, selected_profile)
                            if offer_data:
                                return self._handle_credex_action(action, credex_id, offer_data)

                    return self._format_error_response("Invalid list selection. Please try again.")

            logger.error(f"Unhandled message type: {self.service.message_type}")
            return self._format_error_response("Invalid message type. Please try again.")
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            return self._format_error_response(str(e))

    def _get_offers_for_action(self, action: str, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get relevant offers based on action type"""
        try:
            if action in ["accept", "decline"]:
                return profile.get("data", {}).get("pendingInData", {}).get("data", [])
            elif action == "cancel":
                return profile.get("data", {}).get("pendingOutData", {}).get("data", [])
            return []
        except Exception as e:
            logger.error(f"Error getting offers for action {action}: {str(e)}")
            return []

    def _create_offers_list(self, action: str, offers: List[Dict[str, Any]]) -> WhatsAppMessage:
        """Create interactive list message for offers"""
        try:
            sections = []
            current_section = {
                "title": f"Select an Offer to {action.title()}",
                "rows": []
            }

            for offer in offers:
                # Get amount and party info
                amount_str = offer.get("formattedInitialAmount", "")
                party = offer.get("counterpartyAccountName", "Unknown")
                secured = "Secured" if offer.get("secured", True) else "Unsecured"

                # Format description based on action
                if action in ["accept", "decline"]:
                    title = f"{amount_str} from {party}"
                else:  # cancel
                    title = f"{amount_str} to {party}"

                # Create row for this offer
                row = {
                    "id": f"{action}_offer_{offer['credexID']}",
                    "title": title,
                    "description": f"Tap to {action} this {secured.lower()} credex"
                }
                current_section["rows"].append(row)

            sections.append(current_section)

            # Create interactive list message
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self.service.user.mobile_number,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "header": {
                        "type": "text",
                        "text": f"{action.title()} Offers"
                    },
                    "body": {
                        "text": f"*{self._get_action_emoji(action)} {action.title()} Offers*\n\nSelect an offer below to {action} it:"
                    },
                    "footer": {
                        "text": f"Tap on an offer to {action} it"
                    },
                    "action": {
                        "button": "View Offers",
                        "sections": sections
                    }
                }
            }
        except Exception as e:
            logger.error(f"Error creating offers list: {str(e)}")
            return self._format_error_response(str(e))

    def _get_action_emoji(self, action: str) -> str:
        """Get emoji for action type"""
        return {
            "accept": "✅",
            "decline": "❌",
            "cancel": "❌"
        }.get(action, "")

    def _parse_action_button(self, button_id: str) -> tuple[str, str]:
        """Parse action and credex ID from button ID"""
        try:
            # Expected formats:
            # Button: "accept_credex_123", "decline_credex_123", "cancel_credex_123"
            # List: "accept_offer_123", "decline_offer_123", "cancel_offer_123"
            parts = button_id.split("_")
            if len(parts) >= 2:
                action = parts[0]  # accept/decline/cancel
                credex_id = parts[-1]  # Last part is always the ID
                if action in ["accept", "decline", "cancel"] and credex_id:
                    return action, credex_id
            return None, None
        except Exception as e:
            logger.error(f"Error parsing action button: {str(e)}")
            return None, None

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
