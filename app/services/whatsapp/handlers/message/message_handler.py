"""WhatsApp message handling implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.messaging.types import Message
from core.utils.exceptions import StateException
from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ErrorContext

from ... import auth_handlers as auth
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
        # First check if we're in a multi-step flow
        current_flow = state_manager.get_flow_type()
        if current_flow and current_flow in FLOW_HANDLERS:
            # Get current step
            current_step = state_manager.get_current_step()
            if not current_step:
                error_context = ErrorContext(
                    error_type="flow",
                    message="Missing flow step",
                    step_id=None,
                    details={"flow_type": current_flow}
                )
                error_response = ErrorHandler.handle_error(
                    StateException("Missing flow step"),
                    state_manager,
                    error_context
                )
                return auth.create_error_message(state_manager, error_response)

            # Extract input value and process step
            input_value = extract_input_value(message_text, message_type, message)
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
                error_context = ErrorContext(
                    error_type="flow",
                    message=f"Error processing flow step: {str(e)}",
                    step_id=current_step,
                    details={
                        "flow_type": current_flow,
                        "input": input_value
                    }
                )
                error_response = ErrorHandler.handle_error(
                    e,
                    state_manager,
                    error_context
                )
                return auth.create_error_message(state_manager, error_response)

        # Not in a flow - check if input matches a menu action
        message_text = message_text.strip().lower()
        if message_text in MENU_ACTIONS:
            # Map special flow types
            flow_type = "registration" if message_text == "start_registration" else (
                "upgrade" if message_text == "upgrade_tier" else message_text
            )

            # Only initialize flow if it's a multi-step flow
            if flow_type in FLOW_HANDLERS:
                # Let StateManager validate authentication
                state_manager.get("authenticated")
                return initialize_flow(state_manager, flow_type)

            # For non-flow actions like refresh, return to dashboard
            return handle_dashboard_display(state_manager)

        # For unrecognized inputs, show dashboard
        return handle_dashboard_display(state_manager)

    except StateException as e:
        error_context = ErrorContext(
            error_type="message",
            message=f"Message processing error: {str(e)}",
            details={
                "message_type": message_type,
                "message_text": message_text
            }
        )
        error_response = ErrorHandler.handle_error(
            e,
            state_manager,
            error_context
        )
        return auth.create_error_message(state_manager, error_response)
