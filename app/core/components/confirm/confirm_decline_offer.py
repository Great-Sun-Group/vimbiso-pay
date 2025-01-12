"""Confirm decline offer component

This component handles confirming offer decline action.
"""

from typing import Any, Dict

from core.error.types import ValidationResult
from . import ConfirmBase


# Decline confirmation template
DECLINE_CONFIRMATION = """📝 Review offer to decline:
💸 Amount: {amount}
💳 From: {counterparty}"""


class ConfirmDeclineOffer(ConfirmBase):
    """Handles offer decline confirmation"""

    def __init__(self):
        super().__init__("confirm_decline_offer")
        self.state_manager = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing offer data"""
        self.state_manager = state_manager

    def handle_confirmation(self, value: bool) -> ValidationResult:
        """Handle offer decline confirmation"""
        # Validate state manager is set
        if not self.state_manager:
            return ValidationResult.failure(
                message="State manager not set",
                field="state_manager",
                details={"component": "confirm_decline_offer"}
            )

        # Get offer data from component data (components can store their own data in component_data.data)
        offer_data = self.state_manager.get_state_value("component_data", {})
        if not offer_data:
            return ValidationResult.failure(
                message="No offer data found",
                field="component_data",
                details={"component": "confirm_decline_offer"}
            )
        credex_id = offer_data.get("credex_id")
        amount = offer_data.get("amount")
        counterparty = offer_data.get("counterparty")

        if not all([credex_id, amount, counterparty]):
            return ValidationResult.failure(
                message="Missing offer details",
                field="offer_data",
                details={
                    "missing_fields": [
                        "credex_id" if not credex_id else None,
                        "amount" if not amount else None,
                        "counterparty" if not counterparty else None
                    ]
                }
            )

        # Create confirmation result
        result = {
            "confirmed": True,
            "credex_id": credex_id,
            "amount": amount,
            "counterparty": counterparty
        }

        # Update state with confirmation data
        self.update_state(result, ValidationResult.success(result))
        return ValidationResult.success(result)

    def get_rejection_message(self) -> str:
        """Get message for when decline is rejected"""
        return "Offer decline cancelled"

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified confirmation data"""
        return {
            "confirmed": True,
            "credex_id": value["credex_id"],
            "amount": value["amount"],
            "counterparty": value["counterparty"]
        }
