"""Registration components

This module implements registration-specific components following the component system pattern.
Each component handles a specific part of registration with clear validation and conversion.
"""

from typing import Any, Dict, Set

from core.messaging.types import (
    ChannelIdentifier,
    ChannelType,
    InteractiveContent,
    InteractiveType,
    Message,
    MessageRecipient
)
from core.utils.exceptions import ComponentException
from .base import Component, InputComponent


class RegistrationWelcome(Component):
    """Handles registration welcome screen"""

    def __init__(self):
        super().__init__("registration_welcome")

    def validate(self, value: Any) -> Dict:
        """Validate welcome response"""
        # Validate type
        if not isinstance(value, str):
            raise ComponentException(
                message="Invalid response type",
                component=self.type,
                field="response",
                value=str(type(value))
            )

        # Validate action
        if value.strip().lower() != "start_registration":
            raise ComponentException(
                message="Invalid response - please use the Become a Member button",
                component=self.type,
                field="response",
                value=value
            )

        return {"valid": True}

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified welcome data"""
        return {
            "action": "start_registration",
            "confirmed": True
        }

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
                action_items={
                    "buttons": [{
                        "type": "reply",
                        "reply": {
                            "id": "start_registration",
                            "title": "Become a Member"
                        }
                    }]
                }
            )
        )


class FirstNameInput(InputComponent):
    """First name input with validation"""

    def __init__(self):
        super().__init__("firstname_input")

    def validate(self, value: Any) -> Dict:
        """Validate first name"""
        # Validate type
        if not isinstance(value, str):
            raise ComponentException(
                message="First name must be text",
                component=self.type,
                field="firstname",
                value=str(type(value))
            )

        # Validate length
        firstname = value.strip()
        if not firstname or len(firstname) < 3 or len(firstname) > 50:
            raise ComponentException(
                message="First name must be between 3 and 50 characters",
                component=self.type,
                field="firstname",
                value=firstname
            )

        return {"valid": True}

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified first name"""
        return {
            "firstname": value.strip()
        }


class LastNameInput(InputComponent):
    """Last name input with validation"""

    def __init__(self):
        super().__init__("lastname_input")

    def validate(self, value: Any) -> Dict:
        """Validate last name"""
        # Validate type
        if not isinstance(value, str):
            raise ComponentException(
                message="Last name must be text",
                component=self.type,
                field="lastname",
                value=str(type(value))
            )

        # Validate length
        lastname = value.strip()
        if not lastname or len(lastname) < 3 or len(lastname) > 50:
            raise ComponentException(
                message="Last name must be between 3 and 50 characters",
                component=self.type,
                field="lastname",
                value=lastname
            )

        return {"valid": True}

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified last name"""
        return {
            "lastname": value.strip()
        }


class RegistrationComplete(Component):
    """Handles registration completion"""

    def __init__(self):
        super().__init__("registration_complete")

    def validate(self, value: Any) -> Dict:
        """Validate registration response

        Args:
            value: Registration response containing:
                - member_id: New member ID
                - token: JWT token
                - accounts: Initial accounts

        Returns:
            On success: {"valid": True}
            On error: ComponentException
        """
        if not isinstance(value, dict):
            raise ComponentException(
                message="Invalid registration response format",
                component=self.type,
                field="response",
                value=str(type(value))
            )

        # Validate required fields
        required: Set[str] = {"member_id", "token", "accounts"}
        missing = required - set(value.keys())
        if missing:
            raise ComponentException(
                message=f"Missing required fields in response: {missing}",
                component=self.type,
                field="response",
                value=str(value)
            )

        return {"valid": True}

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified member data"""
        return {
            "member_id": value["member_id"],
            "jwt_token": value["token"],
            "authenticated": True,
            "accounts": value["accounts"],
            "active_account_id": value["accounts"][0]["accountID"] if value["accounts"] else None
        }
