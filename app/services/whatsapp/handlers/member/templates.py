"""Member-specific message templates enforcing SINGLE SOURCE OF TRUTH

These templates are state-independent and only create message structures.
They do not access or modify state directly, maintaining separation of concerns.
"""

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
    """Templates for member-related messages with strict parameter validation"""

    @staticmethod
    def _validate_identifiers(channel_id: str, member_id: Optional[str] = None) -> None:
        """Validate channel and member identifiers"""
        if not channel_id:
            raise ValueError("Channel identifier is required")
        if member_id is not None and not member_id:
            raise ValueError("Member identifier cannot be empty if provided")

    @staticmethod
    def create_first_name_prompt(channel_id: str, member_id: Optional[str] = None) -> Message:
        """Create first name prompt message

        Args:
            channel_id: Required channel identifier
            member_id: Optional member identifier, defaults to "pending"

        Returns:
            Message: Formatted prompt message

        Raises:
            ValueError: If channel_id is empty or member_id is empty when provided
        """
        MemberTemplates._validate_identifiers(channel_id, member_id)
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
        """Create last name prompt message

        Args:
            channel_id: Required channel identifier
            member_id: Optional member identifier, defaults to "pending"

        Returns:
            Message: Formatted prompt message

        Raises:
            ValueError: If channel_id is empty or member_id is empty when provided
        """
        MemberTemplates._validate_identifiers(channel_id, member_id)
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
        """Create registration confirmation message

        Args:
            channel_id: Required channel identifier
            first_name: User's first name
            last_name: User's last name
            member_id: Optional member identifier, defaults to "pending"

        Returns:
            Message: Formatted confirmation message

        Raises:
            ValueError: If any required parameters are empty
        """
        MemberTemplates._validate_identifiers(channel_id, member_id)
        if not first_name or not last_name:
            raise ValueError("First name and last name are required")

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
        """Create tier upgrade confirmation message

        Args:
            channel_id: Required channel identifier
            member_id: Required member identifier

        Returns:
            Message: Formatted confirmation message

        Raises:
            ValueError: If channel_id or member_id is empty
        """
        MemberTemplates._validate_identifiers(channel_id, member_id)
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
        """Create registration success message

        Args:
            channel_id: Required channel identifier
            first_name: User's first name
            member_id: Required member identifier

        Returns:
            Message: Formatted success message

        Raises:
            ValueError: If any required parameters are empty
        """
        MemberTemplates._validate_identifiers(channel_id, member_id)
        if not first_name:
            raise ValueError("First name is required")

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
        """Create upgrade success message

        Args:
            channel_id: Required channel identifier
            member_id: Required member identifier

        Returns:
            Message: Formatted success message

        Raises:
            ValueError: If channel_id or member_id is empty
        """
        MemberTemplates._validate_identifiers(channel_id, member_id)
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
        """Create error message

        Args:
            channel_id: Required channel identifier
            error: Error message to display
            member_id: Optional member identifier, defaults to "pending"

        Returns:
            Message: Formatted error message

        Raises:
            ValueError: If channel_id is empty or error is empty
        """
        MemberTemplates._validate_identifiers(channel_id, member_id)
        if not error:
            raise ValueError("Error message is required")

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
