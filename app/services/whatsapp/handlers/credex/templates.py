"""Credex-specific message templates"""
from typing import List, Dict, Any

from ...types import WhatsAppMessage


class CredexTemplates:
    """Templates for credex-related messages"""

    @staticmethod
    def create_amount_prompt(recipient: str) -> dict:
        """Create amount prompt message"""
        return WhatsAppMessage.create_text(
            recipient,
            "Enter amount:\n\n"
            "Examples:\n"
            "100     (USD)\n"
            "USD 100\n"
            "ZWG 100\n"
            "XAU 1"
        )

    @staticmethod
    def create_handle_prompt(recipient: str) -> dict:
        """Create handle prompt message"""
        return WhatsAppMessage.create_text(
            recipient,
            "Enter recipient handle:"
        )

    @staticmethod
    def create_pending_offers_list(
        recipient: str,
        pending_offers: List[Dict[str, Any]]
    ) -> dict:
        """Create pending offers list message"""
        rows = [
            {
                "id": f"cancel_{offer['id']}",
                "title": f"{offer['amount']} to {offer['to']}"
            }
            for offer in pending_offers
        ]

        return WhatsAppMessage.create_list(
            recipient,
            "Select an offer to cancel:",
            "🕹️ Options",
            [{
                "title": "Pending Offers",
                "rows": rows
            }]
        )

    @staticmethod
    def create_offer_confirmation(
        recipient: str,
        amount: str,
        handle: str,
        name: str
    ) -> dict:
        """Create offer confirmation message"""
        text = (
            f"Confirm transaction:\n\n"
            f"Amount: {amount}\n"
            f"To: {name} ({handle})"
        )

        return WhatsAppMessage.create_button(
            recipient,
            text,
            [{"id": "confirm_action", "title": "Confirm"}]
        )

    @staticmethod
    def create_cancel_confirmation(
        recipient: str,
        amount: str,
        counterparty: str
    ) -> dict:
        """Create cancel confirmation message"""
        text = (
            f"Cancel Credex Offer\n\n"
            f"Amount: {amount}\n"
            f"To: {counterparty}"
        )

        return WhatsAppMessage.create_button(
            recipient,
            text,
            [{"id": "confirm_action", "title": "Cancel Offer"}]
        )

    @staticmethod
    def create_action_confirmation(
        recipient: str,
        amount: str,
        counterparty: str,
        action: str
    ) -> dict:
        """Create action confirmation message"""
        text = (
            f"{action} credex offer\n\n"
            f"Amount: {amount}\n"
            f"From: {counterparty}"
        )

        return WhatsAppMessage.create_button(
            recipient,
            text,
            [{"id": "confirm_action", "title": "Confirm"}]
        )

    @staticmethod
    def create_error_message(recipient: str, error: str) -> dict:
        """Create error message"""
        return WhatsAppMessage.create_text(
            recipient,
            f"❌ {error}"
        )

    @staticmethod
    def create_success_message(recipient: str, message: str) -> dict:
        """Create success message"""
        return WhatsAppMessage.create_text(
            recipient,
            f"✅ {message}"
        )
