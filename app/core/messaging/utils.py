"""Core messaging utilities"""

from core.state.interface import StateManagerInterface
from core.messaging.types import MessageRecipient


def get_recipient(state_manager: StateManagerInterface) -> MessageRecipient:
    """Get message recipient from state

    Args:
        state_manager: State manager instance

    Returns:
        MessageRecipient: Message recipient with channel info

    Raises:
        ComponentException: If identifier is missing
    """
    from core.error.exceptions import ComponentException

    # Get channel info from state
    channel_data = state_manager.get_state_value("channel", {})
    identifier = channel_data.get("identifier")  # e.g. phone number for WhatsApp

    if not identifier:
        raise ComponentException(
            message="Channel identifier is required",
            component="messaging",
            field="channel.identifier",
            value=str(channel_data)
        )

    return MessageRecipient(
        type=channel_data.get("type", "whatsapp"),  # Channel type string
        identifier=identifier  # Use channel identifier (e.g. phone number)
    )
