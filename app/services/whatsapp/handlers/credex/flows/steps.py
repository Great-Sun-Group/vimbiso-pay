"""Step processing functions enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator
from services.whatsapp.types import WhatsAppMessage

from .transformers import transform_amount, transform_handle
from .validators import validate_amount, validate_handle

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()

# Required fields for state validation
REQUIRED_FIELDS = {"channel"}


def create_message(state_manager: Any, message: str) -> Dict[str, Any]:
    """Create message with state validation at boundary"""
    try:
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {"channel": state_manager.get("channel")},
            REQUIRED_FIELDS
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # Get channel info from top level state only
        channel = state_manager.get("channel")
        return WhatsAppMessage.create_text(
            channel["identifier"],
            message
        )

    except ValueError as e:
        logger.error(f"Message creation error: {str(e)}")
        return WhatsAppMessage.create_text("unknown", f"Error: {str(e)}")


def process_amount_step(state_manager: Any, input_data: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
    """Process amount step enforcing SINGLE SOURCE OF TRUTH"""
    try:
        if not input_data:
            return True, create_message(
                state_manager,
                "Enter amount:\n\n"
                "Examples:\n"
                "100     (USD)\n"
                "USD 100\n"
                "ZWG 100\n"
                "XAU 1"
            )

        # Validate input
        if not validate_amount(input_data):
            return False, create_message(state_manager, "Invalid amount format")

        # Transform and store
        amount_data = transform_amount(input_data)
        flow_data = state_manager.get("flow_data", {})

        success, error = state_manager.update_state({
            "flow_data": {
                "flow_type": flow_data["flow_type"],
                "step": flow_data["step"],
                "current_step": "handle",
                "data": {
                    **flow_data.get("data", {}),
                    "amount": amount_data
                }
            }
        })
        if not success:
            raise ValueError(error)

        return True, create_message(state_manager, "Enter recipient handle:")

    except ValueError as e:
        logger.error(f"Amount step error: {str(e)}")
        return False, create_message(state_manager, f"Error: {str(e)}")


def process_handle_step(state_manager: Any, input_data: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
    """Process handle step enforcing SINGLE SOURCE OF TRUTH"""
    try:
        if not input_data:
            return True, create_message(state_manager, "Enter recipient handle:")

        # Validate input
        if not validate_handle(input_data):
            return False, create_message(state_manager, "Invalid handle format")

        # Transform and store
        handle_data = transform_handle(input_data)
        flow_data = state_manager.get("flow_data", {})

        success, error = state_manager.update_state({
            "flow_data": {
                "flow_type": flow_data["flow_type"],
                "step": flow_data["step"],
                "current_step": "confirm",
                "data": {
                    **flow_data.get("data", {}),
                    "handle": handle_data
                }
            }
        })
        if not success:
            raise ValueError(error)

        return True, create_message(state_manager, "Please confirm (yes/no):")

    except ValueError as e:
        logger.error(f"Handle step error: {str(e)}")
        return False, create_message(state_manager, f"Error: {str(e)}")


def process_confirm_step(state_manager: Any, input_data: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
    """Process confirmation step enforcing SINGLE SOURCE OF TRUTH"""
    try:
        if not input_data:
            return True, create_message(state_manager, "Please confirm (yes/no):")

        # Validate input
        input_lower = input_data.lower()
        if input_lower not in ["yes", "no"]:
            return False, create_message(state_manager, "Please enter 'yes' or 'no'")

        # Store confirmation
        flow_data = state_manager.get("flow_data", {})
        success, error = state_manager.update_state({
            "flow_data": {
                "flow_type": flow_data["flow_type"],
                "step": flow_data["step"],
                "current_step": "complete",
                "data": {
                    **flow_data.get("data", {}),
                    "confirmed": input_lower == "yes"
                }
            }
        })
        if not success:
            raise ValueError(error)

        return True, {}

    except ValueError as e:
        logger.error(f"Confirmation step error: {str(e)}")
        return False, create_message(state_manager, f"Error: {str(e)}")
