"""WhatsApp message handling implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.messaging.types import Message
from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator

from ... import auth_handlers as auth
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


def handle_menu_action(state_manager: Any, action: str) -> Message:
    """Handle menu action with proper state validation

    Returns:
        Message: Core message type
    """
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
            # Update state and show login menu
            success, error = state_manager.update_state({"login_required": True})
            if not success:
                raise ValueError(f"Failed to update state: {error}")

            return auth.handle_action_menu(state_manager)

        # Get flow type
        flow_type = FLOW_TYPES[action]

        # Initialize flow
        return initialize_flow(state_manager, flow_type)

    except ValueError as e:
        logger.error(f"Menu action error: {str(e)}")
        return auth.handle_error(state_manager, "Menu action", e)


def process_message(state_manager: Any, message_type: str, message_text: str, message: Dict[str, Any] = None) -> Message:
    """Process incoming message enforcing SINGLE SOURCE OF TRUTH

    Returns:
        Message: Core message type with recipient and content
    """
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
        action = get_action(message_text, message_type, message)

        # Handle menu action
        if action in FLOW_TYPES:
            return handle_menu_action(state_manager, action)

        # Handle active flow
        validation = StateValidator.validate_before_access(
            {"flow_data": state_manager.get("flow_data")},
            {"flow_data"}
        )
        if validation.is_valid:
            flow_data = state_manager.get("flow_data")
            flow_type = flow_data["id"]
            current_step = flow_data["current_step"]

            if flow_type in FLOW_HANDLERS:
                # Get handler function
                handler_name = FLOW_HANDLERS[flow_type]
                handler_module = __import__(f"..credex.flows.{flow_type}", fromlist=[handler_name])
                handler_func = getattr(handler_module, handler_name)

                # Process step
                input_value = extract_input_value(message_text, message_type)
                return handler_func(state_manager, current_step, input_value)
            else:
                raise ValueError(f"Unknown flow type: {flow_type}")

        # Default to menu
        return auth.handle_action_menu(state_manager)

    except ValueError as e:
        logger.error(f"Message processing error: {str(e)}")
        return auth.handle_error(state_manager, "Message processing", e)
