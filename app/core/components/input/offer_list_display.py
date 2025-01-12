"""Offer list display component

This component handles displaying a list of Credex offers and processing offer selection.
"""

import logging
from typing import Any, Dict, List

from core.error.types import ValidationResult
from core.messaging.types import Button
from core.components.base import InputComponent

logger = logging.getLogger(__name__)

# Offer list templates
OFFER_LIST = """📋 *{title}*

{offers}"""

OFFER_ITEM = """💰 *{amount}*
👤 From: {counterparty}
📊 Status: {status}
🆔 ID: {id}
"""


class OfferListDisplay(InputComponent):
    """Handles displaying a list of Credex offers and processing selection"""

    def __init__(self):
        super().__init__("offer_list_display")

    def _validate(self, value: Any) -> ValidationResult:
        """Validate offer display and selection

        Args:
            value: None for initial display, or incoming message for selection
        """
        try:
            # Get current state
            current_data = self.state_manager.get_state_value("component_data", {})
            incoming_message = current_data.get("incoming_message")

            # Initial activation - display offer list
            if not current_data.get("awaiting_input"):
                return self._display_offers()

            # Process offer selection
            if not incoming_message:
                return ValidationResult.success(None)

            # Validate interactive message
            if incoming_message.get("type") != "interactive":
                return ValidationResult.failure(
                    message="Please select an offer using the buttons provided",
                    field="type",
                    details={"message": incoming_message}
                )

            # Get button info
            text = incoming_message.get("text", {})
            if text.get("interactive_type") != "button":
                return ValidationResult.failure(
                    message="Please select an offer using the buttons provided",
                    field="interactive_type",
                    details={"text": text}
                )

            # Get button ID (credex_id)
            button = text.get("button", {})
            credex_id = button.get("id")
            if not credex_id:
                return ValidationResult.failure(
                    message="Invalid offer selection",
                    field="button",
                    details={"button": button}
                )

            # Validate credex_id exists in available offers
            if not self._is_valid_offer(credex_id):
                return ValidationResult.failure(
                    message="Invalid offer selection. Please choose from the available offers.",
                    field="credex_id",
                    details={"credex_id": credex_id}
                )

            # Store selection and allow flow to progress
            self.update_component_data(
                data={"credex_id": credex_id},
                awaiting_input=False
            )
            return ValidationResult.success(None)

        except Exception as e:
            logger.error(f"Error in offer list display: {str(e)}")
            return ValidationResult.failure(
                message=str(e),
                field="offer_list",
                details={
                    "component": self.type,
                    "error": str(e)
                }
            )

    def _display_offers(self) -> ValidationResult:
        """Display offer list with selection buttons"""
        try:
            # Get dashboard data
            dashboard = self.state_manager.get_state_value("dashboard")
            if not dashboard:
                return ValidationResult.failure(
                    message="No dashboard data found",
                    field="dashboard",
                    details={"component": self.type}
                )

            # Get context and offers
            context = self.state_manager.get_path()
            offers = self._get_offers_for_context(context, dashboard)
            if not offers:
                return ValidationResult.failure(
                    message=f"No {context.replace('_', ' ')}s available",
                    field="offers",
                    details={"context": context}
                )

            # Format message
            title = self._get_title_for_context(context)
            message = OFFER_LIST.format(
                title=title,
                offers=self._format_offers(offers)
            )

            # Create buttons for each offer
            buttons = [
                Button(
                    id=str(offer["credexID"]),
                    title=f"{offer['formattedInitialAmount']} - {offer['counterpartyAccountName']}"
                )
                for offer in offers[:3]  # Limit to 3 buttons per message
            ]

            # Send message with buttons
            self.state_manager.messaging.send_interactive(
                body=message,
                buttons=buttons
            )
            self.set_awaiting_input(True)
            return ValidationResult.success(None)

        except Exception as e:
            logger.error(f"Error displaying offers: {str(e)}")
            return ValidationResult.failure(
                message=str(e),
                field="display",
                details={
                    "component": self.type,
                    "error": str(e)
                }
            )

    def _get_offers_for_context(self, context: str, dashboard: Dict) -> List[Dict]:
        """Get relevant offers based on context"""
        if context in {"accept_offer", "decline_offer"}:
            return dashboard.get("incomingOffers", [])
        if context == "cancel_offer":
            return dashboard.get("outgoingOffers", [])
        return []

    def _get_title_for_context(self, context: str) -> str:
        """Get display title based on context"""
        if context in {"accept_offer", "decline_offer"}:
            return "Incoming Offers"
        if context == "cancel_offer":
            return "Outgoing Offers"
        return "Offers"

    def _format_offers(self, offers: List[Dict]) -> str:
        """Format offers for display"""
        return "\n".join(
            OFFER_ITEM.format(
                amount=offer.get("formattedInitialAmount", "Unknown"),
                counterparty=offer.get("counterpartyAccountName", "Unknown"),
                status=offer.get("status", "Unknown"),
                id=offer.get("credexID", "Unknown")
            )
            for offer in offers
        )

    def _is_valid_offer(self, credex_id: str) -> bool:
        """Check if credex_id exists in available offers"""
        try:
            # Get dashboard and context
            dashboard = self.state_manager.get_state_value("dashboard", {})
            context = self.state_manager.get_path()

            # Get relevant offers
            offers = self._get_offers_for_context(context, dashboard)

            # Check if credex_id exists
            return any(str(offer.get("credexID")) == credex_id for offer in offers)

        except Exception as e:
            logger.error(f"Error validating offer: {str(e)}")
            return False

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified offer selection"""
        return {
            "credex_id": value
        }
