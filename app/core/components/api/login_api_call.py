"""Login API call component

Handles the login flow for both new and existing members:
- For new users: Returns not_found to trigger onboarding
- For existing users: Updates state with dashboard data
"""

import logging
from typing import Any

from core.api.base import handle_api_response, make_api_request
from core.utils.exceptions import ComponentException

from ..base import ApiComponent


class LoginApiCall(ApiComponent):
    """Processes login API calls and manages member state"""

    def __init__(self):
        super().__init__("LoginApiCall")  # Match the class name used for lookup

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing state data"""
        self.state_manager = state_manager

    def validate_api_call(self, value: Any) -> None:
        """Process login API call and update state

        For existing members:
        - Makes login API call
        - Updates state with dashboard data

        For new users:
        - 400 response updates state for onboarding

        Raises:
            ComponentException: If API call fails
        """
        logger = logging.getLogger(__name__)

        # Get channel info from state manager
        channel = self.state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            logger.error("Missing channel identifier")
            raise ComponentException(
                message="No channel identifier found",
                component=self.type,
                field="channel",
                value=str(channel)
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

        # Let handlers update state (including 400 for new users)
        _, error = handle_api_response(
            response=response,
            state_manager=self.state_manager
        )
        if error:
            raise ComponentException(
                message=f"Login failed: {error}",
                component=self.type,
                field="api_call",
                value=str(payload)
            )
