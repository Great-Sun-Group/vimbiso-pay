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
            channel = self.state_manager.get("channel")
            if not channel or not channel.get("identifier"):
                return ValidationResult.failure(
                    message="No channel identifier found",
                    field="channel",
                    details={"error": "missing_channel"}
                )

            # Make API call
            response = make_api_request(
                url="login",
                payload={"phone": channel["identifier"]},
                method="POST",
                retry_auth=False,
                state_manager=self.state_manager
            )

            # Let handlers update state
            result, error = handle_api_response(
                response=response,
                state_manager=self.state_manager
            )

            if error:
                return ValidationResult.failure(
                    message=f"Login failed: {error}",
                    field="api_call",
                    details={"error": error}
                )

            # Set component_result based on user existence
            if result.get("exists"):
                # User exists - verify dashboard data was updated
                dashboard = self.state_manager.get_dashboard_data()
                if not dashboard:
                    return ValidationResult.failure(
                        message="Missing dashboard data",
                        field="dashboard",
                        details={"error": "missing_data"}
                    )

                # Set result to send to dashboard
                current = self.state_manager.get_current_state()
                self.state_manager.update_current_state(
                    path=current.get("path", ""),
                    component=current.get("component", ""),
                    data=current.get("data", {}),
                    component_result="send_dashboard"
                )
            else:
                # User doesn't exist - start onboarding
                current = self.state_manager.get_current_state()
                self.state_manager.update_current_state(
                    path=current.get("path", ""),
                    component=current.get("component", ""),
                    data=current.get("data", {}),
                    component_result="start_onboarding"
                )

            return ValidationResult.success(result)

        except Exception as e:
            logger.error(f"Error in login API call: {str(e)}")
            return ValidationResult.failure(
                message=f"Login failed: {str(e)}",
                field="api_call",
                details={"error": str(e)}
            )
