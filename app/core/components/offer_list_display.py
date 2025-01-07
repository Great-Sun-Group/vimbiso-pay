"""Offer list display component

This component handles displaying a list of Credex offers.
"""

from typing import Any, Dict

from core.utils.error_types import ValidationResult

from .base import Component


class OfferListDisplay(Component):
    """Handles displaying a list of Credex offers"""

    def __init__(self):
        super().__init__("offer_list_display")
        self.state_manager = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing offer data"""
        self.state_manager = state_manager

    def validate(self, value: Any) -> ValidationResult:
        """Validate and format offer data for display"""
        # Validate state manager is set
        if not self.state_manager:
            return ValidationResult.failure(
                message="State manager not set",
                field="state_manager",
                details={"component": "offer_list"}
            )

        # Get dashboard data from state
        dashboard = self.state_manager.get("dashboard")
        if not dashboard:
            return ValidationResult.failure(
                message="No dashboard data found",
                field="dashboard",
                details={"component": "offer_list"}
            )

        # Get offers based on context
        flow_data = self.state_manager.get_flow_state()
        if not flow_data:
            return ValidationResult.failure(
                message="No flow data found",
                field="flow_data",
                details={"component": "offer_list"}
            )

        context = flow_data.get("context")
        if not context:
            return ValidationResult.failure(
                message="No context found",
                field="context",
                details={"component": "offer_list"}
            )

        # Get relevant offers based on context
        if context == "accept_offers":
            offers = dashboard.get("incomingOffers", [])
            title = "Incoming Offers"
            action = "Accept"
        elif context == "decline_offers":
            offers = dashboard.get("incomingOffers", [])
            title = "Incoming Offers"
            action = "Decline"
        elif context == "cancel_offers":
            offers = dashboard.get("outgoingOffers", [])
            title = "Outgoing Offers"
            action = "Cancel"
        else:
            return ValidationResult.failure(
                message="Invalid context for offer list",
                field="context",
                details={"context": context}
            )

        if not offers:
            return ValidationResult.failure(
                message="No offers found",
                field="offers",
                details={"context": context}
            )

        # Format offers for display
        formatted_offers = []
        for offer in offers:
            formatted_offers.append({
                "credex_id": offer.get("credexID"),
                "amount": offer.get("formattedInitialAmount"),
                "counterparty": offer.get("counterpartyAccountName"),
                "status": offer.get("status")
            })

        return ValidationResult.success({
            "title": title,
            "action": action,
            "offers": formatted_offers
        })

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified display data"""
        return {
            "title": value["title"],
            "action": value["action"],
            "offers": value["offers"],
            "use_list": True  # Signal to use list format
        }
