import logging

from core.transactions import create_transaction_service
from services.state.service import StateStage
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

            # Check for commands first
            if self.service.message_type == "text" and self._is_credex_command(self.service.body):
                logger.debug(f"Handling credex command: {self.service.body}")
                return self._handle_credex_command(current_state, selected_profile)

            # Handle offer flow states
            if current_state.get("offer_flow"):
                return self._handle_offer_flow(current_state, selected_profile)

            # Start new offer flow
            return self._start_offer_flow(current_state)

        except Exception as e:
            logger.error(f"Error handling credex offer: {str(e)}")
            # Use _format_error_response to properly format the error message
            return self._format_error_response(str(e))

    def handle_action_pending_offers_out(self) -> WhatsAppMessage:
        """Handle viewing and managing outgoing offers"""
        try:
            logger.debug("Starting handle_action_pending_offers_out")
            # Validate and get profile data
            profile_result = self._validate_and_get_profile()
            if isinstance(profile_result, WhatsAppMessage):
                return profile_result

            current_state, selected_profile = profile_result

            # Check for commands first
            if self.service.message_type == "text" and self._is_credex_command(self.service.body):
                logger.debug(f"Handling credex command: {self.service.body}")
                return self._handle_credex_command(current_state, selected_profile)

            # Get pending outgoing offers from current state
            pending_out_data = selected_profile.get("data", {}).get("pendingOutData", {})
            if not pending_out_data.get("success", False):
                return self._format_error_response("Failed to get pending offers data")

            pending_offers = pending_out_data.get("data", [])
            if not pending_offers:
                return self.get_response_template("You have no pending outgoing offers to cancel.")

            # Format offers into a list message
            sections = []
            current_section = {
                "title": "Select an Offer to Cancel",
                "rows": []
            }

            for offer in pending_offers:
                # Get amount and recipient
                amount_str = offer.get("formattedInitialAmount", "").strip("-")  # Remove negative sign
                recipient = offer.get("counterpartyAccountName", "Unknown")
                secured = "Secured" if offer.get("secured", True) else "Unsecured"

                # Create row for this offer
                row = {
                    "id": f"cancel_offer_{offer['credexID']}",  # ID format for cancel action
                    "title": f"{amount_str} to {recipient}",
                    "description": f"Tap to cancel this {secured.lower()} credex"
                }
                current_section["rows"].append(row)

            sections.append(current_section)

            # Update state to handle cancellation
            current_state["stage"] = StateStage.CREDEX.value
            current_state["option"] = "handle_action_pending_offers_out"
            # Preserve JWT token
            if self.service.credex_service.jwt_token:
                current_state["jwt_token"] = self.service.credex_service.jwt_token

            self.service.state.update_state(
                user_id=self.service.user.mobile_number,
                new_state=current_state,
                stage=StateStage.CREDEX.value,
                update_from="pending_offers_out",
                option="handle_action_pending_offers_out"
            )

            # Create interactive list message with header
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self.service.user.mobile_number,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "header": {
                        "type": "text",
                        "text": "Pending Offers"
                    },
                    "body": {
                        "text": "*❌ Cancel Outgoing Offers*\n\nSelect an offer below to cancel it:"
                    },
                    "footer": {
                        "text": "Tap on an offer to cancel it"
                    },
                    "action": {
                        "button": "View Offers",
                        "sections": sections
                    }
                }
            }

        except Exception as e:
            logger.error(f"Error handling pending offers: {str(e)}")
            return self._format_error_response(str(e))

    def handle_action_accept_offers(self) -> WhatsAppMessage:
        """Handle viewing and accepting incoming offers"""
        try:
            logger.debug("Starting handle_action_accept_offers")
            # Validate and get profile data
            profile_result = self._validate_and_get_profile()
            if isinstance(profile_result, WhatsAppMessage):
                return profile_result

            current_state, selected_profile = profile_result

            # Check for commands first
            if self.service.message_type == "text" and self._is_credex_command(self.service.body):
                logger.debug(f"Handling credex command: {self.service.body}")
                return self._handle_credex_command(current_state, selected_profile)

            # Get pending incoming offers from current state
            pending_in_data = selected_profile.get("data", {}).get("pendingInData", {})
            if not pending_in_data.get("success", False):
                return self._format_error_response("Failed to get incoming offers data")

            pending_offers = pending_in_data.get("data", [])
            if not pending_offers:
                return self.get_response_template("You have no pending incoming offers to accept.")

            # Format offers into a list message
            sections = []
            current_section = {
                "title": "Select an Offer to Accept",
                "rows": []
            }

            for offer in pending_offers:
                # Get amount and sender
                amount_str = offer.get("formattedInitialAmount", "")
                sender = offer.get("counterpartyAccountName", "Unknown")
                secured = "Secured" if offer.get("secured", True) else "Unsecured"

                # Create row for this offer
                row = {
                    "id": f"accept_offer_{offer['credexID']}",  # ID format for accept action
                    "title": f"{amount_str} from {sender}",
                    "description": f"Tap to accept this {secured.lower()} credex"
                }
                current_section["rows"].append(row)

            sections.append(current_section)

            # Update state to handle acceptance
            current_state["stage"] = StateStage.CREDEX.value
            current_state["option"] = "handle_action_accept_offers"
            # Preserve JWT token
            if self.service.credex_service.jwt_token:
                current_state["jwt_token"] = self.service.credex_service.jwt_token

            self.service.state.update_state(
                user_id=self.service.user.mobile_number,
                new_state=current_state,
                stage=StateStage.CREDEX.value,
                update_from="accept_offers",
                option="handle_action_accept_offers"
            )

            # Create interactive list message with header
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self.service.user.mobile_number,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "header": {
                        "type": "text",
                        "text": "Incoming Offers"
                    },
                    "body": {
                        "text": "*✅ Accept Incoming Offers*\n\nSelect an offer below to accept it:"
                    },
                    "footer": {
                        "text": "Tap on an offer to accept it"
                    },
                    "action": {
                        "button": "View Offers",
                        "sections": sections
                    }
                }
            }

        except Exception as e:
            logger.error(f"Error handling incoming offers: {str(e)}")
            return self._format_error_response(str(e))

    def handle_action_decline_offers(self) -> WhatsAppMessage:
        """Handle viewing and declining incoming offers"""
        try:
            logger.debug("Starting handle_action_decline_offers")
            # Validate and get profile data
            profile_result = self._validate_and_get_profile()
            if isinstance(profile_result, WhatsAppMessage):
                return profile_result

            current_state, selected_profile = profile_result

            # Check for commands first
            if self.service.message_type == "text" and self._is_credex_command(self.service.body):
                logger.debug(f"Handling credex command: {self.service.body}")
                return self._handle_credex_command(current_state, selected_profile)

            # Get pending incoming offers from current state
            pending_in_data = selected_profile.get("data", {}).get("pendingInData", {})
            if not pending_in_data.get("success", False):
                return self._format_error_response("Failed to get incoming offers data")

            pending_offers = pending_in_data.get("data", [])
            if not pending_offers:
                return self.get_response_template("You have no pending incoming offers to decline.")

            # Format offers into a list message
            sections = []
            current_section = {
                "title": "Select an Offer to Decline",
                "rows": []
            }

            for offer in pending_offers:
                # Get amount and sender
                amount_str = offer.get("formattedInitialAmount", "")
                sender = offer.get("counterpartyAccountName", "Unknown")
                secured = "Secured" if offer.get("secured", True) else "Unsecured"

                # Create row for this offer
                row = {
                    "id": f"decline_offer_{offer['credexID']}",  # ID format for decline action
                    "title": f"{amount_str} from {sender}",
                    "description": f"Tap to decline this {secured.lower()} credex"
                }
                current_section["rows"].append(row)

            sections.append(current_section)

            # Update state to handle decline
            current_state["stage"] = StateStage.CREDEX.value
            current_state["option"] = "handle_action_decline_offers"
            # Preserve JWT token
            if self.service.credex_service.jwt_token:
                current_state["jwt_token"] = self.service.credex_service.jwt_token

            self.service.state.update_state(
                user_id=self.service.user.mobile_number,
                new_state=current_state,
                stage=StateStage.CREDEX.value,
                update_from="decline_offers",
                option="handle_action_decline_offers"
            )

            # Create interactive list message with header
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self.service.user.mobile_number,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "header": {
                        "type": "text",
                        "text": "Incoming Offers"
                    },
                    "body": {
                        "text": "*❌ Decline Incoming Offers*\n\nSelect an offer below to decline it:"
                    },
                    "footer": {
                        "text": "Tap on an offer to decline it"
                    },
                    "action": {
                        "button": "View Offers",
                        "sections": sections
                    }
                }
            }

        except Exception as e:
            logger.error(f"Error handling incoming offers: {str(e)}")
            return self._format_error_response(str(e))
