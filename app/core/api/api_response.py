"""API response management

This module handles state updates from API responses. All API responses contain both
dashboard and action sections that flow through here.

The state updates are protected by schema validation:
- dashboard: Member state after operation (accounts, profile, etc.)
- action: Operation results and details
- auth: Authentication state when token present

Components can still store their own unvalidated data in component_data.data.
"""

import logging
from typing import Any, Dict, Optional, Tuple

from core.state.interface import StateManagerInterface
from core.error.handler import ErrorHandler
from core.error.types import ErrorContext
from core.error.exceptions import FlowException

logger = logging.getLogger(__name__)


def update_state_from_response(
    api_response: Dict[str, Any],
    state_manager: StateManagerInterface
) -> Tuple[bool, Optional[str]]:
    """Update core state from API response

    This is the main entry point for handling API responses.
    All API responses should route through here to maintain consistent state.

    The updates will be validated against the state schema:
    - dashboard: Must match dashboard schema (member info, accounts, etc.)
    - action: Must match action schema (id, type, timestamp, etc.)
    - auth: Must match auth schema when token present

    Components remain free to store their own data in component_data.data
    which is not validated by the schema.

    Args:
        api_response: Full API response containing dashboard and action data
        state_manager: State manager instance

    Returns:
        Tuple[bool, Optional[str]]: Success flag and optional error message
    """
    try:
        # Extract data section
        data = api_response.get("data", {})
        if not isinstance(data, dict):
            raise FlowException(
                message="Invalid API response format - data must be an object",
                step="api_response",
                action="validate_response",
                data={"response": api_response}
            )

        # Prepare state update (will be schema validated by state manager)
        state_update = {}

        # Dashboard section (member state)
        if "dashboard" in data:
            state_update["dashboard"] = data["dashboard"]

        # Action section (operation results)
        if "action" in data:
            state_update["action"] = data["action"]

            # Auth token if present in action details
            if data["action"].get("details", {}).get("token"):
                state_update["auth"] = {
                    "token": data["action"]["details"]["token"]
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
