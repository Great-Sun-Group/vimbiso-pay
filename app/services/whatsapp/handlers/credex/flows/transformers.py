"""Data transformation logic for credex flows enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Tuple, Union

from core.utils.exceptions import StateException
from core.utils.flow_audit import FlowAuditLogger
from services.credex.member import validate_handle

from .validators import AMOUNT_PATTERN

audit = FlowAuditLogger()
logger = logging.getLogger(__name__)


def validate_and_parse_amount(amount_str: str) -> Tuple[float, str]:
    """Validate and parse amount without state transformation"""
    match = AMOUNT_PATTERN.match(str(amount_str).strip().upper())
    if not match:
        raise StateException("Invalid amount format")

    # Extract amount and denomination
    if match.group(1):  # Currency first
        denom, amount = match.group(1), match.group(2)
    elif match.group(3):  # Amount first
        amount, denom = match.group(3), match.group(4)
    else:  # Just amount
        amount, denom = match.group(5), None

    # Validate amount is a positive number
    amount_float = float(amount)
    if amount_float <= 0:
        raise StateException("Amount must be greater than 0")

    return amount_float, denom or "USD"


def validate_and_parse_handle(handle: Union[str, Dict[str, Any]], state_manager: Any) -> str:
    """Validate and parse handle with strict state validation"""
    try:
        # Let StateManager handle validation
        jwt_token = state_manager.get("jwt_token")

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

        # Validate handle through API
        success, response = validate_handle(handle, jwt_token)
        if not success:
            raise StateException(response.get("message", "Invalid handle"))

        return handle

    except StateException as e:
        logger.error(f"Handle validation error: {str(e)}")
        raise


def format_amount_for_display(amount: float, denomination: str) -> str:
    """Format amount for display without state transformation"""
    if denomination in {"USD", "ZWG", "CAD"}:
        return f"${amount:.2f} {denomination}"
    elif denomination == "XAU":
        return f"{amount:.4f} {denomination}"
    return f"{amount} {denomination}"


def store_dashboard_data(state_manager: Any, response: Dict[str, Any]) -> None:
    """Store dashboard data enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Let StateManager handle validation
        channel = state_manager.get("channel")
        flow_data = state_manager.get("flow_data") or {}

        # Validate response format
        if not isinstance(response, dict):
            raise StateException("Invalid response format")

        # Extract dashboard data
        dashboard = response.get("data", {}).get("dashboard")
        if not isinstance(dashboard, dict):
            raise StateException("Invalid dashboard data format")

        # Extract action data
        action = response.get("data", {}).get("action", {})
        if action and not isinstance(action, dict):
            raise StateException("Invalid action data format")

        # Prepare flow data update
        new_flow_data = {
            **flow_data,
            "dashboard": dashboard,
            "last_updated": audit.get_current_timestamp()
        }

        if action:
            action_id = action.get("id")
            action_type = action.get("type")
            if not action_id or not action_type:
                raise StateException("Missing required action data")

            # Let StateManager handle validation and update
            success, error = state_manager.update_state({
                "flow_data": {
                    "flow_type": flow_data["flow_type"],
                    "step": flow_data["step"],
                    "current_step": flow_data["current_step"],
                    "data": {
                        **flow_data.get("data", {}),
                        "action_id": action_id,
                        "action_type": action_type,
                        "action_timestamp": audit.get_current_timestamp(),
                        "action_status": "success" if action_type == "CREDEX_CREATED" else action.get("status", "")
                    }
                }
            })
            if not success:
                raise StateException(f"Failed to update flow data: {error}")

        # Let StateManager handle validation and update
        success, error = state_manager.update_state({
            "flow_data": new_flow_data
        })
        if not success:
            raise StateException(f"Failed to update flow data: {error}")

        # Log success
        logger.info(f"Successfully stored dashboard data for channel {channel['identifier']}")

    except StateException as e:
        logger.error(f"Failed to store dashboard data: {str(e)}")
        raise
