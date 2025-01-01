"""WhatsApp message handling implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.messaging.types import Message
from core.utils.error_handler import ErrorHandler
from core.utils.exceptions import StateException
from ..member.display import handle_dashboard_display
from .flow_manager import FLOW_HANDLERS, initialize_flow
from .input_handler import MENU_ACTIONS, extract_input_value

logger = logging.getLogger(__name__)


def process_message(state_manager: Any, message_type: str, message_text: str, message: Dict[str, Any] = None) -> Message:
    """Process incoming message enforcing SINGLE SOURCE OF TRUTH

    Returns:
        Message: Core message type with recipient and content
    """
    try:
        # Check if we're in a flow
        flow_data = state_manager.get("flow_data")
        if flow_data:
            current_flow = flow_data.get("flow_type")
            current_step = flow_data.get("current_step")

            # Check if we have a valid flow
            if current_flow in FLOW_HANDLERS:
                # Extract input value and process step
                input_value = extract_input_value(message_text, message_type, message, state_manager)
                logger.debug(f"Processing flow input: '{input_value}' for step '{current_step}'")

                try:
                    # Get handler function
                    handler_name = FLOW_HANDLERS[current_flow]

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
                        handler_module = __import__(
                            f"services.whatsapp.handlers.credex.flows.{current_flow}",
                            fromlist=[handler_name]
                        )
                        handler_func = getattr(handler_module, handler_name)
                        logger.debug(f"Got handler function: {handler_func}")

                    # Process step and return result
                    result = handler_func(state_manager, current_step, input_value)
                    logger.debug(f"Flow handler result: {result}")
                    return result

                except Exception as e:
                    # Handle flow step error
                    return ErrorHandler.handle_flow_error(
                        state_manager,
                        e,
                        step_id=current_step,
                        return_message=True
                    )

            # Not in a valid flow - treat as menu action or show dashboard
            message_text = message_text.strip().lower()
            if message_text in MENU_ACTIONS:
                return handle_menu_action(state_manager, message_text)
            return handle_dashboard_display(state_manager)

        # Not in a flow - check if input matches a menu action
        message_text = message_text.strip().lower()
        if message_text in MENU_ACTIONS:
            return handle_menu_action(state_manager, message_text)

        # For unrecognized inputs, show dashboard
        return handle_dashboard_display(state_manager)

    except StateException as e:
        # Handle top-level message error
        return ErrorHandler.handle_flow_error(
            state_manager,
            e,
            return_message=True
        )


def handle_menu_action(state_manager: Any, message_text: str) -> Message:
    """Handle menu action enforcing SINGLE SOURCE OF TRUTH

    Args:
        state_manager: State manager instance
        message_text: Menu action text

    Returns:
        Message: Core message type with recipient and content
    """
    # Reset flow with proper structure
    state_manager.update_state({
        "flow_data": {
            "flow_type": "dashboard",
            "step": 0,
            "current_step": "main",
            "data": {}
        }
    })

    # Map special flow types
    flow_type = "registration" if message_text == "start_registration" else (
        "upgrade" if message_text == "upgrade_tier" else message_text
    )

    # Only initialize flow if it's a multi-step flow
    if flow_type in FLOW_HANDLERS:
        # Let StateManager validate authentication for new flows
        state_manager.get("authenticated")
        return initialize_flow(state_manager, flow_type)

    # For non-flow actions like refresh, return to dashboard
    return handle_dashboard_display(state_manager)
