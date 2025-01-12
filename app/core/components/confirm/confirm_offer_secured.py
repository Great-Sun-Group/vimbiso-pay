"""Confirm offer secured component

This component handles confirming secured offer creation:
- Gets offer details from component_data
- Gets target account from action state
- Gets active account from dashboard state
- Shows confirmation with both account details
"""

import logging
from typing import Any, Dict

from core.error.exceptions import ComponentException
from core.error.types import ValidationResult

from . import ConfirmBase

# Offer confirmation template
OFFER_CONFIRMATION = """📝 *Digitally sign your offer:*
💸 Amount: *{amount}*
💳 From: *{active_account_name}* {active_account_handle}
💳 To: *{input_account_name}* {input_account_handle}"""


class ConfirmOfferSecured(ConfirmBase):
    """Handles secured offer confirmation"""

    def __init__(self):
        super().__init__("confirm_offer_secured")
        self.state_manager = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing offer data"""
        self.state_manager = state_manager

    def _validate(self, value: Any) -> ValidationResult:
        """Validate confirmation input or handle initial activation"""
        # Get current state
        current_data = self.state_manager.get_state_value("component_data", {})

        # Initial activation - send confirmation message
        if not current_data.get("awaiting_input"):
            self.send()
            return ValidationResult.success(None)

        # Process confirmation response
        return self.handle_confirmation(value)

    def _send(self) -> None:
        """Send confirmation message with buttons"""
        logger = logging.getLogger(__name__)
        logger.info("Preparing confirmation message")

        # Get offer data
        logger.debug("Getting offer details from component data")
        offer_data = self.state_manager.get_state_value("component_data", {})
        amount = offer_data.get("amount")
        handle = offer_data.get("handle")

        if not amount or not handle:
            raise ComponentException(
                message="Missing offer details",
                component=self.type,
                field="offer_data",
                value=str(offer_data)
            )

        # Get target account details from action state
        logger.debug("Getting target account from action state")
        action = self.state_manager.get_state_value("action", {})
        target_account = action.get("details", {})

        # Get active account details from dashboard state
        logger.debug("Getting active account from dashboard state")
        dashboard = self.state_manager.get_state_value("dashboard", {})
        active_account_id = self.state_manager.get_state_value("active_account_id")
        active_account = next(
            (acc for acc in dashboard.get("accounts", [])
             if acc.get("accountID") == active_account_id),
            {}
        )

        # Format and send confirmation message
        logger.debug(
            f"Sending confirmation for amount {amount} from "
            f"{active_account.get('accountName')} to {target_account.get('accountName')}"
        )
        confirmation_message = OFFER_CONFIRMATION.format(
            amount=amount,
            active_account_name=active_account.get("accountName", ""),
            active_account_handle=active_account.get("accountHandle", ""),
            input_account_name=target_account.get("accountName", ""),
            input_account_handle=handle
        )

        self.state_manager.messaging.send_interactive(
            body=confirmation_message,
            buttons=[
                {"id": "confirm", "title": "✅ Confirm"},
                {"id": "cancel", "title": "❌ Cancel"}
            ]
        )
        self.set_awaiting_input(True)

    def handle_confirmation(self, value: bool) -> ValidationResult:
        """Handle secured offer confirmation"""
        logger = logging.getLogger(__name__)
        logger.info("Processing confirmation response")

        # Validate state manager is set
        logger.debug("Checking state manager")
        if not self.state_manager:
            return ValidationResult.failure(
                message="State manager not set",
                field="state_manager",
                details={"component": "confirm_offer_secured"}
            )

        # Get offer data from component data
        logger.debug("Getting offer data from component data")
        offer_data = self.state_manager.get_state_value("component_data", {})
        if not offer_data:
            return ValidationResult.failure(
                message="No offer data found",
                field="component_data",
                details={"component": "confirm_offer_secured"}
            )
        amount = offer_data.get("amount")
        handle = offer_data.get("handle")

        if not amount or not handle:
            return ValidationResult.failure(
                message="Missing offer details",
                field="offer_data",
                details={
                    "missing_fields": [
                        "amount" if not amount else None,
                        "handle" if not handle else None
                    ]
                }
            )

        # Get current state
        current_data = self.state_manager.get_state_value("component_data", {})

        # Process button response
        logger.debug("Processing button response")
        incoming_message = current_data.get("incoming_message", {})
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
            logger.info("Offer cancelled")
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
        logger.info("Offer confirmed")
        self.update_component_data(
            data={"confirmed": True},
            awaiting_input=False
        )
        return ValidationResult.success({"confirmed": True})

    def get_rejection_message(self) -> str:
        """Get message for when offer is rejected"""
        return "Secured offer creation cancelled"

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified confirmation data"""
        return {
            "confirmed": value.get("confirmed", False)
        }
