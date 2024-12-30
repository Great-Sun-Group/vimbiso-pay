"""Core message handling for credex flows enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.utils.error_handler import ErrorContext, ErrorHandler
from core.utils.exceptions import StateException
from .messages import create_success_message

logger = logging.getLogger(__name__)


def validate_message_state(state_manager: Any, message: Dict[str, Any]) -> None:
    """Validate message through state manager"""
    # Validate message structure
    state_manager.update_state({
        "flow_data": {
            "message": {
                "type": message.get("type"),
                "timestamp": message.get("timestamp"),
                "content": message.get("content", {})
            }
        }
    })

    # Validate required fields
    state_manager.update_state({
        "flow_data": {
            "validation": {
                "message": {
                    "has_type": bool(message.get("type")),
                    "has_timestamp": bool(message.get("timestamp")),
                    "has_content": bool(message.get("content"))
                }
            }
        }
    })


def update_flow_state(state_manager: Any, is_complete: bool = False) -> None:
    """Update flow state through state manager"""
    # Get current state
    flow_data = state_manager.get_flow_step_data()
    current_step = flow_data.get("step", 0)
    flow_type = flow_data.get("flow_type", "unknown")

    # Update state
    state_manager.update_state({
        "flow_data": {
            "step": current_step + (1 if not is_complete else 0),
            "current_step": "complete" if is_complete else "next",
            "status": {
                "complete": is_complete,
                "flow_type": flow_type,
                "step_count": current_step + 1
            }
        }
    })


def handle_message(state_manager: Any, message: Dict[str, Any], credex_service: Any) -> Dict[str, Any]:
    """Handle incoming message through state validation"""
    try:
        # Validate message state
        validate_message_state(state_manager, message)

        # Get validated flow data
        flow_data = state_manager.get_flow_step_data()
        is_complete = flow_data.get("current_step") == "complete"

        # Update flow state
        update_flow_state(state_manager, is_complete)

        # Get channel ID through state manager
        channel_id = state_manager.get("channel")["identifier"]

        # Handle completion
        if is_complete:
            logger.info(
                "Flow completed successfully",
                extra={
                    "flow_type": flow_data.get("flow_type"),
                    "channel_id": channel_id,
                    "steps_taken": flow_data.get("step", 0)
                }
            )
            return create_success_message(channel_id)

        # Process next step through service
        return credex_service.process_step(
            state_manager,
            flow_data.get("current_step"),
            message
        )

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message="Failed to process message",
            step_id=flow_data.get("current_step") if "flow_data" in locals() else None,
            details={
                "message_type": message.get("type"),
                "flow_type": flow_data.get("flow_type") if "flow_data" in locals() else None,
                "error": str(e)
            }
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))
