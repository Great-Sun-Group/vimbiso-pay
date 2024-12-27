"""WhatsApp message handling implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator

from ... import auth_handlers as auth
from ...types import WhatsAppMessage
from .flow_manager import initialize_flow, FLOW_HANDLERS
from .input_handler import get_action, extract_input_value

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()

# Flow type mapping at module level
FLOW_TYPES: Dict[str, str] = {
    "offer": "offer",
    "accept": "accept",
    "decline": "decline",
    "cancel": "cancel",
    "start_registration": "registration",
    "upgrade_tier": "upgrade"
}


def handle_menu_action(state_manager: Any, action: str) -> WhatsAppMessage:
    """Handle menu action with proper state validation"""
    try:
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {"authenticated": state_manager.get("authenticated")},
            {"authenticated"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # Check authentication
        authenticated = state_manager.get("authenticated")
        if not authenticated:
            # Show login menu
            return WhatsAppMessage.from_core_message(
                auth.handle_action_menu(state_manager, login=True)
            )

        # Get flow type
        flow_type = FLOW_TYPES[action]

        # Initialize flow
        return initialize_flow(state_manager, flow_type)

    except ValueError as e:
        logger.error(f"Menu action error: {str(e)}")
        return auth.handle_error(state_manager, "Menu action", e)


def process_message(state_manager: Any, message_type: str, message_text: str) -> WhatsAppMessage:
    """Process incoming message enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {"channel": state_manager.get("channel")},
            {"channel"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # Log message processing start
        channel = state_manager.get("channel")
        audit.log_flow_event(
            "bot_service",
            "message_processing",
            None,
            {"message_type": message_type, "channel_id": channel["identifier"]},
            "in_progress"
        )

        # Get action from input
        action = get_action(message_text, message_type)

        # Handle menu action
        if action in FLOW_TYPES:
            return handle_menu_action(state_manager, action)

        # Handle active flow
        flow_data = state_manager.get("flow_data")
        if flow_data and isinstance(flow_data, dict):
            flow_type = flow_data.get("id")
            current_step = flow_data.get("current_step")

            if flow_type in FLOW_HANDLERS:
                # Get handler function
                handler_name = FLOW_HANDLERS[flow_type]
                handler_module = __import__(f"..{flow_type}.handler", fromlist=[handler_name])
                handler_func = getattr(handler_module, handler_name)

                # Process step
                input_value = extract_input_value(message_text, message_type)
                return handler_func(state_manager, current_step, input_value)

        # Default to menu
        return WhatsAppMessage.from_core_message(
            auth.handle_action_menu(state_manager)
        )

    except ValueError as e:
        logger.error(f"Message processing error: {str(e)}")
        return auth.handle_error(state_manager, "Message processing", e)
