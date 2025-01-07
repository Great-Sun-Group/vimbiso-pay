"""Welcome component for registration flow

This component handles the registration welcome screen with proper validation.
"""

from typing import Any

from core.messaging.types import (Button, ChannelIdentifier, ChannelType,
                                  InteractiveContent, InteractiveType, Message,
                                  MessageRecipient)
from core.utils.error_types import ValidationResult

from core.components.base import Component


class Welcome(Component):
    """Handles registration welcome screen"""

    def __init__(self):
        super().__init__("welcome")

    def validate(self, value: Any) -> ValidationResult:
        """Simple validation for welcome step"""
        return ValidationResult.success(value)

    def get_message(self, channel_id: str) -> Message:
        """Get welcome message"""
        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel_id
                )
            ),
            content=InteractiveContent(
                interactive_type=InteractiveType.BUTTON,
                body="Welcome to VimbisoPay 💰\n\nWe're your portal 🚪to the credex ecosystem 🌱\n\nBecome a member 🌐 and open a free account 💳 to get started 📈",
                buttons=[
                    Button(
                        id="start_registration",
                        title="Become a Member"
                    )
                ]
            )
        )
