"""Credex-specific message templates"""
from typing import Any, Dict, Optional

from core.messaging.types import (
    Message,
    MessageRecipient,
    TextContent,
    InteractiveContent,
    InteractiveType,
    Button,
    ChannelIdentifier,
    ChannelType
)


class CredexTemplates:
    """Templates for credex-related messages"""

    @staticmethod
    def create_amount_prompt(channel_id: str, member_id: str) -> Message:
        """Create amount prompt message"""
        return Message(
            recipient=MessageRecipient(
                member_id=member_id,
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel_id
                )
            ),
            content=TextContent(
                body="Enter amount:\n\n"
                "Examples:\n"
                "100     (USD)\n"
                "USD 100\n"
                "ZWG 100\n"
                "XAU 1"
            )
        )

    @staticmethod
    def create_handle_prompt(channel_id: str, member_id: str) -> Message:
        """Create handle prompt message"""
        return Message(
            recipient=MessageRecipient(
                member_id=member_id,
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel_id
                )
            ),
            content=TextContent(
                body="Enter recipient handle:"
            )
        )

    @staticmethod
    def create_pending_offers_list(
        channel_id: str,
        data: Dict[str, Any],
        member_id: str
    ) -> Message:
        """Create pending offers list message"""
        flow_type = data.get("flow_type", "cancel")
        current_account = data.get("current_account", {})

        # Get offers from current account
        if flow_type in ["accept", "decline"]:
            offers = current_account.get("pendingInData", [])
            action_text = "accept" if flow_type == "accept" else "decline"
            title = "Incoming Offers"
        else:
            offers = current_account.get("pendingOutData", [])
            action_text = "cancel"
            title = "Outgoing Offers"

        if not offers:
            return Message(
                recipient=MessageRecipient(
                    member_id=member_id,
                    channel_id=ChannelIdentifier(
                        channel=ChannelType.WHATSAPP,
                        value=channel_id
                    )
                ),
                content=TextContent(
                    body=f"No {title.lower()} available"
                )
            )

        rows = []
        for offer in offers:
            # Remove negative sign from amount for display
            amount = offer['formattedInitialAmount'].lstrip('-')
            rows.append({
                "id": f"{flow_type}_{offer['credexID']}",
                "title": f"{amount} {action_text == 'cancel' and 'to' or 'from'} {offer['counterpartyAccountName']}"
            })

        # Ensure sections are properly structured
        sections = [{
            "title": title,
            "rows": [
                {
                    "id": row["id"],
                    "title": row["title"]
                }
                for row in rows
            ]
        }]

        return Message(
            recipient=MessageRecipient(
                member_id=member_id,
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel_id
                )
            ),
            content=InteractiveContent(
                interactive_type=InteractiveType.LIST,
                body=f"Select an offer to {action_text}:",
                action_items={
                    "button": "🕹️ Options",
                    "sections": sections
                }
            )
        )

    @staticmethod
    def create_offer_confirmation(
        channel_id: str,
        amount: str,
        handle: str,
        name: str,
        member_id: str
    ) -> Message:
        """Create offer confirmation message"""
        return Message(
            recipient=MessageRecipient(
                member_id=member_id,
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel_id
                )
            ),
            content=InteractiveContent(
                interactive_type=InteractiveType.BUTTON,
                body=(
                    f"Confirm transaction:\n\n"
                    f"Amount: {amount}\n"
                    f"To: {name} ({handle})"
                ),
                buttons=[
                    Button(id="confirm_action", title="Confirm")
                ]
            )
        )

    @staticmethod
    def create_cancel_confirmation(
        channel_id: str,
        amount: str,
        counterparty: str,
        member_id: str
    ) -> Message:
        """Create cancel confirmation message"""
        return Message(
            recipient=MessageRecipient(
                member_id=member_id,
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel_id
                )
            ),
            content=InteractiveContent(
                interactive_type=InteractiveType.BUTTON,
                body=(
                    f"Cancel Credex Offer\n\n"
                    f"Amount: {amount}\n"
                    f"To: {counterparty}"
                ),
                buttons=[
                    Button(id="confirm_action", title="Cancel Offer")
                ]
            )
        )

    @staticmethod
    def create_action_confirmation(
        channel_id: str,
        amount: str,
        counterparty: str,
        action: str,
        member_id: str
    ) -> Message:
        """Create action confirmation message"""
        return Message(
            recipient=MessageRecipient(
                member_id=member_id,
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel_id
                )
            ),
            content=InteractiveContent(
                interactive_type=InteractiveType.BUTTON,
                body=(
                    f"{action} credex offer\n\n"
                    f"Amount: {amount}\n"
                    f"From: {counterparty}"
                ),
                buttons=[
                    Button(id="confirm_action", title="Confirm")
                ]
            )
        )

    @staticmethod
    def create_error_message(channel_id: str, error: str, member_id: Optional[str] = None) -> Message:
        """Create error message"""
        return Message(
            recipient=MessageRecipient(
                member_id=member_id or "pending",
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel_id
                )
            ),
            content=TextContent(
                body=f"❌ {error}"
            )
        )

    @staticmethod
    def create_success_message(channel_id: str, message: str, member_id: str) -> Message:
        """Create success message"""
        return Message(
            recipient=MessageRecipient(
                member_id=member_id,
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel_id
                )
            ),
            content=TextContent(
                body=f"✅ {message}"
            )
        )
