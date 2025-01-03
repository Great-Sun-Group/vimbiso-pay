"""Shared utilities for messaging services"""
from typing import Any

from core.messaging.types import MessageRecipient
from core.utils.exceptions import ComponentException


def get_recipient(state_manager: Any) -> MessageRecipient:
    """Get message recipient from state with validation"""
    try:
        return MessageRecipient(
            channel_id=state_manager.get_channel_id(),
            member_id=state_manager.get_member_id()
        )
    except ComponentException:
        # If member_id fails, still return with channel_id
        return MessageRecipient(
            channel_id=state_manager.get_channel_id(),
            member_id=None
        )
