"""Member-specific message templates"""

from typing import Optional

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


class MemberTemplates:
    """Templates for member-related messages"""

    @staticmethod
    def create_first_name_prompt(channel_id: str, member_id: Optional[str] = None) -> Message:
        """Create first name prompt message"""
        return Message(
            recipient=MessageRecipient(
                member_id=member_id or "pending",
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel_id
                )
            ),
            content=TextContent(body="What's your first name?")
        )

    @staticmethod
    def create_last_name_prompt(channel_id: str, member_id: Optional[str] = None) -> Message:
        """Create last name prompt message"""
        return Message(
            recipient=MessageRecipient(
                member_id=member_id or "pending",
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel_id
                )
            ),
            content=TextContent(body="And what's your last name?")
        )

    @staticmethod
    def create_registration_confirmation(
        channel_id: str,
        first_name: str,
        last_name: str,
        member_id: Optional[str] = None
    ) -> Message:
        """Create registration confirmation message"""
        return Message(
            recipient=MessageRecipient(
                member_id=member_id or "pending",
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel_id
                )
            ),
            content=InteractiveContent(
                interactive_type=InteractiveType.BUTTON,
                body=(
                    "✅ Please confirm your registration details:\n\n"
                    f"First Name: {first_name}\n"
                    f"Last Name: {last_name}\n"
                    f"Default Currency: USD"
                ),
                buttons=[
                    Button(id="confirm_action", title="Confirm Registration")
                ]
            )
        )

    @staticmethod
    def create_upgrade_confirmation(channel_id: str, member_id: str) -> Message:
        """Create tier upgrade confirmation message"""
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
                    "*Upgrade to the Hustler tier for $1/month.*\n\n"
                    "Subscribe with the button below to unlock unlimited "
                    "credex transactions.\n\n"
                    "Clicking below authorizes a $1 payment to be automatically "
                    "processed from your credex account every 4 weeks (28 days), "
                    "starting today."
                ),
                buttons=[
                    Button(id="confirm_action", title="Hustle Hard")
                ]
            )
        )

    @staticmethod
    def create_registration_success(channel_id: str, first_name: str, member_id: str) -> Message:
        """Create registration success message"""
        return Message(
            recipient=MessageRecipient(
                member_id=member_id,
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel_id
                )
            ),
            content=TextContent(
                body=f"Welcome {first_name}! Your account has been created successfully! 🎉"
            )
        )

    @staticmethod
    def create_upgrade_success(channel_id: str, member_id: str) -> Message:
        """Create upgrade success message"""
        return Message(
            recipient=MessageRecipient(
                member_id=member_id,
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel_id
                )
            ),
            content=TextContent(
                body="🎉 Successfully upgraded to Hustler tier!"
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
