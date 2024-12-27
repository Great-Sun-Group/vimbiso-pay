"""Validation logic for credex flows"""
import logging
import re
from typing import Any, Dict, Union

from core.utils.flow_audit import FlowAuditLogger

audit = FlowAuditLogger()

logger = logging.getLogger(__name__)

# Constants
VALID_DENOMINATIONS = {"USD", "ZWG", "CAD", "XAU"}
AMOUNT_PATTERN = re.compile(r"^(?:([A-Z]{3})\s+(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s+([A-Z]{3})|(\d+(?:\.\d+)?))$")
HANDLE_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")


def validate_button_response(response: Union[str, Dict[str, Any]], current_step_id: str = None) -> bool:
    """Validate button response"""
    # Log the response for debugging
    logger.debug(f"Validating button response: {response}")

    # Handle string input (pre-parsed message)
    if isinstance(response, str):
        if response != "confirm_action":
            raise ValueError("Please use the confirmation button")
        return True

    # Handle dict input (raw message format)
    if isinstance(response, dict):
        # Get message type and body from payload
        msg_type = response.get("type")
        body = response.get("body", "")

        # Handle button press
        if msg_type == "button":
            if body != "confirm_action":
                raise ValueError("Please use the confirmation button")
            return True

        # Handle text input (for backwards compatibility)
        if msg_type == "text":
            # Check if we're in a flow step
            if current_step_id == "confirm":
                if body.lower() != "confirm_action":
                    raise ValueError("Please use the confirmation button")
                return True
            raise ValueError("Invalid confirmation format")

    raise ValueError("Invalid confirmation format")


def validate_amount(amount_data: Union[str, Dict[str, Any]], flow_id: str = None) -> bool:
    """Validate amount format"""
    # Handle already transformed amount
    if isinstance(amount_data, dict):
        if not ("amount" in amount_data and "denomination" in amount_data):
            raise ValueError("Amount data missing required fields")

        if not isinstance(amount_data["amount"], (int, float)):
            raise ValueError("Amount must be a number")

        if amount_data["denomination"] and amount_data["denomination"] not in VALID_DENOMINATIONS:
            raise ValueError(f"Invalid currency. Valid options are: {', '.join(VALID_DENOMINATIONS)}")

        return True

    # Handle string input
    if not amount_data:
        raise ValueError("Amount cannot be empty")

    # Try to match the pattern
    amount_str = str(amount_data).strip().upper()
    match = AMOUNT_PATTERN.match(amount_str)

    if not match:
        raise ValueError(
            "Invalid amount format. Examples:\n"
            "100     (USD)\n"
            "USD 100\n"
            "ZWG 100\n"
            "XAU 1"
        )

    # Validate denomination
    denom = match.group(1) or match.group(4)
    if denom and denom not in VALID_DENOMINATIONS:
        raise ValueError(f"Invalid currency. Valid options are: {', '.join(VALID_DENOMINATIONS)}")

    # Log validation if flow_id provided
    if flow_id:
        audit.log_validation_event(
            flow_id,
            "amount",
            amount_str,
            True,
            None
        )

    return True


def validate_handle(handle: Union[str, Dict[str, Any]], flow_id: str = None) -> bool:
    """Validate handle format"""
    # Handle interactive message
    if isinstance(handle, dict):
        interactive = handle.get("interactive", {})
        if interactive.get("type") == "text":
            text = interactive.get("text", {}).get("body", "")
            if not text:
                raise ValueError("Handle cannot be empty")
            if not HANDLE_PATTERN.match(text.strip()):
                raise ValueError("Handle can only contain letters, numbers, and underscores")
            return True
        raise ValueError("Invalid handle format")

    # Handle text input
    if not handle:
        raise ValueError("Handle cannot be empty")
    if not HANDLE_PATTERN.match(handle.strip()):
        raise ValueError("Handle can only contain letters, numbers, and underscores")

    # Log validation if flow_id provided
    if flow_id:
        audit.log_validation_event(
            flow_id,
            "handle",
            handle,
            True,
            None
        )

    return True
