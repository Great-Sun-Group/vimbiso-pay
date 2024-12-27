"""Credex-specific message templates enforcing SINGLE SOURCE OF TRUTH"""
import logging
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
from core.utils.state_validator import StateValidator

logger = logging.getLogger(__name__)


class CredexTemplates:
    """Templates for credex-related messages with strict state validation"""

    @staticmethod
    def create_amount_prompt(channel_id: str, state_manager: Any) -> Message:
        """Create amount prompt message using state manager"""
        try:
            # Validate state access at boundary
            validation = StateValidator.validate_before_access(
                {
                    "channel": state_manager.get("channel"),
                    "member_id": state_manager.get("member_id")
                },
                {"channel", "member_id"}
            )
            if not validation.is_valid:
                raise ValueError(validation.error_message)

            member_id = state_manager.get("member_id")
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
        except ValueError as e:
            return CredexTemplates.create_error_message(channel_id, str(e))

    @staticmethod
    def create_handle_prompt(channel_id: str, state_manager: Any) -> Message:
        """Create handle prompt message using state manager"""
        try:
            # Validate state access at boundary
            validation = StateValidator.validate_before_access(
                {
                    "channel": state_manager.get("channel"),
                    "member_id": state_manager.get("member_id")
                },
                {"channel", "member_id"}
            )
            if not validation.is_valid:
                raise ValueError(validation.error_message)

            member_id = state_manager.get("member_id")
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
        except ValueError as e:
            return CredexTemplates.create_error_message(channel_id, str(e))

    @staticmethod
    def create_pending_offers_list(
        channel_id: str,
        data: Dict[str, Any],
        state_manager: Any
    ) -> Message:
        """Create pending offers list message"""
        try:
            # Validate state access at boundary
            validation = StateValidator.validate_before_access(
                {
                    "channel": state_manager.get("channel"),
                    "member_id": state_manager.get("member_id")
                },
                {"channel", "member_id"}
            )
            if not validation.is_valid:
                raise ValueError(validation.error_message)

            member_id = state_manager.get("member_id")
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
        except ValueError as e:
            return CredexTemplates.create_error_message(channel_id, str(e))

    @staticmethod
    def create_offer_confirmation(
        channel_id: str,
        amount: str,
        handle: str,
        name: str,
        state_manager: Any
    ) -> Message:
        """Create offer confirmation message"""
        try:
            # Validate state access at boundary
            validation = StateValidator.validate_before_access(
                {
                    "channel": state_manager.get("channel"),
                    "member_id": state_manager.get("member_id")
                },
                {"channel", "member_id"}
            )
            if not validation.is_valid:
                raise ValueError(validation.error_message)

            member_id = state_manager.get("member_id")
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
        except ValueError as e:
            return CredexTemplates.create_error_message(channel_id, str(e))

    @staticmethod
    def create_cancel_confirmation(
        channel_id: str,
        amount: str,
        counterparty: str,
        state_manager: Any
    ) -> Message:
        """Create cancel confirmation message"""
        try:
            # Validate state access at boundary
            validation = StateValidator.validate_before_access(
                {
                    "channel": state_manager.get("channel"),
                    "member_id": state_manager.get("member_id")
                },
                {"channel", "member_id"}
            )
            if not validation.is_valid:
                raise ValueError(validation.error_message)

            member_id = state_manager.get("member_id")
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
        except ValueError as e:
            return CredexTemplates.create_error_message(channel_id, str(e))

    @staticmethod
    def create_action_confirmation(
        channel_id: str,
        amount: str,
        counterparty: str,
        action: str,
        state_manager: Any
    ) -> Message:
        """Create action confirmation message"""
        try:
            # Validate state access at boundary
            validation = StateValidator.validate_before_access(
                {
                    "channel": state_manager.get("channel"),
                    "member_id": state_manager.get("member_id")
                },
                {"channel", "member_id"}
            )
            if not validation.is_valid:
                raise ValueError(validation.error_message)

            member_id = state_manager.get("member_id")
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
        except ValueError as e:
            return CredexTemplates.create_error_message(channel_id, str(e))

    @staticmethod
    def create_success_message(channel_id: str, message: str, state_manager: Any) -> Message:
        """Create success message"""
        try:
            # Validate state access at boundary
            validation = StateValidator.validate_before_access(
                {
                    "channel": state_manager.get("channel"),
                    "member_id": state_manager.get("member_id")
                },
                {"channel", "member_id"}
            )
            if not validation.is_valid:
                raise ValueError(validation.error_message)

            member_id = state_manager.get("member_id")
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
        except ValueError as e:
            return CredexTemplates.create_error_message(channel_id, str(e))

    @staticmethod
    def create_error_message(channel_id: str, error: str, state_manager: Optional[Any] = None) -> Message:
        """Create error message enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate input parameters
            if not channel_id:
                raise ValueError("Channel ID is required")
            if not error:
                raise ValueError("Error message is required")

            member_id = "pending"
            if state_manager:
                try:
                    # Validate ALL required state at boundary
                    required_fields = {"channel", "member_id"}
                    current_state = {
                        field: state_manager.get(field)
                        for field in required_fields
                    }

                    # Validate state access
                    validation = StateValidator.validate_before_access(
                        current_state,
                        {"channel", "member_id"}
                    )
                    if validation.is_valid:
                        # Get member ID (SINGLE SOURCE OF TRUTH)
                        member_id = state_manager.get("member_id")
                        if not member_id:
                            raise ValueError("Member ID not found")

                        # Get channel info (SINGLE SOURCE OF TRUTH)
                        channel = state_manager.get("channel")
                        if not channel or not channel.get("identifier"):
                            raise ValueError("Channel identifier not found")

                        # Log error creation
                        logger.info(f"Creating error message for channel {channel['identifier']}")
                    else:
                        logger.warning(f"Invalid state access: {validation.error_message}")
                except ValueError as err:
                    logger.warning(f"State validation failed: {str(err)}")
                except Exception as err:
                    logger.error(f"Unexpected error accessing state: {str(err)}")

            # Create error message
            return Message(
                recipient=MessageRecipient(
                    member_id=member_id,
                    channel_id=ChannelIdentifier(
                        channel=ChannelType.WHATSAPP,
                        value=channel_id
                    )
                ),
                content=TextContent(
                    body="❌ Error: Unable to process request. Please try again."
                )
            )

        except ValueError as e:
            logger.error(f"Failed to create error message: {str(e)} for channel {channel_id}")
            return Message(
                recipient=MessageRecipient(
                    member_id="unknown",
                    channel_id=ChannelIdentifier(
                        channel=ChannelType.WHATSAPP,
                        value=channel_id
                    )
                ),
                content=TextContent(
                    body="❌ Critical Error: System temporarily unavailable"
                )
            )
