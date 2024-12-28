"""Auth display handler enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any

from core.messaging.types import (
    ChannelIdentifier, Message, MessageRecipient, TextContent
)

logger = logging.getLogger(__name__)


def handle_registration_display(state_manager: Any) -> Message:
    """Display registration prompt"""
    # Get channel info from state
    channel = state_manager.get("channel", {})

    # Return registration message
    return Message(
        recipient=MessageRecipient(
            channel_id=ChannelIdentifier(
                channel=channel.get("type"),
                value=channel.get("identifier")
            )
        ),
        content=TextContent(
            text="Welcome to VimbisoPay! Please register to continue.\n\n"
                 "Reply with your phone number to start."
        )
    )
