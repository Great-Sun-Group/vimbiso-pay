"""Flow processing and continuation logic enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional

from core.utils.exceptions import StateException
from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ErrorContext
from ...types import WhatsAppMessage
from ..member.dashboard import handle_dashboard_display

logger = logging.getLogger(__name__)

# Flow handler mapping
FLOW_HANDLERS: Dict[str, str] = {
    "registration": "process_registration_step",
    "upgrade": "process_upgrade_step",
    "offer": "process_offer_step",
    "accept": "process_accept_step",
    "decline": "process_decline_step",
    "cancel": "process_cancel_step"
}


def process_flow(
    state_manager: Any,
    input_value: Any,
    flow_data: dict
) -> WhatsAppMessage:
    """Process flow continuation enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get channel ID (StateManager validates)
        channel_id = state_manager.get_channel_id()

        # Get handler function
        flow_type = state_manager.get_flow_type()  # StateManager validates flow_data structure
        handler_name = FLOW_HANDLERS.get(flow_type)
        if not handler_name:
            error_context = ErrorContext(
                error_type="flow",
                message=f"Unsupported flow type: {flow_type}",
                details={"flow_type": flow_type}
            )
            error_response = ErrorHandler.handle_error(
                StateException(error_context.message),
                state_manager,
                error_context
            )
            return WhatsAppMessage.create_text(
                channel_id,
                error_response['data']['action']['details']['message']
            )

        handler_module = __import__(
            f"services.whatsapp.handlers.credex.flows.{flow_type}",
            fromlist=[handler_name]
        )
        handler_func = getattr(handler_module, handler_name)

        # Process step (StateManager validates current_step exists)
        current_step = state_manager.get_current_step()
        result = handler_func(state_manager, current_step, input_value)

        # Only clear flow and show dashboard if we're at the final step
        if not result and current_step == "complete":
            # Clear flow state and return to default display
            success, error = state_manager.update_state({
                "flow_data": {
                    "data": {
                        "message": "Operation completed successfully"
                    }
                }
            })
            if not success:
                error_context = ErrorContext(
                    error_type="flow",
                    message=f"Failed to clear flow state: {error}",
                    details={"flow_type": flow_type}
                )
                error_response = ErrorHandler.handle_error(
                    StateException(error_context.message),
                    state_manager,
                    error_context
                )
                return WhatsAppMessage.create_text(
                    channel_id,
                    error_response['data']['action']['details']['message']
                )

            # Show default dashboard display
            return handle_dashboard_display(state_manager)

        # For intermediate steps, preserve flow state and return result
        # This allows steps to return None for initial prompts
        return result

    except StateException as e:
        error_context = ErrorContext(
            error_type="flow",
            message=f"Flow processing error: {str(e)}",
            details={
                "flow_type": state_manager.get_flow_type(),
                "step": state_manager.get_current_step(),
                "input": input_value
            }
        )
        error_response = ErrorHandler.handle_error(
            e,
            state_manager,
            error_context
        )
        return WhatsAppMessage.create_text(
            state_manager.get_channel_id(),
            error_response['data']['action']['details']['message']
        )


def handle_flow_completion(state_manager: Any, success_message: Optional[str] = None) -> WhatsAppMessage:
    """Handle flow completion enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get channel ID (StateManager validates)
        channel_id = state_manager.get_channel_id()

        # Clear flow state and return to default display
        success, error = state_manager.update_state({
            "flow_data": {
                "data": {
                    "message": success_message or "Operation completed successfully"
                }
            }
        })
        if not success:
            error_context = ErrorContext(
                error_type="flow",
                message=f"Failed to clear flow state: {error}",
                details={"channel_id": channel_id}
            )
            error_response = ErrorHandler.handle_error(
                StateException(error_context.message),
                state_manager,
                error_context
            )
            return WhatsAppMessage.create_text(
                channel_id,
                error_response['data']['action']['details']['message']
            )

        # Show dashboard
        return handle_dashboard_display(state_manager)

    except StateException as e:
        error_context = ErrorContext(
            error_type="flow",
            message=f"Flow completion error: {str(e)}",
            details={"channel_id": state_manager.get_channel_id()}
        )
        error_response = ErrorHandler.handle_error(
            e,
            state_manager,
            error_context
        )
        return WhatsAppMessage.create_text(
            state_manager.get_channel_id(),
            error_response['data']['action']['details']['message']
        )
