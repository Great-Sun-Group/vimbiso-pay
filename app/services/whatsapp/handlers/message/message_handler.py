"""WhatsApp message handling implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.messaging.types import Message
from core.utils.exceptions import StateException
from core.utils.flow_audit import FlowAuditLogger

from ... import auth_handlers as auth
from .flow_manager import FLOW_HANDLERS, initialize_flow
from .input_handler import MENU_ACTIONS, extract_input_value, get_action

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


def handle_menu_action(state_manager: Any, action: str) -> Message:
    """Handle menu action

    Returns:
        Message: Core message type
    """
    try:
        # Let StateManager validate authentication
        state_manager.get("authenticated")

        # Map special flow types (after validation)
        flow_type = "registration" if action == "start_registration" else (
            "upgrade" if action == "upgrade_tier" else action
        )

        # Initialize flow (StateManager validates state)
        return initialize_flow(state_manager, flow_type)

    except StateException as e:
        logger.error(f"Menu action error: {str(e)}")
        return auth.handle_error(state_manager, "Menu action", e)


def process_message(state_manager: Any, message_type: str, message_text: str, message: Dict[str, Any] = None) -> Message:
    """Process incoming message enforcing SINGLE SOURCE OF TRUTH

    Returns:
        Message: Core message type with recipient and content
    """
    try:
        # Log message processing start (only log type)
        audit.log_flow_event(
            "bot_service",
            "message_processing",
            None,
            {"type": message_type},  # Only log message type
            "in_progress"
        )

        # Get action from input
        action = get_action(message_text, message_type, message)

        # Handle menu action
        if action in MENU_ACTIONS:
            return handle_menu_action(state_manager, action)

        # Let StateManager validate flow state structure
        flow_type = state_manager.get("flow_data")["flow_type"]  # StateManager validates
        current_step = state_manager.get("flow_data")["current_step"]  # StateManager validates

        # Get handler function
        handler_name = FLOW_HANDLERS[flow_type]
        handler_module = __import__(
            f"app.services.whatsapp.handlers.credex.flows.{flow_type}",
            fromlist=[handler_name]
        )
        handler_func = getattr(handler_module, handler_name)

        # Process step (service initialization handled by flow manager)
        input_value = extract_input_value(message_text, message_type)
        return handler_func(state_manager, current_step, input_value)

    except StateException as e:
        logger.error(f"Message processing error: {str(e)}")
        return auth.handle_error(state_manager, "Message processing", e)
