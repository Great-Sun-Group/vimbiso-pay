"""Login API call component

This component handles the login API call with proper validation.
Dashboard data is the source of truth for member state.
"""

from typing import Any, Dict

from decouple import config

from core.utils.error_types import ValidationResult
from core.api.base import make_api_request, handle_api_response

from ..base import ApiComponent


class LoginApiCall(ApiComponent):
    """Handles login API call with proper exit conditions"""

    def __init__(self):
        super().__init__("login")
        self.state_manager = None
        self.bot_service = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing state data"""
        self.state_manager = state_manager

    def set_bot_service(self, bot_service: Any) -> None:
        """Set bot service for API access"""
        self.bot_service = bot_service

    def validate_api_call(self, value: Any) -> ValidationResult:
        """Call login endpoint and validate response"""
        # Get channel info from state manager
        channel = self.state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            return ValidationResult.failure(
                message="No channel identifier found",
                field="channel",
                details={"component": "login"}
            )

        # Make API call
        url = "login"
        headers = {
            "Content-Type": "application/json",
            "x-client-api-key": config("CLIENT_API_KEY"),
        }
        payload = {"phone": channel["identifier"]}

        response = make_api_request(url, headers, payload)

        # Handle 400 for new users
        if response.status_code == 400:
            return ValidationResult.success(
                {"message": "Welcome! Let's get you set up."},
                metadata={
                    "exit_condition": "not_member"  # Exit to onboarding
                }
            )

        # Let handlers update state
        response_data, error = handle_api_response(
            response=response,
            state_manager=self.state_manager
        )
        if error:
            return ValidationResult.failure(
                message=f"Login failed: {error}",
                field="api_call",
                details={"error": error}
            )

        # Get action data for flow
        flow_data = self.state_manager.get_flow_state()
        action_data = flow_data.get("action", {})

        return ValidationResult.success(
            {"action": action_data},
            metadata={
                "exit_condition": "success"  # Exit to dashboard
            }
        )

    def to_message_content(self, value: Dict) -> str:
        """Convert component result to message content"""
        if isinstance(value, dict):
            if "message" in value:
                return value["message"]
            if "action" in value:
                return "Processing your request..."
        return "Logging you in..."

    def to_verified_data(self, value: Any) -> Dict:
        """Convert API response to verified data

        Note: Most data is in dashboard state, we just need
        success indicators and action details here.
        """
        return {
            "authenticated": "message" not in value,  # True if we got API data
            "action_type": value.get("action", {}).get("type"),
            "action_id": value.get("action", {}).get("id")
        }
