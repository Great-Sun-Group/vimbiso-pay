"""Step processing functions enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional

from core.utils.error_handler import ErrorContext, ErrorHandler
from core.utils.exceptions import StateException
from services.whatsapp.types import WhatsAppMessage

from .transformers import transform_amount, transform_handle

logger = logging.getLogger(__name__)


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
    try:
        # Let StateManager validate channel access
        channel_id = state_manager.get("channel")["identifier"]  # StateManager validates
        return WhatsAppMessage.create_text(channel_id, message)
    except Exception as e:
        error_context = ErrorContext(
            error_type="state",
            message="Failed to create message. Please try again",
            details={
                "error": str(e),
                "message": message
            }
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))


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
    try:
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
        success, error = state_manager.update_state({
            "flow_data": {
                "current_step": "handle",
                "data": {
                    "amount": amount_data
                }
            }
        })
        if not success:
            error_context = ErrorContext(
                error_type="state",
                message="Failed to save amount. Please try again",
                step_id="amount",
                details={
                    "input": input_data,
                    "amount_data": amount_data,
                    "error": error
                }
            )
            raise StateException(ErrorHandler.handle_error(
                StateException(error),
                state_manager,
                error_context
            ))

        return create_message(state_manager, "Enter recipient handle:")

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message="Failed to process amount. Please try again",
            step_id="amount",
            details={
                "input": input_data,
                "error": str(e)
            }
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))


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
    try:
        if not input_data:
            return create_message(state_manager, "Enter recipient handle:")

        # Transform input (raises StateException if invalid)
        handle_data = transform_handle(input_data)

        # Let StateManager validate and update state
        success, error = state_manager.update_state({
            "flow_data": {
                "current_step": "confirm",
                "data": {
                    "handle": handle_data
                }
            }
        })
        if not success:
            error_context = ErrorContext(
                error_type="state",
                message="Failed to save handle. Please try again",
                step_id="handle",
                details={
                    "input": input_data,
                    "handle_data": handle_data,
                    "error": error
                }
            )
            raise StateException(ErrorHandler.handle_error(
                StateException(error),
                state_manager,
                error_context
            ))

        return create_message(state_manager, "Please confirm (yes/no):")

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message="Failed to process handle. Please try again",
            step_id="handle",
            details={
                "input": input_data,
                "error": str(e)
            }
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))


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
    try:
        if not input_data:
            return create_message(state_manager, "Please confirm (yes/no):")

        # Validate input
        input_lower = input_data.lower()
        if input_lower not in ["yes", "no"]:
            error_context = ErrorContext(
                error_type="input",
                message="Please enter 'yes' or 'no'",
                step_id="confirm",
                details={"input": input_data}
            )
            raise StateException(ErrorHandler.handle_error(
                StateException("Invalid confirmation"),
                state_manager,
                error_context
            ))

        # Let StateManager validate and update state
        success, error = state_manager.update_state({
            "flow_data": {
                "current_step": "complete",
                "data": {
                    "confirmed": input_lower == "yes"
                }
            }
        })
        if not success:
            error_context = ErrorContext(
                error_type="state",
                message="Failed to save confirmation. Please try again",
                step_id="confirm",
                details={
                    "input": input_data,
                    "confirmed": input_lower == "yes",
                    "error": error
                }
            )
            raise StateException(ErrorHandler.handle_error(
                StateException(error),
                state_manager,
                error_context
            ))

        return {}

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message="Failed to process confirmation. Please try again",
            step_id="confirm",
            details={
                "input": input_data,
                "error": str(e)
            }
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))
