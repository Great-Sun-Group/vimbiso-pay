"""Offer list display component

This component handles displaying a list of Credex offers and processing offer selection.
"""

import logging
from typing import Any, Dict, List

from core.components.base import InputComponent
from core.error.types import ValidationResult

logger = logging.getLogger(__name__)

# Title templates
TITLES = {
    "process_offer": "*Process An Offer*",  # Default
    "accept_offer": "*Accept An Offer*",
    "decline_offer": "*Decline An Offer*",
    "cancel_offer": "*Cancel An Offer*"
}


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
                    message="Please select an offer from the list provided",
                    field="type",
                    details={"message": incoming_message}
                )

            # Get selection info from interactive message
            interactive = incoming_message.get("interactive", {})
            if interactive.get("type") != "list_reply":
                return ValidationResult.failure(
                    message="Please select an offer from the list provided",
                    field="interactive_type",
                    details={"interactive": interactive}
                )

            # Get selected item ID (credex_id)
            list_reply = interactive.get("list_reply", {})
            credex_id = list_reply.get("id")
            if not credex_id:
                return ValidationResult.failure(
                    message="Invalid offer selection",
                    field="list_reply",
                    details={"list_reply": list_reply}
                )

            # Handle return to dashboard
            if credex_id == "return_to_dashboard":
                # Tell headquarters to return to dashboard
                self.set_result("return_to_dashboard")

                # Release input wait
                self.set_awaiting_input(False)
                return ValidationResult.success(None)

            # Validate credex_id exists in available offers
            if not self._is_valid_offer(credex_id):
                return ValidationResult.failure(
                    message="Invalid offer selection. Please choose from the available offers.",
                    field="credex_id",
                    details={"credex_id": credex_id}
                )

            # Store credex_id
            self.update_data({"credex_id": credex_id})

            # Tell headquarters to process offer
            self.set_result("process_offer")

            # Release input wait
            self.set_awaiting_input(False)
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
            logger.info(f"Dashboard state: {dashboard}")
            if not dashboard:
                return ValidationResult.failure(
                    message="No dashboard data found",
                    field="dashboard",
                    details={"component": self.type}
                )

            # Get context and offers
            context = self.state_manager.get_path()
            offers = self._get_offers_for_context(context, dashboard)
            logger.info(f"Got offers in _display_offers: {offers}")

            # Sort offers chronologically (oldest first)
            if offers and len(offers) > 0:  # Explicitly check length
                sorted_offers = sorted(offers, key=lambda x: x.get("timestamp", "0"))

                # Get context-specific templates
                title = TITLES.get(context, TITLES["process_offer"])

                # Create list message sections
                sections = [
                    {
                        "title": "Available Offers",
                        "rows": []
                    },
                    {
                        "title": "Navigation",
                        "rows": [
                            {
                                "id": "return_to_dashboard",
                                "title": "Return to Dashboard",
                                "description": "Go back to account overview"
                            }
                        ]
                    }
                ]

                # Add offer rows (up to 10)
                for offer in sorted_offers[:10]:
                    direction = "to" if context == "cancel_offer" else "from"

                    # Title shows amount (24 char limit)
                    row_title = f"{offer['formattedInitialAmount']}"

                    # Description shows full details (72 char limit)
                    row_description = f"{direction} {offer['counterpartyAccountName']}"

                    sections[0]["rows"].append({
                        "id": str(offer["credexID"]),
                        "title": row_title,
                        "description": row_description
                    })

                # Send list message using interactive type
                self.state_manager.messaging.send_interactive(
                    body=title,
                    sections=sections,
                    button_text="Select Offer"
                )
                self.set_awaiting_input(True)
                return ValidationResult.success(None)
            else:
                # Send error message for no offers
                error_msg = f"❌ No {context.replace('_', ' ')}s available at this time."
                self.state_manager.messaging.send_text(error_msg)

                # Tell headquarters to return to dashboard
                self.set_result("return_to_dashboard")

                # Release input wait
                self.set_awaiting_input(False)
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
        # Get active account
        active_account_id = self.state_manager.get_state_value("active_account_id")
        if not active_account_id:
            logger.info("No active_account_id found in state")
            return []

        # Find active account
        accounts = dashboard.get("accounts", [])
        active_account = next(
            (acc for acc in accounts if acc.get("accountID") == active_account_id),
            None
        )
        if not active_account:
            logger.info(f"Active account {active_account_id} not found in dashboard accounts")
            return []

        # Get offers based on context
        logger.info(f"Context: {context}")
        logger.info(f"Active account pendingOutData: {active_account.get('pendingOutData')}")

        # Get relevant offers list
        offers = []
        if context in {"process_offer", "accept_offer", "decline_offer"}:
            offers = active_account.get("pendingInData", [])
        if context == "cancel_offer":
            offers = active_account.get("pendingOutData", [])

        logger.info(f"Returning offers for {context}: {offers}")
        return offers

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
