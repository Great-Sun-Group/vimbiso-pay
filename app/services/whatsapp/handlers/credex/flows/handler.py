"""Core message handling for credex flows enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.utils.error_handler import ErrorContext, ErrorHandler
from core.utils.exceptions import StateException

logger = logging.getLogger(__name__)


def handle_message(state_manager: Any, message: Dict[str, Any], credex_service: Any) -> Dict[str, Any]:
    """Handle incoming message with strict state validation"""
    try:
        # Let StateManager validate flow state
        try:
            flow_data = state_manager.get("flow_data")
            current_step = flow_data["current_step"]
        except Exception as e:
            error_context = ErrorContext(
                error_type="state",
                message="Failed to get flow state. Please restart the flow",
                details={
                    "error": str(e)
                }
            )
            raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))

        # Log message handling
        logger.info(
            "Processing message",
            extra={
                "step": current_step,
                "message_type": message.get("type")
            }
        )

        if current_step == "complete":
            return handle_completion(state_manager, message, credex_service)

        # Default to next step
        return handle_next_step(state_manager, message, credex_service)

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message="Failed to process message. Please try again",
            details={
                "message_type": message.get("type"),
                "error": str(e)
            }
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))


def handle_next_step(state_manager: Any, message: Dict[str, Any], credex_service: Any) -> Dict[str, Any]:
    """Handle next step in flow"""
    try:
        # Let StateManager determine next message
        try:
            next_message = state_manager.get_message("next")
            if not next_message:
                error_context = ErrorContext(
                    error_type="flow",
                    message="Failed to get next message. Please try again",
                    details={
                        "current_step": state_manager.get("flow_data")["current_step"]
                    }
                )
                raise StateException(ErrorHandler.handle_error(
                    StateException("No next message"),
                    state_manager,
                    error_context
                ))
            return next_message
        except Exception as e:
            error_context = ErrorContext(
                error_type="flow",
                message="Failed to process next step. Please try again",
                details={
                    "current_step": state_manager.get("flow_data")["current_step"],
                    "error": str(e)
                }
            )
            raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message="Failed to handle next step. Please try again",
            details={
                "message_type": message.get("type"),
                "error": str(e)
            }
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))


def handle_completion(state_manager: Any, message: Dict[str, Any], credex_service: Any) -> Dict[str, Any]:
    """Handle flow completion"""
    try:
        # Let StateManager determine completion message
        try:
            completion_message = state_manager.get_message("complete")
            if not completion_message:
                error_context = ErrorContext(
                    error_type="flow",
                    message="Failed to get completion message. Please try again",
                    details={
                        "flow_type": state_manager.get("flow_data")["flow_type"]
                    }
                )
                raise StateException(ErrorHandler.handle_error(
                    StateException("No completion message"),
                    state_manager,
                    error_context
                ))

            # Log completion
            logger.info(
                "Flow completed successfully",
                extra={
                    "flow_type": state_manager.get("flow_data")["flow_type"]
                }
            )

            return completion_message

        except Exception as e:
            error_context = ErrorContext(
                error_type="flow",
                message="Failed to process completion. Please try again",
                details={
                    "flow_type": state_manager.get("flow_data")["flow_type"],
                    "error": str(e)
                }
            )
            raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message="Failed to handle completion. Please try again",
            details={
                "message_type": message.get("type"),
                "error": str(e)
            }
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))
