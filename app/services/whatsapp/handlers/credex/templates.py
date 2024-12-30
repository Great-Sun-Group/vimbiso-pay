"""Credex-specific message templates enforcing SINGLE SOURCE OF TRUTH"""
from typing import Any, Dict

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
from core.utils.error_handler import error_decorator


class CredexTemplates:
    """Templates for credex-related messages with strict state validation"""

    @staticmethod
    @error_decorator
    def create_amount_prompt(state_manager: Any) -> Message:
        """Create amount prompt message using state manager"""
        # Update state to trigger validation
        state_manager.update_state({
            "flow_data": {
                "current_step": "amount",
                "step": 1
            }
        })

        # Get validated state
        channel = state_manager.get("channel")
        member_id = state_manager.get("member_id")

        return Message(
            recipient=MessageRecipient(
                member_id=member_id,
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel["identifier"]
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
    @error_decorator
    def create_handle_prompt(state_manager: Any) -> Message:
        """Create handle prompt message using state manager"""
        # Update state to trigger validation
        state_manager.update_state({
            "flow_data": {
                "current_step": "handle",
                "step": 2
            }
        })

        # Get validated state
        channel = state_manager.get("channel")
        member_id = state_manager.get("member_id")

        return Message(
            recipient=MessageRecipient(
                member_id=member_id,
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel["identifier"]
                )
            ),
            content=TextContent(
                body="Enter recipient handle:"
            )
        )

    @staticmethod
    @error_decorator
    def create_pending_offers_list(state_manager: Any, data: Dict[str, Any]) -> Message:
        """Create pending offers list message"""
        # Update state to trigger validation
        state_manager.update_state({
            "flow_data": {
                "current_step": "list",
                "step": 1,
                "data": data
            }
        })

        # Get validated state
        channel = state_manager.get("channel")
        member_id = state_manager.get("member_id")
        flow_data = state_manager.get("flow_data")
        flow_type = flow_data["data"].get("flow_type", "cancel")
        current_account = flow_data["data"].get("current_account", {})

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
                        value=channel["identifier"]
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
                    value=channel["identifier"]
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
    @error_decorator
    def create_offer_confirmation(state_manager: Any, amount: str, handle: str, name: str) -> Message:
        """Create offer confirmation message"""
        # Update state to trigger validation
        state_manager.update_state({
            "flow_data": {
                "current_step": "confirm",
                "step": 3,
                "data": {
                    "amount": amount,
                    "handle": handle,
                    "name": name
                }
            }
        })

        # Get validated state
        channel = state_manager.get("channel")
        member_id = state_manager.get("member_id")

        return Message(
            recipient=MessageRecipient(
                member_id=member_id,
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel["identifier"]
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
    @error_decorator
    def create_cancel_confirmation(state_manager: Any, amount: str, counterparty: str) -> Message:
        """Create cancel confirmation message"""
        # Update state to trigger validation
        state_manager.update_state({
            "flow_data": {
                "current_step": "confirm_cancel",
                "step": 2,
                "data": {
                    "amount": amount,
                    "counterparty": counterparty
                }
            }
        })

        # Get validated state
        channel = state_manager.get("channel")
        member_id = state_manager.get("member_id")

        return Message(
            recipient=MessageRecipient(
                member_id=member_id,
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel["identifier"]
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
    @error_decorator
    def create_action_confirmation(state_manager: Any, amount: str, counterparty: str, action: str) -> Message:
        """Create action confirmation message"""
        # Update state to trigger validation
        state_manager.update_state({
            "flow_data": {
                "current_step": "confirm_action",
                "step": 2,
                "data": {
                    "amount": amount,
                    "counterparty": counterparty,
                    "action": action
                }
            }
        })

        # Get validated state
        channel = state_manager.get("channel")
        member_id = state_manager.get("member_id")

        return Message(
            recipient=MessageRecipient(
                member_id=member_id,
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel["identifier"]
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
    @error_decorator
    def create_success_message(state_manager: Any, message: str) -> Message:
        """Create success message"""
        # Update state to trigger validation
        state_manager.update_state({
            "flow_data": {
                "current_step": "success",
                "step": 4,
                "data": {
                    "message": message
                }
            }
        })

        # Get validated state
        channel = state_manager.get("channel")
        member_id = state_manager.get("member_id")

        return Message(
            recipient=MessageRecipient(
                member_id=member_id,
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel["identifier"]
                )
            ),
            content=TextContent(
                body=f"✅ {message}"
            )
        )

    @staticmethod
    @error_decorator
    def create_error_message(state_manager: Any, error: str) -> Message:
        """Create error message enforcing SINGLE SOURCE OF TRUTH"""
        # Update state to trigger validation
        state_manager.update_state({
            "flow_data": {
                "current_step": "error",
                "step": 0,
                "data": {
                    "error": error
                }
            }
        })

        # Get validated state
        channel = state_manager.get("channel")
        member_id = state_manager.get("member_id")

        return Message(
            recipient=MessageRecipient(
                member_id=member_id,
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel["identifier"]
                )
            ),
            content=TextContent(
                body=f"❌ {error}"
            )
        )
