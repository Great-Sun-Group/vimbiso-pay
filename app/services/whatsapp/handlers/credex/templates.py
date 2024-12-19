"""Credex-specific message templates"""
from typing import List, Dict, Any

from core.messaging.types import (
    Message,
    MessageRecipient,
    TextContent,
    InteractiveContent,
    InteractiveType,
    Button
)


class CredexTemplates:
    """Templates for credex-related messages"""

    @staticmethod
    def create_amount_prompt(recipient: str) -> Message:
        """Create amount prompt message"""
        return Message(
            recipient=MessageRecipient(phone_number=recipient),
            content=TextContent(
                body=(
                    "Enter amount:\n\n"
                    "Examples:\n"
                    "100     (USD)\n"
                    "USD 100\n"
                    "ZWG 100\n"
                    "XAU 1"
                )
            )
        )

    @staticmethod
    def create_handle_prompt(recipient: str) -> Message:
        """Create handle prompt message"""
        return Message(
            recipient=MessageRecipient(phone_number=recipient),
            content=TextContent(body="Enter recipient handle:")
        )

    @staticmethod
    def create_pending_offers_list(
        recipient: str,
        pending_offers: List[Dict[str, Any]]
    ) -> Message:
        """Create pending offers list message"""
        rows = [
            {
                "id": f"cancel_{offer['id']}",
                "title": f"{offer['amount']} to {offer['to']}"
            }
            for offer in pending_offers
        ]

        return Message(
            recipient=MessageRecipient(phone_number=recipient),
            content=InteractiveContent(
                interactive_type=InteractiveType.LIST,
                body="Select an offer to cancel:",
                action_items={
                    "button": "🕹️ Options",
                    "sections": [{
                        "title": "Pending Offers",
                        "rows": rows
                    }]
                }
            )
        )

    @staticmethod
    def create_offer_confirmation(
        recipient: str,
        amount: str,
        handle: str,
        name: str
    ) -> Message:
        """Create offer confirmation message"""
        text = (
            f"Confirm transaction:\n\n"
            f"Amount: {amount}\n"
            f"To: {name} ({handle})"
        )

        return Message(
            recipient=MessageRecipient(phone_number=recipient),
            content=InteractiveContent(
                interactive_type=InteractiveType.BUTTON,
                body=text,
                buttons=[
                    Button(id="confirm_action", title="Confirm")
                ]
            )
        )

    @staticmethod
    def create_cancel_confirmation(
        recipient: str,
        amount: str,
        counterparty: str
    ) -> Message:
        """Create cancel confirmation message"""
        text = (
            f"Cancel Credex Offer\n\n"
            f"Amount: {amount}\n"
            f"To: {counterparty}"
        )

        return Message(
            recipient=MessageRecipient(phone_number=recipient),
            content=InteractiveContent(
                interactive_type=InteractiveType.BUTTON,
                body=text,
                buttons=[
                    Button(id="confirm_action", title="Cancel Offer")
                ]
            )
        )

    @staticmethod
    def create_action_confirmation(
        recipient: str,
        amount: str,
        counterparty: str,
        action: str
    ) -> Message:
        """Create action confirmation message"""
        text = (
            f"{action} credex offer\n\n"
            f"Amount: {amount}\n"
            f"From: {counterparty}"
        )

        return Message(
            recipient=MessageRecipient(phone_number=recipient),
            content=InteractiveContent(
                interactive_type=InteractiveType.BUTTON,
                body=text,
                buttons=[
                    Button(id="confirm_action", title="Confirm")
                ]
            )
        )

    @staticmethod
    def create_error_message(recipient: str, error: str) -> Message:
        """Create error message"""
        return Message(
            recipient=MessageRecipient(phone_number=recipient),
            content=TextContent(body=f"❌ {error}")
        )

    @staticmethod
    def create_success_message(recipient: str, message: str) -> Message:
        """Create success message"""
        return Message(
            recipient=MessageRecipient(phone_number=recipient),
            content=TextContent(body=f"✅ {message}")
        )
