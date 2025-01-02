"""Data transformation logic for credex flows using component system"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from core.components import create_component
from core.utils.exceptions import ComponentException, SystemException

logger = logging.getLogger(__name__)


def transform_button_input(input_data: Any, state_manager: Any) -> Optional[str]:
    """Transform button input using ButtonInput component

    Args:
        input_data: Raw button input
        state_manager: State manager instance

    Returns:
        Button ID string or None if invalid

    Raises:
        ComponentException: If validation fails
    """
    # Create button component
    button_component = create_component("ButtonInput")

    # Validate and convert
    button_component.validate(input_data)
    result = button_component.to_verified_data(input_data)

    return result["button_id"]


def transform_handle(handle: Any, state_manager: Any) -> str:
    """Transform handle input using HandleInput component

    Args:
        handle: Raw handle input
        state_manager: State manager instance

    Returns:
        Validated handle string

    Raises:
        ComponentException: If validation fails
    """
    # Extract handle from interactive message
    if isinstance(handle, dict):
        interactive = handle.get("interactive", {})
        if interactive.get("type") == "text":
            handle = interactive.get("text", {}).get("body", "")
        else:
            raise ComponentException(
                message="Invalid handle format. Please provide text input.",
                component="handle_input",
                field="handle",
                value=str(handle)
            )

    # Create handle component
    handle_component = create_component("HandleInput")

    # Validate and convert
    handle_component.validate(handle)
    result = handle_component.to_verified_data(handle)

    return result["handle"]


def store_dashboard_data(state_manager: Any, response: Dict[str, Any]) -> None:
    """Store dashboard data with validation

    Args:
        state_manager: State manager instance
        response: API response data

    Raises:
        SystemException: If storage fails
    """
    try:
        timestamp = datetime.utcnow().isoformat()

        # Validate and store dashboard data
        dashboard = response.get("data", {}).get("dashboard")
        if not dashboard:
            raise SystemException(
                message="Missing dashboard data in response",
                code="DASHBOARD_ERROR",
                service="transformers",
                action="store_dashboard"
            )

        state_manager.update_state({
            "flow_data": {
                "dashboard": {
                    "data": dashboard,
                    "last_updated": timestamp
                }
            }
        })

        # Store action data if present
        action = response.get("data", {}).get("action")
        if action:
            state_manager.update_state({
                "flow_data": {
                    "data": {
                        "action_id": action.get("id"),
                        "action_type": action.get("type"),
                        "action_timestamp": timestamp,
                        "action_status": "success" if action.get("type") == "CREDEX_CREATED" else action.get("status", "")
                    }
                }
            })

        logger.info(f"Successfully stored dashboard data for channel {state_manager.get_channel_id()}")

    except Exception as e:
        raise SystemException(
            message=f"Failed to store dashboard data: {str(e)}",
            code="DASHBOARD_ERROR",
            service="transformers",
            action="store_dashboard"
        )
