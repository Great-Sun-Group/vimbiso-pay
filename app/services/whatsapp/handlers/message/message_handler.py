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


def process_message(state_manager: Any, message_type: str, message_text: str, message: Dict[str, Any] = None) -> Message:
    """Process incoming message enforcing SINGLE SOURCE OF TRUTH

    Returns:
        Message: Core message type with recipient and content
    """
    try:
        # Log message processing start
        audit.log_flow_event(
            "bot_service",
            "message_processing",
            None,
            {"type": message_type},
            "in_progress"
        )

        # Get action from input
        action = get_action(message_text, state_manager, message_type, message)

        # Get current state
        flow_data = state_manager.get("flow_data")

        # Handle menu actions that start multi-step flows
        if action in MENU_ACTIONS:
            # Map special flow types
            flow_type = "registration" if action == "start_registration" else (
                "upgrade" if action == "upgrade_tier" else action
            )

            # Only initialize flow if it's a multi-step flow
            if flow_type in FLOW_HANDLERS:
                # Let StateManager validate authentication
                state_manager.get("authenticated")
                return initialize_flow(state_manager, flow_type)

            # For non-flow actions like refresh, return to dashboard
            from ...member.dashboard import handle_dashboard_display
            return handle_dashboard_display(state_manager)

        # If in a multi-step flow, process the step
        if flow_data and flow_data.get("flow_type") in FLOW_HANDLERS:
            current_flow = flow_data["flow_type"]
            current_step = flow_data.get("current_step")

            if not current_step:
                raise StateException("Missing flow step")

            # Get handler function
            handler_name = FLOW_HANDLERS[current_flow]

            try:
                # Import and get handler function
                if current_flow in ["registration", "upgrade"]:
                    # Member-related flows
                    handler_module = __import__(
                        f"services.whatsapp.handlers.member.{current_flow}",
                        fromlist=[handler_name]
                    )
                    handler_func = getattr(handler_module, handler_name)
                else:
                    # CredEx-related flows (offer, accept, decline, cancel)
                    logger.debug(f"Getting credex flow handler: {current_flow}")
                    from ...credex.flows import offer, action
                    if current_flow == "offer":
                        handler_func = offer.process_offer_step
                    else:
                        handler_func = getattr(action, handler_name)
                    logger.debug(f"Got handler function: {handler_func}")
            except Exception as e:
                logger.error(f"Failed to import handler: {str(e)}")
                raise StateException(f"Failed to load flow handler: {str(e)}")

            # Process step through state update
            input_value = extract_input_value(message_text, message_type)
            logger.debug(f"Processing flow input: '{input_value}' for step '{current_step}'")

            result = handler_func(state_manager, current_step, input_value)
            logger.debug(f"Flow handler result: {result}")
            return result

        # Default to dashboard for any other input
        from ...member.dashboard import handle_dashboard_display
        return handle_dashboard_display(state_manager)

    except StateException as e:
        logger.error(f"Message processing error: {str(e)}")
        return auth.handle_error(state_manager, "Message processing", e)
