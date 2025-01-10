"""Core messaging utilities"""

from core.state.interface import StateManagerInterface
from core.messaging.types import ChannelIdentifier, ChannelType, MessageRecipient


def get_recipient(state_manager: StateManagerInterface) -> MessageRecipient:
    """Get message recipient from state

    Args:
        state_manager: State manager instance

    Returns:
        MessageRecipient: Message recipient with channel info

    Raises:
        ComponentException: If channel identifier is missing
    """
    from core.error.exceptions import ComponentException

    channel_data = state_manager.get("channel") or {}
    channel_id = channel_data.get("identifier")

    if not channel_id:
        raise ComponentException(
            message="Channel identifier is required",
            component="messaging",
            field="channel.identifier",
            value=str(channel_data)
        )

    return MessageRecipient(
        channel_id=ChannelIdentifier(
            channel=ChannelType(channel_data.get("type", "whatsapp")),
            value=channel_id
        )
    )
