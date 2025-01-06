"""Registration components

This module implements registration-specific components following the component system pattern.
Each component handles a specific part of registration with clear validation and conversion.
"""

from typing import Any, Dict

from core.messaging.types import (Button, ChannelIdentifier, ChannelType,
                                  InteractiveContent, InteractiveType, Message,
                                  MessageRecipient)
from core.utils.error_types import ValidationResult

from .base import Component, InputComponent


class RegistrationWelcome(InputComponent):
    """Handles registration welcome screen"""

    def __init__(self):
        super().__init__("registration_welcome")

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


class OnBoardMember(Component):
    """Handles member onboarding by calling the onboardMember endpoint"""

    def __init__(self):
        super().__init__("onboard_member")
        self.state_manager = None
        self.bot_service = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing registration data"""
        self.state_manager = state_manager

    def set_bot_service(self, bot_service: Any) -> None:
        """Set bot service for API access"""
        self.bot_service = bot_service

    def validate(self, value: Any) -> ValidationResult:
        """Call onboardMember endpoint and validate response"""
        # Validate state manager and bot service are set
        if not self.state_manager:
            return ValidationResult.failure(
                message="State manager not set",
                field="state_manager",
                details={"component": "onboard_member"}
            )

        if not self.bot_service:
            return ValidationResult.failure(
                message="Bot service not set",
                field="bot_service",
                details={"component": "onboard_member"}
            )

        # Get registration data from state
        flow_data = self.state_manager.get_flow_state()
        if not flow_data or "data" not in flow_data:
            return ValidationResult.failure(
                message="No registration data found",
                field="flow_data",
                details={"component": "onboard_member"}
            )

        # Get registration data
        registration_data = flow_data["data"]

        # Get channel info from state manager
        channel = self.state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            return ValidationResult.failure(
                message="No channel identifier found",
                field="channel",
                details={"component": "onboard_member"}
            )

        member_data = {
            "firstname": registration_data.get("firstname"),
            "lastname": registration_data.get("lastname"),
            "phone": channel["identifier"],
            "defaultDenom": "USD"  # Default denomination required by API
        }

        # Call onboardMember endpoint
        from core.api.auth import onboard_member
        success, message = onboard_member(
            bot_service=self.bot_service,
            member_data=member_data
        )

        if not success:
            return ValidationResult.failure(
                message=f"Registration failed: {message}",
                field="api_call",
                details={"error": message}
            )

        # Return raw API response from state
        flow_data = self.state_manager.get_flow_state()
        if not flow_data or "data" not in flow_data:
            return ValidationResult.failure(
                message="No state data after registration",
                field="flow_data",
                details={"component": "onboard_member"}
            )

        # Get API response from state
        api_response = flow_data["data"].get("api_response")
        if not api_response:
            return ValidationResult.failure(
                message="No API response data found",
                field="api_response",
                details={"flow_data": flow_data["data"]}
            )

        return ValidationResult.success(api_response)

    def to_verified_data(self, value: Any) -> Dict:
        """Convert registration data to verified data"""
        return {
            "member_id": value.get("member_id"),
            "jwt_token": value.get("token"),
            "authenticated": True,
            "accounts": value.get("accounts", []),
            "active_account_id": value.get("accounts", [{}])[0].get("accountID") if value.get("accounts") else None
        }
