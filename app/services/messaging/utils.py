"""Shared utilities for messaging services"""
from typing import Any
from core.messaging.types import ChannelIdentifier, ChannelType, MessageRecipient


def get_recipient(state_manager: Any) -> MessageRecipient:
    """Get message recipient from state with validation"""
    return MessageRecipient(
        channel_id=ChannelIdentifier(
            channel=ChannelType(state_manager.get_channel_type()),
            value=state_manager.get_channel_id()
        )
    )
