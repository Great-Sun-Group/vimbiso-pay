"""Core messaging utilities"""

from typing import Any

from core.messaging.types import ChannelIdentifier, ChannelType, MessageRecipient


def get_recipient(state_manager: Any) -> MessageRecipient:
    """Get message recipient from state

    Args:
        state_manager: State manager instance

    Returns:
        MessageRecipient: Message recipient with channel info
    """
    channel_data = state_manager.get("channel") or {}
    return MessageRecipient(
        channel_id=ChannelIdentifier(
            channel=ChannelType(channel_data.get("type", "whatsapp")),
            value=channel_data.get("identifier")
        )
    )
