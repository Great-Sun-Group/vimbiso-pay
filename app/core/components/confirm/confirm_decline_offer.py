"""Confirm decline offer component

This component handles confirming offer decline:
- Gets offer details from component_data
- Shows confirmation with offer details
- Handles confirmation button interaction
"""

import logging
from typing import Any, Dict

from core.error.exceptions import ComponentException
from core.error.types import ValidationResult
from core.messaging.types import Button

from . import ConfirmBase

logger = logging.getLogger(__name__)

# Decline confirmation template
DECLINE_CONFIRMATION = """📝 *Review Offer to Decline*

💰 Amount: {amount}
👤 From: {counterparty}
💳 Account: {account_handle}
🆔 ID: {credex_id}"""


class ConfirmDeclineOffer(ConfirmBase):
    """Handles offer decline confirmation"""

    def __init__(self):
        super().__init__("confirm_decline_offer")

    def validate(self, value: Any) -> ValidationResult:
        """Override parent validate to handle confirmation flow"""
        # Get current state
        current_data = self.state_manager.get_state_value("component_data", {})
        awaiting_input = current_data.get("awaiting_input", False)

        # Initial activation - let parent handle it only if not already awaiting input
        if value is None and not awaiting_input:
            return super().validate(value)

        # Process confirmation if we have an incoming message
        if current_data.get("incoming_message"):
            # Process the confirmation
            return self.handle_confirmation(value)

        # Already awaiting input but no message to process
        return ValidationResult.success(None)

    def _send(self) -> None:
        """Send confirmation message with buttons"""
        logger.info("Preparing decline confirmation message")

        try:
            # Get offer data from component_data.data
            logger.debug("Getting offer details from component data")
            offer_data = self.state_manager.get_state_value("component_data", {}).get("data", {})
            credex_id = offer_data.get("credex_id")

            if not credex_id:
                raise ComponentException(
                    message="Missing credex ID",
                    component=self.type,
                    field="credex_id",
                    value=str(offer_data)
                )

            # Get offer details from dashboard
            logger.debug("Getting offer details from dashboard")
            dashboard = self.state_manager.get_state_value("dashboard", {})
            incoming_offers = dashboard.get("incomingOffers", [])
            offer = next(
                (o for o in incoming_offers if str(o.get("credexID")) == str(credex_id)),
                None
            )

            if not offer:
                raise ComponentException(
                    message="Offer not found in dashboard",
                    component=self.type,
                    field="offer",
                    value=str(credex_id)
                )

            # Format confirmation message
            logger.debug("Formatting confirmation message")
            confirmation_message = DECLINE_CONFIRMATION.format(
                amount=offer.get("formattedInitialAmount", "Unknown"),
                counterparty=offer.get("counterpartyAccountName", "Unknown"),
                account_handle=offer.get("counterpartyAccountHandle", "Unknown"),
                credex_id=credex_id
            )

            # Send message with buttons
            self.state_manager.messaging.send_interactive(
                body=confirmation_message,
                buttons=[
                    Button(id="confirm", title="📝 Confirm Decline 💸"),
                    Button(id="cancel", title="❌ Keep Offer ❌")
                ]
            )
            self.set_awaiting_input(True)

        except Exception as e:
            logger.error(f"Error preparing confirmation: {str(e)}")
            raise ComponentException(
                message=f"Failed to prepare confirmation: {str(e)}",
                component=self.type,
                field="confirmation",
                value=str(e)
            )

    def handle_confirmation(self, value: bool) -> ValidationResult:
        """Handle offer decline confirmation"""
        logger.info("Processing decline confirmation")

        try:
            # Get current state
            current_data = self.state_manager.get_state_value("component_data", {})
            incoming_message = current_data.get("incoming_message", {})

            # Validate interactive message
            if incoming_message.get("type") != "interactive":
                return ValidationResult.failure(
                    message="Please use the Confirm or Cancel button",
                    field="type",
                    details={"message": incoming_message}
                )

            # Get button info
            text = incoming_message.get("text", {})
            if text.get("interactive_type") != "button":
                return ValidationResult.failure(
                    message="Please use the Confirm or Cancel button",
                    field="interactive_type",
                    details={"text": text}
                )

            # Check button ID
            button = text.get("button", {})
            button_id = button.get("id")

            logger.debug(f"Button ID: {button_id}")
            if button_id == "cancel":
                logger.info("Decline rejected")
                self.update_component_data(
                    data={"confirmed": False},
                    awaiting_input=False
                )
                return ValidationResult.success({"confirmed": False})

            if button_id != "confirm":
                return ValidationResult.failure(
                    message="Please use the Confirm or Cancel button",
                    field="button",
                    details={"button": button}
                )

            # Add confirmation status
            logger.info("Decline confirmed")
            self.update_component_data(
                data={"confirmed": True},
                awaiting_input=False
            )
            return ValidationResult.success({"confirmed": True})

        except Exception as e:
            logger.error(f"Error processing confirmation: {str(e)}")
            return ValidationResult.failure(
                message=str(e),
                field="confirmation",
                details={
                    "component": self.type,
                    "error": str(e)
                }
            )

    def get_rejection_message(self) -> str:
        """Get message for when decline is rejected"""
        return "Offer decline cancelled"

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified confirmation data"""
        return {
            "confirmed": value.get("confirmed", False)
        }
