"""Confirm offer secured component

This component handles confirming secured offer creation.
"""

from typing import Any, Dict

from core.error.types import ValidationResult

from . import ConfirmBase


class ConfirmOfferSecured(ConfirmBase):
    """Handles secured offer confirmation"""

    def __init__(self):
        super().__init__("confirm_offer_secured")
        self.state_manager = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing offer data"""
        self.state_manager = state_manager

    def handle_confirmation(self, value: bool) -> ValidationResult:
        """Handle secured offer confirmation"""
        # Validate state manager is set
        if not self.state_manager:
            return ValidationResult.failure(
                message="State manager not set",
                field="state_manager",
                details={"component": "confirm_offer_secured"}
            )

        # Get offer data from component data (components can store their own data in component_data.data)
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

        # Create confirmation result
        result = {
            "confirmed": True,
            "amount": amount,
            "handle": handle
        }

        # Update state with confirmation data
        self.update_state(result, ValidationResult.success(result))
        return ValidationResult.success(result)

    def get_rejection_message(self) -> str:
        """Get message for when offer is rejected"""
        return "Secured offer creation cancelled"

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified confirmation data"""
        return {
            "confirmed": True,
            "amount": value["amount"],
            "handle": value["handle"]
        }
