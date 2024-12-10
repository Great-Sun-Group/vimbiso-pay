import logging
import re
from typing import Any, Dict, Tuple

from core.transactions import (TransactionOffer, TransactionType)
from services.state.service import StateStage

from ...base_handler import BaseActionHandler
from ...forms import offer_credex
from ...types import WhatsAppMessage

logger = logging.getLogger(__name__)


class OfferFlowMixin(BaseActionHandler):
    """Mixin for handling the offer creation flow"""

    VALID_DENOMINATIONS = {"USD", "ZWG", "XAU", "CAD"}
    AMOUNT_PATTERN = re.compile(r'^(?:([A-Z]{3})\s+)?(\d+(?:\.\d+)?)$')

    def _handle_offer_flow(
        self,
        current_state: Dict[str, Any],
        selected_profile: Dict[str, Any]
    ) -> WhatsAppMessage:
        """Handle ongoing offer flow with proper state management"""
        try:
            logger.debug(f"Handling offer flow with message type: {self.service.message_type}")
            logger.debug(f"Message body: {self.service.body}")
            logger.debug(f"Interactive message: {self.service.message.get('interactive', {})}")

            # Check for offer commands first
            if self.service.message_type == "text" and isinstance(self.service.body, str):
                if self.service.body.startswith("cancel_offer_"):
                    credex_id = self.service.body.replace("cancel_offer_", "")
                    return self._handle_offer_cancellation(current_state, credex_id)
                elif self.service.body.startswith("accept_offer_"):
                    credex_id = self.service.body.replace("accept_offer_", "")
                    return self._handle_offer_acceptance(current_state, credex_id)
                elif self.service.body.startswith("decline_offer_"):
                    credex_id = self.service.body.replace("decline_offer_", "")
                    return self._handle_offer_decline(current_state, credex_id)

            elif self._is_credex_command(self.service.body):
                return self._handle_credex_command(current_state, selected_profile)
            elif self.service.message_type == "nfm_reply":
                logger.debug("Processing form submission")
                return self._handle_form_submission(current_state, selected_profile)
            elif self.service.message_type == "interactive":
                message_type = self.service.message.get("interactive", {}).get("type")
                if message_type == "button_reply":
                    return self._handle_interactive_message(current_state, selected_profile)
                elif message_type == "nfm_reply":
                    logger.debug("Processing form submission from interactive message")
                    return self._handle_form_submission(current_state, selected_profile)
                elif message_type == "list_reply":
                    selected_id = self.service.message["interactive"]["list_reply"]["id"]
                    logger.debug(f"Processing list selection: {selected_id}")
                    if selected_id.startswith("cancel_offer_"):
                        credex_id = selected_id.replace("cancel_offer_", "")
                        logger.debug(f"Cancelling offer with ID: {credex_id}")
                        return self._handle_offer_cancellation(current_state, credex_id)
                    elif selected_id.startswith("accept_offer_"):
                        credex_id = selected_id.replace("accept_offer_", "")
                        logger.debug(f"Accepting offer with ID: {credex_id}")
                        return self._handle_offer_acceptance(current_state, credex_id)
                    elif selected_id.startswith("decline_offer_"):
                        credex_id = selected_id.replace("decline_offer_", "")
                        logger.debug(f"Declining offer with ID: {credex_id}")
                        return self._handle_offer_decline(current_state, credex_id)

            logger.error(f"Unhandled message type: {self.service.message_type}")
            return self._format_error_response("Invalid message type. Please try again.")
        except Exception as e:
            logger.error(f"Error in offer flow: {str(e)}", exc_info=True)
            return self._format_error_response(str(e))

    def _handle_offer_acceptance(self, current_state: Dict[str, Any], credex_id: str) -> WhatsAppMessage:
        """Handle offer acceptance with proper state management"""
        try:
            logger.debug(f"Accepting offer: {credex_id}")
            # Ensure JWT token is set
            if current_state.get("jwt_token"):
                logger.debug("Setting JWT token from state")
                self.service.credex_service.jwt_token = current_state["jwt_token"]

            # Accept the offer
            success, message = self.service.credex_service.accept_credex(credex_id)
            logger.debug(f"Accept offer result - success: {success}, message: {message}")
            if not success:
                return self._format_error_response(f"Failed to accept offer: {message}")

            # Clear offer-related state
            current_state.pop("offer_flow", None)
            current_state.pop("form_shown", None)
            current_state.pop("confirmation_shown", None)
            current_state.pop("selected_denomination", None)

            # Preserve JWT token
            if self.service.credex_service.jwt_token:
                current_state["jwt_token"] = self.service.credex_service.jwt_token

            # Get fresh dashboard data
            success, data = self.service.credex_service._member.get_dashboard(self.service.user.mobile_number)
            if not success:
                return self.get_response_template("Offer accepted successfully. Failed to refresh dashboard.")

            # Update state with fresh dashboard data
            current_state["profile"] = data
            current_state["last_refresh"] = True
            current_state["current_account"] = None  # Force reselection of account with fresh data

            self.service.state.update_state(
                user_id=self.service.user.mobile_number,
                new_state=current_state,
                stage=StateStage.MENU.value,
                update_from="offer_accept",
                option="handle_action_menu"
            )

            # Show success message and updated dashboard
            return self.service.action_handler.auth_handler.handle_action_menu(
                message="✅ Offer accepted successfully.\n\n",
                login=True  # Force fresh data
            )

        except Exception as e:
            logger.error(f"Error accepting offer: {str(e)}", exc_info=True)
            return self._format_error_response(str(e))

    def _handle_offer_decline(self, current_state: Dict[str, Any], credex_id: str) -> WhatsAppMessage:
        """Handle offer decline with proper state management"""
        try:
            logger.debug(f"Declining offer: {credex_id}")
            # Ensure JWT token is set
            if current_state.get("jwt_token"):
                logger.debug("Setting JWT token from state")
                self.service.credex_service.jwt_token = current_state["jwt_token"]

            # Decline the offer
            success, message = self.service.credex_service.decline_credex(credex_id)
            logger.debug(f"Decline offer result - success: {success}, message: {message}")
            if not success:
                return self._format_error_response(f"Failed to decline offer: {message}")

            # Clear offer-related state
            current_state.pop("offer_flow", None)
            current_state.pop("form_shown", None)
            current_state.pop("confirmation_shown", None)
            current_state.pop("selected_denomination", None)

            # Preserve JWT token
            if self.service.credex_service.jwt_token:
                current_state["jwt_token"] = self.service.credex_service.jwt_token

            # Get fresh dashboard data
            success, data = self.service.credex_service._member.get_dashboard(self.service.user.mobile_number)
            if not success:
                return self.get_response_template("Offer declined successfully. Failed to refresh dashboard.")

            # Update state with fresh dashboard data
            current_state["profile"] = data
            current_state["last_refresh"] = True
            current_state["current_account"] = None  # Force reselection of account with fresh data

            self.service.state.update_state(
                user_id=self.service.user.mobile_number,
                new_state=current_state,
                stage=StateStage.MENU.value,
                update_from="offer_decline",
                option="handle_action_menu"
            )

            # Show success message and updated dashboard
            return self.service.action_handler.auth_handler.handle_action_menu(
                message="✅ Offer declined successfully.\n\n",
                login=True  # Force fresh data
            )

        except Exception as e:
            logger.error(f"Error declining offer: {str(e)}", exc_info=True)
            return self._format_error_response(str(e))

    def _handle_button_response(
        self,
        current_state: Dict[str, Any],
        selected_profile: Dict[str, Any]
    ) -> WhatsAppMessage:
        """Handle button responses that come through as text"""
        try:
            button_id = self.service.body
            if button_id == "confirm_offer":
                # Get offer details from state
                offer_details = current_state.get("offer_details", {})
                if not offer_details:
                    return self._format_error_response("No offer details found")

                # Create the offer now that user has confirmed
                offer = TransactionOffer(
                    authorizer_member_id=offer_details["authorizer_member_id"],
                    issuer_member_id=offer_details["issuer_member_id"],
                    receiver_account_id=offer_details["receiver_account_id"],
                    amount=offer_details["amount"],
                    denomination=offer_details["denomination"],
                    type=TransactionType.SECURED_CREDEX,
                    handle=offer_details["handle"],
                    metadata=offer_details.get("metadata", {})
                )

                # Create the offer through the API
                result = self.transaction_service.create_offer(offer)
                if not result.success:
                    return self._format_error_response(result.error_message or "Failed to create offer")

                # Update state with created offer details
                current_state["offer_details"] = {
                    **offer_details,
                    "credexID": result.transaction.id
                }

                # Preserve JWT token
                if self.service.credex_service.jwt_token:
                    current_state["jwt_token"] = self.service.credex_service.jwt_token

                # Update state
                self.service.state.update_state(
                    user_id=self.service.user.mobile_number,
                    new_state=current_state,
                    stage=StateStage.CREDEX.value,
                    update_from="offer_confirm",
                    option="handle_action_offer_credex"
                )

                # Format success message
                return self._format_success_response(result.transaction, selected_profile)

            elif button_id == "cancel_offer":
                return self._handle_offer_cancellation(current_state)

            return self._format_error_response("Invalid button response. Please try again.")
        except Exception as e:
            logger.error(f"Error handling button response: {str(e)}", exc_info=True)
            return self._format_error_response(str(e))

    def _start_offer_flow(self, current_state: Dict[str, Any]) -> WhatsAppMessage:
        """Start offer flow with form"""
        try:
            # Check for offer commands first
            if self.service.message_type == "text" and isinstance(self.service.body, str):
                if self.service.body.startswith("cancel_offer_"):
                    credex_id = self.service.body.replace("cancel_offer_", "")
                    return self._handle_offer_cancellation(current_state, credex_id)
                elif self.service.body.startswith("accept_offer_"):
                    credex_id = self.service.body.replace("accept_offer_", "")
                    return self._handle_offer_acceptance(current_state, credex_id)
                elif self.service.body.startswith("decline_offer_"):
                    credex_id = self.service.body.replace("decline_offer_", "")
                    return self._handle_offer_decline(current_state, credex_id)

            # Preserve JWT token
            if self.service.credex_service.jwt_token:
                current_state["jwt_token"] = self.service.credex_service.jwt_token

            # Set offer flow flag and update state once
            current_state["offer_flow"] = True
            self.service.state.update_state(
                user_id=self.service.user.mobile_number,
                new_state=current_state,
                stage=StateStage.CREDEX.value,  # Use consistent CREDEX stage
                update_from="offer_start",
                option="handle_action_offer_credex"
            )

            # Show form
            return offer_credex(self.service.user.mobile_number, message="")
        except Exception as e:
            logger.error(f"Error starting offer flow: {str(e)}", exc_info=True)
            return self._format_error_response(str(e))

    def _parse_amount_with_denomination(self, amount_str: str) -> Tuple[float, str]:
        """Parse amount string to extract denomination and value

        Args:
            amount_str: Amount string possibly with denomination prefix

        Returns:
            Tuple[float, str]: (amount, denomination)
        """
        amount_str = amount_str.strip().upper()
        match = self.AMOUNT_PATTERN.match(amount_str)

        if not match:
            raise ValueError("Invalid amount format")

        denom, amount = match.groups()
        return float(amount), denom or "USD"  # Default to USD if no denomination specified

    def _handle_form_submission(
        self, current_state: Dict[str, Any], selected_profile: Dict[str, Any]
    ) -> WhatsAppMessage:
        """Handle form submission processing with proper state management"""
        try:
            # Check for offer commands first
            if self.service.message_type == "text" and isinstance(self.service.body, str):
                if self.service.body.startswith("cancel_offer_"):
                    credex_id = self.service.body.replace("cancel_offer_", "")
                    return self._handle_offer_cancellation(current_state, credex_id)
                elif self.service.body.startswith("accept_offer_"):
                    credex_id = self.service.body.replace("accept_offer_", "")
                    return self._handle_offer_acceptance(current_state, credex_id)
                elif self.service.body.startswith("decline_offer_"):
                    credex_id = self.service.body.replace("decline_offer_", "")
                    return self._handle_offer_decline(current_state, credex_id)

            # For nfm_reply, body is already a dict with form data
            form_data = self.service.body
            if not isinstance(form_data, dict):
                logger.error("Invalid form data format")
                return self._format_error_response("Invalid form submission. Please try again.")

            # Validate required fields
            if not all([form_data.get("amount"), form_data.get("recipientAccountHandle")]):
                return self._format_error_response("Please fill in all required fields.")

            try:
                amount, denomination = self._parse_amount_with_denomination(form_data["amount"])
                if denomination not in self.VALID_DENOMINATIONS:
                    return self._format_error_response(
                        f"Invalid denomination. Please use one of: {', '.join(self.VALID_DENOMINATIONS)}"
                    )
            except ValueError:
                return self._format_error_response(
                    "Invalid amount format. Please enter amount like '100' for USD or 'ZWG 100' for other denominations."
                )

            # First validate the handle to get receiver's account ID
            success, handle_data = self.service.credex_service._member.validate_handle(form_data["recipientAccountHandle"])
            if not success:
                error_msg = handle_data.get("message", "Invalid recipient handle")
                return self._format_error_response(error_msg)

            # Get receiver's account ID and name from handle validation response
            receiver_data = handle_data.get("data", {})
            receiver_account_id = receiver_data.get("accountID")
            receiver_name = receiver_data.get("accountName")

            # If we didn't get the data directly, try the action details path
            if not receiver_account_id or not receiver_name:
                action_details = receiver_data.get("action", {}).get("details", {})
                receiver_account_id = receiver_account_id or action_details.get("accountID")
                receiver_name = receiver_name or action_details.get("accountName")

            # Final fallback to handle
            receiver_name = receiver_name or form_data["recipientAccountHandle"]

            if not receiver_account_id:
                logger.error(f"No account ID found in handle validation response: {handle_data}")
                return self._format_error_response("Could not find recipient's account. Please check the handle and try again.")

            # Add phone number to form data for token refresh
            form_data["phone"] = self.service.user.mobile_number

            # Store offer details in state for confirmation
            offer_details = {
                "authorizer_member_id": current_state["profile"]["data"]["action"]["details"]["memberID"],
                "issuer_member_id": selected_profile["data"]["accountID"],
                "receiver_account_id": receiver_account_id,
                "amount": amount,
                "denomination": denomination,
                "type": "secured_credex",  # Store as string for JSON serialization
                "handle": form_data.get("recipientAccountHandle", ""),
                "metadata": {"full_name": receiver_name}
            }

            # Update state with offer details and current account
            current_state["offer_details"] = offer_details
            current_state["current_account"] = selected_profile

            # Preserve JWT token
            if self.service.credex_service.jwt_token:
                current_state["jwt_token"] = self.service.credex_service.jwt_token

            # Update state
            self.service.state.update_state(
                user_id=self.service.user.mobile_number,
                new_state=current_state,
                stage=StateStage.CREDEX.value,
                update_from="form_submit",
                option="handle_action_offer_credex"
            )

            # Create TransactionOffer for confirmation message
            offer = TransactionOffer(
                authorizer_member_id=offer_details["authorizer_member_id"],
                issuer_member_id=offer_details["issuer_member_id"],
                receiver_account_id=offer_details["receiver_account_id"],
                amount=offer_details["amount"],
                denomination=offer_details["denomination"],
                type=TransactionType.SECURED_CREDEX,
                handle=offer_details["handle"],
                metadata=offer_details["metadata"]
            )

            # Show confirmation message
            return self._format_confirmation_message(
                offer,
                current_state,
                self.transaction_service.get_available_accounts(
                    current_state["profile"]["data"]["action"]["details"]["memberID"]
                )
            )

        except Exception as e:
            logger.error(f"Error processing form submission: {str(e)}", exc_info=True)
            return self._format_error_response(str(e))

    def _handle_offer_cancellation(self, current_state: Dict[str, Any], credex_id: str = None) -> WhatsAppMessage:
        """Handle offer cancellation with proper state cleanup"""
        try:
            if credex_id:
                logger.debug(f"Cancelling specific offer: {credex_id}")
                # Ensure JWT token is set
                if current_state.get("jwt_token"):
                    logger.debug("Setting JWT token from state")
                    self.service.credex_service.jwt_token = current_state["jwt_token"]

                # Cancel specific offer
                success, message = self.service.credex_service.cancel_credex(credex_id)
                logger.debug(f"Cancel offer result - success: {success}, message: {message}")
                if not success:
                    return self._format_error_response(f"Failed to cancel offer: {message}")

            # Clear offer-related state
            current_state.pop("offer_flow", None)
            current_state.pop("form_shown", None)
            current_state.pop("confirmation_shown", None)
            current_state.pop("selected_denomination", None)

            # Preserve JWT token
            if self.service.credex_service.jwt_token:
                current_state["jwt_token"] = self.service.credex_service.jwt_token

            # Get fresh dashboard data
            success, data = self.service.credex_service._member.get_dashboard(self.service.user.mobile_number)
            if not success:
                return self.get_response_template("Offer cancelled successfully. Failed to refresh dashboard.")

            # Update state with fresh dashboard data
            current_state["profile"] = data
            current_state["last_refresh"] = True
            current_state["current_account"] = None  # Force reselection of account with fresh data

            self.service.state.update_state(
                user_id=self.service.user.mobile_number,
                new_state=current_state,
                stage=StateStage.MENU.value,
                update_from="offer_cancel",
                option="handle_action_menu"
            )

            # Show success message and updated dashboard
            return self.service.action_handler.auth_handler.handle_action_menu(
                message="✅ Offer cancelled successfully.\n\n",
                login=True  # Force fresh data
            )

        except Exception as e:
            logger.error(f"Error cancelling offer: {str(e)}", exc_info=True)
            return self._format_error_response(str(e))