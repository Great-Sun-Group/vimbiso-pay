"""Login API call component

Handles the login flow for both new and existing members:
- For new users: Returns not_found to trigger onboarding
- For existing users: Updates state with dashboard data
"""

import logging
from typing import Any, Dict

from core.api.base import handle_api_response, make_api_request
from core.utils.error_types import ValidationResult

from ..base import ApiComponent


class LoginApiCall(ApiComponent):
    """Processes login API calls and manages member state"""

    def __init__(self):
        super().__init__("LoginApiCall")  # Match the class name used for lookup

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing state data"""
        self.state_manager = state_manager

    def validate_api_call(self, value: Any) -> ValidationResult:
        """Process login API call and update state

        For existing members:
        - Makes login API call
        - Updates state with dashboard data
        - Returns success status

        For new users:
        - Returns not_found status for onboarding
        """
        logger = logging.getLogger(__name__)

        # Get channel info from state manager
        channel = self.state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            logger.error("Missing channel identifier")
            return ValidationResult.failure(
                message="No channel identifier found",
                field="channel",
                details={"component": self.type}
            )

        # Make API call
        url = "login"
        payload = {"phone": channel["identifier"]}
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Making login API call")

        response = make_api_request(
            url=url,
            payload=payload,
            method="POST",
            retry_auth=False,
            state_manager=self.state_manager
        )

        # Handle 400 for new users
        if response.status_code == 400:
            return ValidationResult.success({
                "status": "not_found"
            })

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

        return ValidationResult.success({
            "status": "success"
        })

    def to_verified_data(self, value: Any) -> Dict:
        """Convert API response to verified data

        Note: Dashboard/action data is handled by handle_api_response.
        We just track authentication status here.
        """
        return {
            "authenticated": value.get("status") == "success"
        }
