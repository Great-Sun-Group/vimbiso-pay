import logging
import re
from typing import Any, Dict, Tuple

from core.transactions import (TransactionError, TransactionOffer,
                               TransactionType)
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

            if self._is_credex_command(self.service.body):
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

            logger.error(f"Unhandled message type: {self.service.message_type}")
            return self._format_error_response("Invalid message type. Please try again.")
        except Exception as e:
            logger.error(f"Error in offer flow: {str(e)}")
            return self._format_error_response("Error processing offer. Please try again.")

    def _start_offer_flow(self, current_state: Dict[str, Any]) -> WhatsAppMessage:
        """Start offer flow with form"""
        try:
            # First update state to handle_action_offer_credex
            # Preserve JWT token
            if self.service.credex_service.jwt_token:
                current_state["jwt_token"] = self.service.credex_service.jwt_token
            self.service.state.update_state(
                user_id=self.service.user.mobile_number,
                new_state=current_state,
                stage="handle_action_offer_credex",
                update_from="offer_init",
                option="handle_action_offer_credex"
            )

            # Then update state for credex stage
            current_state["offer_flow"] = True
            self.service.state.update_state(
                user_id=self.service.user.mobile_number,
                new_state=current_state,
                stage=StateStage.CREDEX.value,
                update_from="offer_start",
                option="handle_action_offer_credex"
            )

            # Show form
            return offer_credex(self.service.user.mobile_number, message="")
        except Exception as e:
            logger.error(f"Error starting offer flow: {str(e)}")
            return self._format_error_response("Error starting offer. Please try again.")

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

            # Get receiver's account ID from handle validation response
            receiver_account_id = handle_data.get("data", {}).get("accountID")
            if not receiver_account_id:
                logger.error(f"No account ID found in handle validation response: {handle_data}")
                return self._format_error_response("Could not find recipient's account. Please check the handle and try again.")

            # Add phone number to form data for token refresh
            form_data["phone"] = self.service.user.mobile_number

            # Create offer with receiver's account ID
            offer = TransactionOffer(
                authorizer_member_id=current_state["profile"]["data"]["action"]["details"]["memberID"],
                issuer_member_id=selected_profile["data"]["accountID"],
                receiver_account_id=receiver_account_id,
                amount=amount,
                denomination=denomination,
                type=TransactionType.SECURED_CREDEX,
                handle=form_data.get("recipientAccountHandle", ""),
            )

            # Ensure JWT token is set
            if current_state.get("jwt_token"):
                self.service.credex_service.jwt_token = current_state["jwt_token"]

            try:
                result = self.transaction_service.create_offer(offer)
                if not result.success:
                    return self._format_error_response(result.error_message or "Failed to create offer")

                # Update state with offer details
                current_state["offer_details"] = offer.to_dict()
                # Preserve JWT token
                if self.service.credex_service.jwt_token:
                    current_state["jwt_token"] = self.service.credex_service.jwt_token
                self.service.state.update_state(
                    user_id=self.service.user.mobile_number,
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
                logger.error(f"Transaction error: {str(e)}")
                return self._format_error_response(str(e))

        except Exception as e:
            logger.error(f"Error processing form submission: {str(e)}")
            return self._format_error_response("Error processing offer. Please try again.")
