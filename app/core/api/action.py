"""Action state management

This module handles action data from API responses.
All API responses include an action section describing what happened.
Action data represents operation results and details.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ErrorContext
from core.utils.exceptions import FlowException

logger = logging.getLogger(__name__)


def update_action_from_response(
    api_response: Dict[str, Any],
    state_manager: Any
) -> Tuple[bool, Optional[str]]:
    """Update action state from API response

    This is the main entry point for handling API response action data.
    All API responses include an action section that should flow through here.

    Args:
        api_response: Full API response containing action data
        state_manager: State manager instance

    Returns:
        Tuple[bool, Optional[str]]: Success flag and optional error message
    """
    try:
        # Validate response format
        if not isinstance(api_response, dict):
            raise FlowException(
                message="Invalid API response format",
                step="action",
                action="validate_response",
                data={"response": api_response}
            )

        # Get and validate action data
        action_data = api_response.get("data", {}).get("action")
        if not action_data:
            raise FlowException(
                message="Missing action data",
                step="action",
                action="validate_action",
                data={"response": api_response}
            )

        # Update state with action data
        state_update = {
            "flow_data": {
                "action": action_data,
                "_metadata": {
                    "updated_at": datetime.utcnow().isoformat()
                }
            }
        }

        try:
            state_manager.update_state(state_update)
        except Exception as e:
            raise FlowException(
                message="Failed to update state",
                step="action",
                action="update_state",
                data={"error": str(e), "update": state_update}
            )

        logger.info("Successfully updated action state")
        return True, None

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message=str(e),
            details={
                "step": "action",
                "action": "update_action"
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


def get_action_message(action: Dict[str, Any]) -> str:
    """Get human-friendly message from action data"""
    # Return explicit message if present
    if action.get("message"):
        return action["message"]

    # Check details for message
    if action.get("details", {}).get("message"):
        return action["details"]["message"]

    return ""
