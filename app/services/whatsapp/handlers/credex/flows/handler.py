"""Core message handling for credex flows enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.utils.error_handler import ErrorContext, ErrorHandler
from core.utils.exceptions import StateException

logger = logging.getLogger(__name__)


def handle_message(state_manager: Any, message: Dict[str, Any], credex_service: Any) -> Dict[str, Any]:
    """Handle incoming message through state validation

    Args:
        state_manager: State manager instance
        message: Incoming message data
        credex_service: CredEx service instance

    Returns:
        Dict containing response message data

    Raises:
        StateException: If state validation fails
    """
    try:
        # Validate message state through update
        state_update = {
            "flow_data": {
                "message": {
                    "type": message.get("type"),
                    "timestamp": message.get("timestamp")
                }
            }
        }

        # Let StateManager validate
        success, error = state_manager.update_state(state_update)
        if not success:
            raise StateException(f"Failed to validate message state: {error}")

        # Get validated flow data
        flow_data = state_manager.get("flow_data")
        if not flow_data:
            raise StateException("Missing flow data")

        # Route based on flow state
        if flow_data.get("current_step") == "complete":
            return handle_completion(state_manager, message, credex_service)

        return handle_next_step(state_manager, message, credex_service)

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message=str(e),
            details={
                "operation": "handle_message",
                "message_type": message.get("type")
            }
        )
        ErrorHandler.handle_error(e, state_manager, error_context)
        raise StateException(f"Message handling failed: {str(e)}")


def handle_next_step(state_manager: Any, message: Dict[str, Any], credex_service: Any) -> Dict[str, Any]:
    """Handle next step through state validation

    Args:
        state_manager: State manager instance
        message: Current message data
        credex_service: CredEx service instance

    Returns:
        Dict containing next step message

    Raises:
        StateException: If state validation fails
    """
    try:
        # Update state for next step
        state_update = {
            "flow_data": {
                "step_transition": {
                    "direction": "next",
                    "message_type": message.get("type")
                }
            }
        }

        # Let StateManager validate transition
        success, error = state_manager.update_state(state_update)
        if not success:
            raise StateException(f"Failed to validate step transition: {error}")

        # Get validated next message
        next_message = state_manager.get_message("next")
        if not next_message:
            raise StateException("No next message available")

        return next_message

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message=str(e),
            details={
                "operation": "handle_next_step",
                "message_type": message.get("type")
            }
        )
        ErrorHandler.handle_error(e, state_manager, error_context)
        raise StateException(f"Next step handling failed: {str(e)}")


def handle_completion(state_manager: Any, message: Dict[str, Any], credex_service: Any) -> Dict[str, Any]:
    """Handle completion through state validation

    Args:
        state_manager: State manager instance
        message: Current message data
        credex_service: CredEx service instance

    Returns:
        Dict containing completion message

    Raises:
        StateException: If state validation fails
    """
    try:
        # Update state for completion
        state_update = {
            "flow_data": {
                "completion": {
                    "message_type": message.get("type"),
                    "timestamp": message.get("timestamp")
                }
            }
        }

        # Let StateManager validate completion
        success, error = state_manager.update_state(state_update)
        if not success:
            raise StateException(f"Failed to validate completion: {error}")

        # Get validated completion message
        completion_message = state_manager.get_message("complete")
        if not completion_message:
            raise StateException("No completion message available")

        # Log successful completion
        flow_data = state_manager.get("flow_data")
        logger.info(
            "Flow completed successfully",
            extra={
                "flow_type": flow_data.get("flow_type"),
                "channel_id": state_manager.get("channel", {}).get("identifier")
            }
        )

        return completion_message

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message=str(e),
            details={
                "operation": "handle_completion",
                "message_type": message.get("type")
            }
        )
        ErrorHandler.handle_error(e, state_manager, error_context)
        raise StateException(f"Completion handling failed: {str(e)}")
