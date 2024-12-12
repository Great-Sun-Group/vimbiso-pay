"""Mixin for handling credex action flows"""
import logging
from typing import Dict, Optional, Any

from core.messaging.types import Message as WhatsAppMessage
from services.state.service import StateStage
from .action_flows import AcceptCredexFlow, DeclineCredexFlow, CancelCredexFlow

logger = logging.getLogger(__name__)


class ActionFlowMixin:
    """Mixin for handling credex action flows"""

    def _handle_credex_action(self, action: str, credex_id: str, offer_data: Dict[str, Any]) -> WhatsAppMessage:
        """Handle credex action (accept/decline/cancel)"""
        try:
            logger.debug(f"Handling credex action: {action} for credex_id: {credex_id}")

            # Initialize appropriate flow
            flow_map = {
                "accept": AcceptCredexFlow("accept_credex"),
                "decline": DeclineCredexFlow("decline_credex"),
                "cancel": CancelCredexFlow("cancel_credex")
            }

            flow = flow_map.get(action)
            if not flow:
                logger.error(f"Invalid action: {action}")
                return self._format_error_response(f"Invalid action: {action}")

            # Inject services
            flow.credex_service = self.service.credex_service

            # Set flow state
            flow.state.update({
                "credex_id": credex_id,
                "phone": self.service.user.mobile_number,
                "amount": {
                    "amount": offer_data.get("initialAmount"),
                    "denomination": offer_data.get("denomination", "USD")
                },
                "sender_name": offer_data.get("counterpartyAccountName"),
                "recipient_name": offer_data.get("counterpartyAccountName")
            })

            # Update state BEFORE executing flow
            current_state = self.service.current_state
            current_state["stage"] = StateStage.CREDEX.value
            current_state["option"] = f"handle_action_{action}_offers"

            # Preserve JWT token
            if self.service.credex_service.jwt_token:
                current_state["jwt_token"] = self.service.credex_service.jwt_token

            # Update state
            self.service.state.update_state(
                user_id=self.service.user.mobile_number,
                new_state=current_state,
                stage=StateStage.CREDEX.value,
                update_from=f"{action}_offer",
                option=f"handle_action_{action}_offers"
            )

            # Execute flow
            success, message = flow.complete_flow()
            if not success:
                logger.error(f"Failed to {action} credex: {message}")
                return self._format_error_response(message)

            # Return success message
            return self.get_response_template(
                f"✅ Successfully {action}ed the credex offer.\n\n"
                "Type *Menu* to return to the main menu."
            )

        except Exception as e:
            logger.exception(f"Error in credex action flow: {str(e)}")
            return self._format_error_response(str(e))

    def _extract_credex_id_from_button(self, button_id: str) -> Optional[str]:
        """Extract credex ID from button ID"""
        if not button_id:
            return None

        # Expected format: "{action}_offer_{credex_id}"
        parts = button_id.split("_")
        if len(parts) >= 3:
            return parts[2]
        return None

    def _get_offer_data(self, credex_id: str, profile_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get offer data from profile data"""
        # Check incoming offers
        pending_in = profile_data.get("data", {}).get("pendingInData", {}).get("data", [])
        for offer in pending_in:
            if offer.get("credexID") == credex_id:
                return offer

        # Check outgoing offers
        pending_out = profile_data.get("data", {}).get("pendingOutData", {}).get("data", [])
        for offer in pending_out:
            if offer.get("credexID") == credex_id:
                return offer

        return None
