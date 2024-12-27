"""Data transformation logic for credex flows enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Tuple, Union

from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator

from .validators import AMOUNT_PATTERN

audit = FlowAuditLogger()

logger = logging.getLogger(__name__)


def validate_and_parse_amount(amount_str: str) -> Tuple[float, str]:
    """Validate and parse amount without state transformation"""
    match = AMOUNT_PATTERN.match(str(amount_str).strip().upper())
    if not match:
        raise ValueError("Invalid amount format")

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
        raise ValueError("Amount must be greater than 0")

    return amount_float, denom or "USD"


def validate_and_parse_handle(handle: Union[str, Dict[str, Any]], state_manager: Any) -> str:
    """Validate and parse handle with strict state validation"""
    # Extract handle from interactive or text
    if isinstance(handle, dict):
        interactive = handle.get("interactive", {})
        if interactive.get("type") == "text":
            handle = interactive.get("text", {}).get("body", "")
        else:
            raise ValueError("Invalid handle format")

    handle = handle.strip()

    # Get service through state manager
    credex_service = state_manager.get_or_create_credex_service()

    # Validate handle through API
    success, response = credex_service.services['member'].validate_handle(handle)
    if not success:
        raise ValueError(response.get("message", "Invalid handle"))

    return handle


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
        # Validate input parameters
        if not isinstance(response, dict):
            raise ValueError("Invalid response format")

        # Validate ALL required state at boundary
        required_fields = {"channel", "member_id", "flow_data", "authenticated"}
        current_state = {
            field: state_manager.get(field)
            for field in required_fields
        }

        # Validate required fields
        validation = StateValidator.validate_before_access(
            current_state,
            {"channel", "member_id", "flow_data"}
        )
        if not validation.is_valid:
            raise ValueError(f"State validation failed: {validation.error_message}")

        # Get channel info (SINGLE SOURCE OF TRUTH)
        channel = state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            raise ValueError("Channel identifier not found")

        # Extract and validate dashboard data
        dashboard = response.get("data", {}).get("dashboard")
        if not isinstance(dashboard, dict):
            raise ValueError("Invalid dashboard data format")

        # Extract and validate action data
        action = response.get("data", {}).get("action", {})
        if action and not isinstance(action, dict):
            raise ValueError("Invalid action data format")

        # Get current flow data (SINGLE SOURCE OF TRUTH)
        flow_data = state_manager.get("flow_data")
        if not isinstance(flow_data, dict):
            flow_data = {}

        # Prepare new flow data
        new_flow_data = {
            "dashboard": dashboard,
            "last_updated": audit.get_current_timestamp()
        }

        if action:
            action_id = action.get("id")
            action_type = action.get("type")
            if not action_id or not action_type:
                raise ValueError("Missing required action data")

            new_flow_data.update({
                "action_id": action_id,
                "action_type": action_type,
                "action_timestamp": audit.get_current_timestamp(),
                "action_status": "success" if action_type == "CREDEX_CREATED" else action.get("status", "")
            })

        # Merge with existing flow data
        flow_data.update(new_flow_data)

        # Validate state update
        new_state = {"flow_data": flow_data}
        validation = StateValidator.validate_state(new_state)
        if not validation.is_valid:
            raise ValueError(f"Invalid flow data: {validation.error_message}")

        # Update state
        success, error = state_manager.update_state(new_state)
        if not success:
            raise ValueError(f"Failed to update flow data: {error}")

        # Log success
        logger.info(f"Successfully stored dashboard data for channel {channel['identifier']}")

    except ValueError as e:
        # Get channel info for error logging
        try:
            channel = state_manager.get("channel")
            channel_id = channel["identifier"] if channel else "unknown"
        except (ValueError, KeyError, TypeError) as err:
            logger.error(f"Failed to get channel for error logging: {str(err)}")
            channel_id = "unknown"

        logger.error(f"Failed to store dashboard data: {str(e)} for channel {channel_id}")
        raise
