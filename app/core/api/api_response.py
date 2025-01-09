"""API response management

This module handles validation and state injection of API responses.
All API responses contain both dashboard and action sections that flow through here.
"""

import logging
from typing import Any, Dict, Optional, Tuple

from core.config.interface import StateManagerInterface
from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ErrorContext
from core.utils.exceptions import FlowException

logger = logging.getLogger(__name__)


def update_state_from_response(
    api_response: Dict[str, Any],
    state_manager: StateManagerInterface
) -> Tuple[bool, Optional[str]]:
    """Update state from API response

    This is the main entry point for handling API responses.
    All API responses should route through here to maintain consistent state.

    Args:
        api_response: Full API response containing dashboard and action data
        state_manager: State manager instance
        auth_token: Optional auth token from response

    Returns:
        Tuple[bool, Optional[str]]: Success flag and optional error message
    """
    try:
        # Validate response format
        if not isinstance(api_response, dict):
            raise FlowException(
                message="Invalid API response format",
                step="api_response",
                action="validate_response",
                data={"response": api_response}
            )

        # Get and validate dashboard data
        dashboard_data = api_response.get("data", {}).get("dashboard")
        if not dashboard_data:
            raise FlowException(
                message="Missing dashboard data",
                step="api_response",
                action="validate_dashboard",
                data={"response": api_response}
            )

        # Validate member data exists
        if not dashboard_data.get("member", {}).get("memberID"):
            raise FlowException(
                message="Missing member ID in dashboard",
                step="api_response",
                action="validate_member",
                data={"dashboard": dashboard_data}
            )

        # Get and validate action data
        action_data = api_response.get("data", {}).get("action")
        if not action_data:
            raise FlowException(
                message="Missing action data",
                step="api_response",
                action="validate_action",
                data={"response": api_response}
            )

        # Update state with API response data
        state_update = {
            "dashboard": dashboard_data,  # Complete dashboard data from API
            "action": action_data  # Complete action data from API
        }

        try:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Updating state from API response")
            state_manager.update_state(state_update)
            return True, None
        except Exception as e:
            raise FlowException(
                message="Failed to update state",
                step="api_response",
                action="update_state",
                data={"error": str(e)}
            )

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message=str(e),
            details={
                "step": "api_response",
                "action": "update_state"
            }
        )
        ErrorHandler.handle_flow_error(
            step=error_context.details["step"],
            action=error_context.details["action"],
            data={},
            message=error_context.message,
            flow_state={}
        )
        return False, str(e)
