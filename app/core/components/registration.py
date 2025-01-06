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
from core.utils.error_types import ValidationResult
from .base import Component, InputComponent


class RegistrationWelcome(Component):
    """Handles registration welcome screen"""

    def __init__(self):
        super().__init__("registration_welcome")

    def validate(self, value: Any) -> ValidationResult:
        """Validate welcome response with proper tracking"""
        # Validate type
        type_result = self._validate_type(value, str, "text")
        if not type_result.valid:
            return type_result

        # Validate action
        action = value.strip().lower()
        if action != "start_registration":
            return ValidationResult.failure(
                message="Please use the Become a Member button",
                field="response",
                details={
                    "expected": "start_registration",
                    "received": action
                }
            )

        return ValidationResult.success(action)

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

    def validate(self, value: Any) -> ValidationResult:
        """Validate first name with proper tracking"""
        # Validate type
        type_result = self._validate_type(value, str, "text")
        if not type_result.valid:
            return type_result

        # Validate required
        required_result = self._validate_required(value)
        if not required_result.valid:
            return required_result

        # Validate length
        firstname = value.strip()
        if len(firstname) < 3 or len(firstname) > 50:
            return ValidationResult.failure(
                message="First name must be between 3 and 50 characters",
                field="firstname",
                details={
                    "min_length": 3,
                    "max_length": 50,
                    "actual_length": len(firstname)
                }
            )

        return ValidationResult.success(firstname)

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified first name"""
        return {
            "firstname": value.strip()
        }


class LastNameInput(InputComponent):
    """Last name input with validation"""

    def __init__(self):
        super().__init__("lastname_input")

    def validate(self, value: Any) -> ValidationResult:
        """Validate last name with proper tracking"""
        # Validate type
        type_result = self._validate_type(value, str, "text")
        if not type_result.valid:
            return type_result

        # Validate required
        required_result = self._validate_required(value)
        if not required_result.valid:
            return required_result

        # Validate length
        lastname = value.strip()
        if len(lastname) < 3 or len(lastname) > 50:
            return ValidationResult.failure(
                message="Last name must be between 3 and 50 characters",
                field="lastname",
                details={
                    "min_length": 3,
                    "max_length": 50,
                    "actual_length": len(lastname)
                }
            )

        return ValidationResult.success(lastname)

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified last name"""
        return {
            "lastname": value.strip()
        }


class RegistrationComplete(Component):
    """Handles registration completion"""

    def __init__(self):
        super().__init__("registration_complete")

    def validate(self, value: Any) -> ValidationResult:
        """Validate registration response with proper tracking"""
        # Validate type
        type_result = self._validate_type(value, dict, "object")
        if not type_result.valid:
            return type_result

        # Validate required fields
        required: Set[str] = {"member_id", "token", "accounts"}
        missing = required - set(value.keys())
        if missing:
            return ValidationResult.failure(
                message="Missing required fields in response",
                field="response",
                details={
                    "missing_fields": list(missing),
                    "received_fields": list(value.keys())
                }
            )

        return ValidationResult.success(value)

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified member data"""
        return {
            "member_id": value["member_id"],
            "jwt_token": value["token"],
            "authenticated": True,
            "accounts": value["accounts"],
            "active_account_id": value["accounts"][0]["accountID"] if value["accounts"] else None
        }
