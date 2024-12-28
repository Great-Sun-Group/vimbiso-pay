"""Data transformation logic for credex flows enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Union

from core.utils.exceptions import StateException
from core.utils.flow_audit import FlowAuditLogger
from services.credex.member import validate_handle

audit = FlowAuditLogger()
logger = logging.getLogger(__name__)


def transform_amount(amount_str: str, state_manager: Any) -> Dict[str, Any]:
    """Transform amount input to standardized format

    Args:
        amount_str: Raw amount string
        state_manager: State manager instance

    Returns:
        Dict with amount and denomination

    Raises:
        StateException: If validation fails
    """
    # Let StateManager validate amount through state update
    state_manager.update_state({
        "flow_data": {
            "input": {
                "amount": str(amount_str).strip().upper()
            }
        }
    })

    # Get validated amount from state
    amount_data = state_manager.get("flow_data")["input"]["amount"]
    return amount_data


def transform_handle(handle: Union[str, Dict[str, Any]], state_manager: Any) -> str:
    """Transform handle input to standardized format

    Args:
        handle: Raw handle input
        state_manager: State manager instance

    Returns:
        Validated handle string

    Raises:
        StateException: If validation fails
    """
    # Let StateManager validate token
    jwt_token = state_manager.get("jwt_token")  # StateManager validates

    # Extract handle from interactive or text
    if isinstance(handle, dict):
        interactive = handle.get("interactive", {})
        if interactive.get("type") == "text":
            handle = interactive.get("text", {}).get("body", "")
        else:
            raise StateException("Invalid handle format")

    handle = handle.strip()
    if not handle:
        raise StateException("Handle cannot be empty")

    # Validate handle through API (raises StateException if invalid)
    validate_handle(handle, jwt_token)

    return handle


def store_dashboard_data(state_manager: Any, response: Dict[str, Any]) -> None:
    """Store dashboard data enforcing SINGLE SOURCE OF TRUTH

    Args:
        state_manager: State manager instance
        response: API response data

    Raises:
        StateException: If validation or storage fails
    """
    # Let StateManager validate response through state update
    state_manager.update_state({
        "flow_data": {
            "dashboard": {
                "data": response.get("data", {}).get("dashboard", {}),
                "last_updated": audit.get_current_timestamp()
            }
        }
    })

    # Let StateManager validate action data through state update
    action = response.get("data", {}).get("action", {})
    if action:
        state_manager.update_state({
            "flow_data": {
                "data": {
                    "action_id": action.get("id"),
                    "action_type": action.get("type"),
                    "action_timestamp": audit.get_current_timestamp(),
                    "action_status": "success" if action.get("type") == "CREDEX_CREATED" else action.get("status", "")
                }
            }
        })

    # Log success
    logger.info(f"Successfully stored dashboard data for channel {state_manager.get('channel')['identifier']}")
