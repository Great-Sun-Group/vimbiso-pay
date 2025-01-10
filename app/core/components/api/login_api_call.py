"""Login API call component

Handles the login flow for both new and existing members:
- For new users: Sets component_result="start_onboarding"
- For existing users: Sets component_result="send_dashboard"
"""

import logging
from typing import Any

from core.api.base import handle_api_response, make_api_request
from core.error.types import ValidationResult

from ..base import ApiComponent

logger = logging.getLogger(__name__)


class LoginApiCall(ApiComponent):
    """Processes login API calls and manages member state"""

    def __init__(self):
        super().__init__("LoginApiCall")

    def validate_api_call(self, value: Any) -> ValidationResult:
        """Process login API call and set component_result for flow control"""
        try:
            # Get channel info
            channel = self.state_manager.get_state_value("channel")
            if not channel or not channel.get("identifier"):
                return ValidationResult.failure(
                    message="No channel identifier found",
                    field="channel",
                    details={"error": "missing_channel"}
                )

            logger.info(f"Making login API call for channel: {channel['identifier']}")

            # Make API call
            response = make_api_request(
                url="login",
                payload={"phone": channel["identifier"]},
                method="POST",
                retry_auth=False,
                state_manager=self.state_manager
            )
            logger.info(f"API response received: {response}")

            # Check for 404 status which indicates new member
            if response.status_code == 404:
                logger.info("New member detected - starting onboarding flow")
                # Set result for onboarding flow
                self.update_component_data(component_result="start_onboarding")
                return ValidationResult.success(None)  # Success but no result data needed

            # For existing members, let handlers update state
            result, error = handle_api_response(
                response=response,
                state_manager=self.state_manager
            )
            logger.info(f"API response handled - Result: {result}, Error: {error}")

            if error:
                logger.error(f"Login API error: {error}")
                return ValidationResult.failure(
                    message=f"Login failed: {error}",
                    field="api_call",
                    details={"error": error}
                )

            # Get personal account ID from dashboard (schema-validated)
            dashboard = self.state_manager.get_state_value("dashboard", {})
            personal_account = dashboard["accounts"][0]  # First account is always PERSONAL

            # Set active account and transition to dashboard
            self.state_manager.update_state({
                "active_account_id": personal_account["accountID"]
            })

            # Set result for dashboard flow
            self.update_component_data(component_result="send_dashboard")

            return ValidationResult.success(result)

        except Exception as e:
            logger.error(f"Error in login API call: {str(e)}")
            return ValidationResult.failure(
                message=f"Login failed: {str(e)}",
                field="api_call",
                details={"error": str(e)}
            )
