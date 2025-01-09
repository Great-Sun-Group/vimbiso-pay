"""Offer list display component

This component handles displaying a list of Credex offers.
"""

from typing import Any, Dict

from core.messaging.templates.messages import ACTION_PROMPT, OFFER_LIST, OFFER_ITEM
from core.utils.error_types import ValidationResult

from ..base import DisplayComponent


class OfferListDisplay(DisplayComponent):
    """Handles displaying a list of Credex offers"""

    def __init__(self):
        super().__init__("offer_list_display")
        self.state_manager = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing offer data"""
        self.state_manager = state_manager

    def validate_display(self, value: Any) -> ValidationResult:
        """Validate display and handle offer selection"""
        # Validate state manager is set
        if not self.state_manager:
            return ValidationResult.failure(
                message="State manager not set",
                field="state_manager",
                details={"component": "offer_list"}
            )

        # If this is an offer selection, validate it
        if isinstance(value, dict) and value.get("type") == "text":
            # Get available offer IDs from state
            dashboard = self.state_manager.get("dashboard")
            if not dashboard:
                return ValidationResult.failure(
                    message="No dashboard data found",
                    field="dashboard",
                    details={"component": "offer_list"}
                )

            # Get context to determine which offers to check
            flow_data = self.state_manager.get_flow_state()
            context = flow_data.get("context") if flow_data else None
            if not context:
                return ValidationResult.failure(
                    message="No context found",
                    field="context",
                    details={"component": "offer_list"}
                )

            # Get valid offer IDs based on context
            if context in {"accept_offers", "decline_offers"}:
                offers = dashboard.get("incomingOffers", [])
            elif context == "cancel_offers":
                offers = dashboard.get("outgoingOffers", [])
            else:
                return ValidationResult.failure(
                    message="Invalid context for offer list",
                    field="context",
                    details={"context": context}
                )

            valid_ids = {str(offer["credexID"]) for offer in offers}
            selection = value.get("text", "").strip()

            if selection in valid_ids:
                # Update state with selection using standard API key
                self.state_manager.update_state({
                    "flow_data": {
                        "data": {"credex_id": selection}
                    }
                })
                return ValidationResult.success({"selection": selection})

            return ValidationResult.failure(
                message="Invalid offer selection. Please choose from the available offers.",
                field="selection",
                details={"component": "offer_list"}
            )

        # Otherwise get and validate dashboard data for display
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

    def to_message_content(self, value: Dict) -> str:
        """Format offer list using templates"""
        # Format each offer using template
        offer_lines = [
            OFFER_ITEM.format(
                amount=offer["amount"],
                counterparty=offer["counterparty"],
                status=offer["status"]
            )
            for offer in value["offers"]
        ]

        # Format complete message using templates
        return OFFER_LIST.format(
            title=value["title"],
            offers="\n".join(offer_lines)
        ) + "\n" + ACTION_PROMPT.format(action_type=value["action"].lower())
