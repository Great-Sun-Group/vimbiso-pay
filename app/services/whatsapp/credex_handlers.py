import logging
from typing import Dict, Any, List, Optional, Tuple

from core.transactions import (
    Transaction,
    TransactionOffer,
    TransactionType,
    TransactionError,
    create_transaction_service,
)
from services.state.service import StateStage
from .base_handler import BaseActionHandler
from .forms import offer_credex
from .screens import (
    CONFIRM_SECURED_CREDEX,
    CONFIRM_UNSECURED_CREDEX,
    OFFER_SUCCESSFUL,
)
from .types import WhatsAppMessage

logger = logging.getLogger(__name__)


class CredexActionHandler(BaseActionHandler):
    """Handler for Credex-related actions"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.transaction_service = create_transaction_service(
            api_client=self.service.credex_service
        )

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
            return self.get_response_template("An error occurred. Please try again.")

    def _validate_and_get_profile(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Validate and get profile data with proper state management"""
        user = self.service.user
        current_state = self.service.current_state

        # Check if profile refresh needed
        if not current_state.get("profile"):
            response = self.service.refresh(reset=True)
            if response:
                self.service.state.update_state(
                    user_id=user,
                    new_state={},
                    stage=StateStage.AUTH.value,
                    update_from="profile_refresh",
                    option="handle_action_register"
                )
                return self.get_response_template("Please log in again to continue.")

        # Get selected profile
        selected_profile = current_state.get("current_account")
        if not selected_profile:
            selected_profile = self._find_personal_account(current_state)
            if isinstance(selected_profile, WhatsAppMessage):
                return selected_profile

            # Update state with selected profile
            current_state["current_account"] = selected_profile
            self.service.state.update_state(
                user_id=user,
                new_state=current_state,
                stage=StateStage.CREDEX.value,
                update_from="profile_select",
                option="handle_action_offer_credex"
            )

        return current_state, selected_profile

    def _find_personal_account(self, current_state: Dict[str, Any]) -> Any:
        """Find personal account from available accounts"""
        try:
            accounts = current_state["profile"]["data"]["dashboard"]["accounts"]
            if not accounts:
                return self.get_response_template("No accounts found. Please try again later.")

            for account in accounts:
                if (account.get("success") and
                        account["data"].get("accountHandle") == self.service.user.mobile_number):
                    return account

            return self.get_response_template("Personal account not found. Please try again later.")
        except (KeyError, IndexError) as e:
            logger.error(f"Error finding personal account: {str(e)}")
            return self.get_response_template("Error loading account information. Please try again.")

    def _handle_offer_flow(
        self,
        current_state: Dict[str, Any],
        selected_profile: Dict[str, Any]
    ) -> Optional[WhatsAppMessage]:
        """Handle ongoing offer flow with proper state management"""
        try:
            if self._is_credex_command(self.service.body):
                return self._handle_credex_command(current_state, selected_profile)
            elif self.service.message_type == "nfm_reply":
                return self._handle_form_submission(current_state, selected_profile)
            elif self.service.message_type == "interactive":
                return self._handle_interactive_message(current_state, selected_profile)
            return None
        except Exception as e:
            logger.error(f"Error in offer flow: {str(e)}")
            return self.get_response_template("Error processing offer. Please try again.")

    def _start_offer_flow(self, current_state: Dict[str, Any]) -> WhatsAppMessage:
        """Start new offer flow with proper state management"""
        try:
            # Update state for offer flow
            current_state["offer_flow"] = True
            self.service.state.update_state(
                user_id=self.service.user,
                new_state=current_state,
                stage=StateStage.CREDEX.value,
                update_from="offer_start",
                option="handle_action_offer_credex"
            )
            return offer_credex(self.service.user.mobile_number, message="")
        except Exception as e:
            logger.error(f"Error starting offer flow: {str(e)}")
            return self.get_response_template("Error starting offer. Please try again.")

    def _handle_interactive_message(
        self,
        current_state: Dict[str, Any],
        selected_profile: Dict[str, Any]
    ) -> Optional[WhatsAppMessage]:
        """Handle interactive message responses"""
        try:
            interactive_type = self.service.message.get("interactive", {}).get("type")
            if interactive_type == "button_reply":
                button_id = self.service.message["interactive"]["button_reply"]["id"]
                if button_id == "confirm_offer":
                    return self._handle_offer_confirmation(current_state, selected_profile)
                elif button_id == "cancel_offer":
                    return self._handle_offer_cancellation(current_state)
            return None
        except Exception as e:
            logger.error(f"Error handling interactive message: {str(e)}")
            return self.get_response_template("Error processing response. Please try again.")

    def _handle_offer_cancellation(self, current_state: Dict[str, Any]) -> WhatsAppMessage:
        """Handle offer cancellation with proper state cleanup"""
        try:
            # Clear offer-related state
            current_state.pop("offer_flow", None)
            current_state.pop("form_shown", None)
            current_state.pop("confirmation_shown", None)

            # Update state to return to menu
            self.service.state.update_state(
                user_id=self.service.user,
                new_state=current_state,
                stage=StateStage.MENU.value,
                update_from="offer_cancel",
                option="handle_action_menu"
            )
            return self.get_response_template("Offer cancelled. Returning to menu.")
        except Exception as e:
            logger.error(f"Error cancelling offer: {str(e)}")
            return self.get_response_template("Error cancelling offer. Please try again.")

    def _is_credex_command(self, body: str) -> bool:
        """Check if message is a credex command"""
        return "=>" in str(body) or "->" in str(body)

    def _handle_credex_command(
        self, current_state: Dict[str, Any], selected_profile: Dict[str, Any]
    ) -> WhatsAppMessage:
        """Handle credex command processing with proper error handling"""
        try:
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
            self.service.state.update_state(
                user_id=self.service.user,
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

    def _handle_form_submission(
        self, current_state: Dict[str, Any], selected_profile: Dict[str, Any]
    ) -> WhatsAppMessage:
        """Handle form submission processing with proper state management"""
        try:
            offer = TransactionOffer(
                authorizer_member_id=current_state["profile"]["data"]["action"]["details"]["memberID"],
                issuer_member_id=selected_profile["data"]["accountID"],
                amount=float(self.service.body.get("amount")),
                currency=self.service.body.get("currency"),
                type=TransactionType.SECURED_CREDEX,
                handle=self.service.body.get("handle"),
            )

            result = self.transaction_service.create_offer(offer)
            if not result.success:
                return self._format_error_response(result.error_message)

            # Update state with offer details
            current_state["offer_details"] = offer.to_dict()
            self.service.state.update_state(
                user_id=self.service.user,
                new_state=current_state,
                stage=StateStage.CREDEX.value,
                update_from="form_submit",
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
            logger.error(f"Error processing form submission: {str(e)}")
            return self._format_error_response(str(e))

    def _handle_offer_confirmation(
        self, current_state: Dict[str, Any], selected_profile: Dict[str, Any]
    ) -> WhatsAppMessage:
        """Handle offer confirmation with proper state management"""
        try:
            transaction_id = current_state.get("confirm_offer_payload", {}).get("id")
            if not transaction_id:
                return self._format_error_response("No transaction to confirm")

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
            current_state["last_transaction"] = result.transaction.to_dict()
            self.service.state.update_state(
                user_id=self.service.user,
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
            template = (
                CONFIRM_SECURED_CREDEX if offer.type == TransactionType.SECURED_CREDEX
                else CONFIRM_UNSECURED_CREDEX
            )

            date_str = (
                f"*Due Date :* {offer.due_date}"
                if offer.type == TransactionType.UNSECURED_CREDEX else ""
            )

            return {
                "messaging_product": "whatsapp",
                "to": self.service.user.mobile_number,
                "recipient_type": "individual",
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {
                        "text": template.format(
                            party=offer.metadata.get("full_name"),
                            amount=offer.amount,
                            currency=offer.currency,
                            source=current_state.get("current_account", {}).get("accountName"),
                            handle=offer.handle,
                            secured="*secured*" if offer.type == TransactionType.SECURED_CREDEX else "*unsecured*",
                            date=date_str,
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
            return self.get_response_template("Error displaying confirmation. Please try again.")

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
                    currency=transaction.offer.currency,
                    recipient=transaction.metadata.get("receiverAccountName"),
                    source=selected_profile["data"]["accountName"],
                    secured="*Secured* credex" if transaction.offer.type == TransactionType.SECURED_CREDEX
                    else "*Unsecured* credex",
                )
            )
        except Exception as e:
            logger.error(f"Error formatting success response: {str(e)}")
            return self.get_response_template("Offer completed successfully.")

    def _format_error_response(self, message: str) -> WhatsAppMessage:
        """Format error response with proper error handling"""
        try:
            error_message = self.format_synopsis(
                message.replace("Error:", "")
            )
        except Exception as e:
            logger.error(f"Error formatting error message: {str(e)}")
            error_message = "An error occurred. Please try again."

        return self.get_response_template(error_message)
