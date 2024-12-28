"""Step processing functions enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional

from core.utils.exceptions import StateException
from core.utils.flow_audit import FlowAuditLogger
from services.whatsapp.types import WhatsAppMessage

from .transformers import transform_amount, transform_handle

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


def create_message(state_manager: Any, message: str) -> Dict[str, Any]:
    """Create message with state validation

    Args:
        state_manager: State manager instance
        message: Message text

    Returns:
        WhatsApp message dict

    Raises:
        StateException: If state validation fails
    """
    # Let StateManager validate channel access
    channel_id = state_manager.get("channel")["identifier"]  # StateManager validates
    return WhatsAppMessage.create_text(channel_id, message)


def process_amount_step(state_manager: Any, input_data: Optional[str] = None) -> Dict[str, Any]:
    """Process amount step enforcing SINGLE SOURCE OF TRUTH

    Args:
        state_manager: State manager instance
        input_data: Optional amount input

    Returns:
        Message dict

    Raises:
        StateException: If validation or processing fails
    """
    if not input_data:
        return create_message(
            state_manager,
            "Enter amount:\n\n"
            "Examples:\n"
            "100     (USD)\n"
            "USD 100\n"
            "ZWG 100\n"
            "XAU 1"
        )

    # Transform input (raises StateException if invalid)
    amount_data = transform_amount(input_data)

    # Let StateManager validate and update state
    state_manager.update_state({
        "flow_data": {
            "current_step": "handle",
            "data": {
                "amount": amount_data
            }
        }
    })

    return create_message(state_manager, "Enter recipient handle:")


def process_handle_step(state_manager: Any, input_data: Optional[str] = None) -> Dict[str, Any]:
    """Process handle step enforcing SINGLE SOURCE OF TRUTH

    Args:
        state_manager: State manager instance
        input_data: Optional handle input

    Returns:
        Message dict

    Raises:
        StateException: If validation or processing fails
    """
    if not input_data:
        return create_message(state_manager, "Enter recipient handle:")

    # Transform input (raises StateException if invalid)
    handle_data = transform_handle(input_data)

    # Let StateManager validate and update state
    state_manager.update_state({
        "flow_data": {
            "current_step": "confirm",
            "data": {
                "handle": handle_data
            }
        }
    })

    return create_message(state_manager, "Please confirm (yes/no):")


def process_confirm_step(state_manager: Any, input_data: Optional[str] = None) -> Dict[str, Any]:
    """Process confirmation step enforcing SINGLE SOURCE OF TRUTH

    Args:
        state_manager: State manager instance
        input_data: Optional confirmation input

    Returns:
        Message dict

    Raises:
        StateException: If validation or processing fails
    """
    if not input_data:
        return create_message(state_manager, "Please confirm (yes/no):")

    # Validate input
    input_lower = input_data.lower()
    if input_lower not in ["yes", "no"]:
        raise StateException("Please enter 'yes' or 'no'")

    # Let StateManager validate and update state
    state_manager.update_state({
        "flow_data": {
            "current_step": "complete",
            "data": {
                "confirmed": input_lower == "yes"
            }
        }
    })

    return {}
