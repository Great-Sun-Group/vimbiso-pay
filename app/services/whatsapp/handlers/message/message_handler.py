"""WhatsApp message handling implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.messaging.types import Message
from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator

from ... import auth_handlers as auth
from .flow_manager import FLOW_HANDLERS, initialize_flow
from .input_handler import MENU_ACTIONS, extract_input_value, get_action

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


def handle_menu_action(state_manager: Any, action: str) -> Message:
    """Handle menu action with proper state validation

    Returns:
        Message: Core message type
    """
    try:
        # Debug state
        logger.info(f"Current state: {state_manager._state}")

        # Get authentication state
        authenticated = state_manager.get("authenticated")
        logger.info(f"Authenticated value: {authenticated}")

        # If not authenticated, must login first - no action continuation
        if not authenticated:
            logger.info("Not authenticated, attempting login")
            return auth.handle_hi(state_manager)

        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {"authenticated": authenticated},
            {"authenticated"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # Map special flow types
        flow_type = action
        if action == "start_registration":
            flow_type = "registration"
        elif action == "upgrade_tier":
            flow_type = "upgrade"

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
        if action in MENU_ACTIONS:
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
                handler_module = __import__(f"app.services.whatsapp.handlers.credex.flows.{flow_type}", fromlist=[handler_name])
                handler_func = getattr(handler_module, handler_name)

                # Get credex service if needed
                credex_service = None
                if flow_type == "offer":
                    from services.credex.service import get_credex_service
                    credex_service = get_credex_service(state_manager)

                # Process step
                input_value = extract_input_value(message_text, message_type)
                return handler_func(state_manager, current_step, input_value, credex_service)
            else:
                raise ValueError(f"Unknown flow type: {flow_type}")

        # If not authenticated, attempt login
        if not state_manager.get("authenticated"):
            logger.info("Not authenticated, attempting login")
            return auth.handle_hi(state_manager)

        # Default to menu only if authenticated
        return auth.handle_action_menu(state_manager)

    except ValueError as e:
        logger.error(f"Message processing error: {str(e)}")
        return auth.handle_error(state_manager, "Message processing", e)
