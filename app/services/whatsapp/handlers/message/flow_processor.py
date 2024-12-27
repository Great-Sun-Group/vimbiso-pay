"""Flow processing and continuation logic enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional

from core.utils.flow_audit import FlowAuditLogger
from ...types import WhatsAppMessage
from ..member.dashboard import handle_dashboard_display

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()

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
        # Let StateManager handle validation
        channel = state_manager.get("channel")
        flow_type = flow_data.get("flow_type") if isinstance(flow_data, dict) else None

        if not flow_type:
            raise ValueError("Invalid flow type")

        # Get handler function
        handler_name = FLOW_HANDLERS.get(flow_type)
        if not handler_name:
            raise ValueError(f"Unsupported flow type: {flow_type}")

        handler_module = __import__(f"services.whatsapp.handlers.credex.flows.{flow_type}", fromlist=[handler_name])
        handler_func = getattr(handler_module, handler_name)

        # Get current step
        current_step = flow_data.get("current_step")
        if not current_step:
            raise ValueError("Missing current step in flow data")

        # Process step
        result = handler_func(state_manager, current_step, input_value)
        if not result:
            # Clear flow data
            success, error = state_manager.update_state({"flow_data": None})
            if not success:
                raise ValueError(f"Failed to clear flow data: {error}")

            # Show dashboard
            return handle_dashboard_display(
                state_manager,
                success_message="Operation completed successfully"
            )

        return result

    except ValueError as e:
        # Get channel info for error response
        try:
            channel = state_manager.get("channel")
            channel_id = channel["identifier"] if channel else "unknown"
        except (ValueError, KeyError, TypeError) as err:
            logger.error(f"Failed to get channel for error response: {str(err)}")
            channel_id = "unknown"

        logger.error(f"Flow processing error: {str(e)} for channel {channel_id}")
        return WhatsAppMessage.create_text(
            channel_id,
            "Error: Unable to process flow. Please try again."
        )


def handle_flow_completion(state_manager: Any, success_message: Optional[str] = None) -> WhatsAppMessage:
    """Handle flow completion enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Let StateManager handle validation
        channel = state_manager.get("channel")

        # Log completion
        audit.log_flow_event(
            "bot_service",
            "flow_complete",
            None,
            {"channel_id": channel["identifier"]},
            "success"
        )

        # Clear flow data
        success, error = state_manager.update_state({"flow_data": None})
        if not success:
            raise ValueError(f"Failed to clear flow data: {error}")

        # Show dashboard
        return handle_dashboard_display(
            state_manager,
            success_message=success_message or "Operation completed successfully"
        )

    except ValueError as e:
        # Get channel info for error response
        try:
            channel = state_manager.get("channel")
            channel_id = channel["identifier"] if channel else "unknown"
        except (ValueError, KeyError, TypeError) as err:
            logger.error(f"Failed to get channel for error response: {str(err)}")
            channel_id = "unknown"

        logger.error(f"Flow completion error: {str(e)} for channel {channel_id}")
        return WhatsAppMessage.create_text(
            channel_id,
            "Error: Unable to complete flow. Please try again."
        )
