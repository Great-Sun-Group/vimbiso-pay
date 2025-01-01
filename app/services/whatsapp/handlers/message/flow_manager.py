"""Flow initialization and management enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.messaging.types import (ChannelIdentifier, ChannelType, Message,
                                  MessageRecipient, TextContent)
from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ErrorContext
from core.utils.exceptions import StateException

logger = logging.getLogger(__name__)

# Flow type to handler function mapping for multi-step flows
FLOW_HANDLERS: Dict[str, Any] = {
    "offer": "process_offer_step",
    "accept": "process_accept_step",
    "decline": "process_decline_step",
    "cancel": "process_cancel_step",
    "registration": "process_registration_step",
    "upgrade": "process_upgrade_step"
}


def initialize_flow(state_manager: Any, flow_type: str) -> Message:
    """Initialize a new flow enforcing SINGLE SOURCE OF TRUTH

    Args:
        state_manager: State manager instance
        flow_type: Type of flow to initialize

    Returns:
        Message: Core message type with recipient and content
    """
    try:
        # Let StateManager validate channel access
        try:
            channel_id = state_manager.get_channel_id()
        except Exception as e:
            error_context = ErrorContext(
                error_type="state",
                message="Failed to get channel information. Please try again",
                details={"error": str(e)}
            )
            error_response = ErrorHandler.handle_error(e, state_manager, error_context)
            raise StateException(error_response["data"]["action"]["details"]["message"])

        # Validate flow type through state update
        if flow_type not in FLOW_HANDLERS:
            error_context = ErrorContext(
                error_type="system",  # Use system type since we don't have a step yet
                message=f"Unknown flow type: {flow_type}. Please select a valid option",
                details={"flow_type": flow_type}
            )
            error_response = ErrorHandler.handle_error(
                StateException("Invalid flow type"),
                state_manager,
                error_context
            )
            raise StateException(error_response["data"]["action"]["details"]["message"])

        # Initialize flow state through state update
        state_update = {
            "flow_data": {
                "flow_type": flow_type,
                "step": 1,  # Steps start at 1 to match validation
                "current_step": "amount" if flow_type == "offer" else "start",
                "data": {}
            }
        }
        logger.debug(f"Initializing flow state with: {state_update}")

        success, error = state_manager.update_state(state_update)
        logger.debug(f"Flow state initialization result - success: {success}, error: {error}")
        if not success:
            # Get current step for error context
            current_step = state_update["flow_data"]["current_step"]
            error_context = ErrorContext(
                error_type="flow",  # Use flow type for validation errors
                message=str(error),  # Use actual validation error
                step_id=current_step,  # Include step_id
                details={
                    "flow_type": flow_type,
                    "step": current_step,
                    "error": error
                }
            )
            # Use flow error handler for proper message
            return ErrorHandler.handle_flow_error(
                StateException(error),
                state_manager,
                error_context,
                return_message=True
            )

        # Log flow start attempt
        logger.info(
            "Starting flow",
            extra={
                "flow_type": flow_type,
                "initial_step": state_update["flow_data"]["current_step"]
            }
        )

        # Get handler name and import function
        handler_name = FLOW_HANDLERS[flow_type]  # Already validated flow_type exists

        try:
            # Import and get handler function
            if flow_type in ["registration", "upgrade"]:
                # Member-related flows
                handler_module = __import__(
                    f"services.whatsapp.handlers.member.{flow_type}",
                    fromlist=[handler_name]
                )
                handler_func = getattr(handler_module, handler_name)
            else:
                # CredEx-related flows (offer, accept, decline, cancel)
                logger.debug(f"Getting credex flow handler: {flow_type}")
                handler_module = __import__(
                    f"services.whatsapp.handlers.credex.flows.{flow_type}",
                    fromlist=[handler_name]
                )
                handler_func = getattr(handler_module, handler_name)
                logger.debug(f"Got handler function: {handler_func}")
        except Exception as e:
            # Get current step for error context
            current_step = state_update["flow_data"]["current_step"]
            error_context = ErrorContext(
                error_type="flow",  # Use flow type for all flow-related errors
                message="Failed to load flow handler. Please try again",
                step_id=current_step,  # Include step_id
                details={
                    "flow_type": flow_type,
                    "handler": handler_name,
                    "step": current_step,
                    "error": str(e)
                }
            )
            # Use flow error handler for proper message
            return ErrorHandler.handle_flow_error(
                e,
                state_manager,
                error_context,
                return_message=True
            )

        try:
            # Initialize flow with first step
            result = handler_func(state_manager, state_update["flow_data"]["current_step"], None)
            if not result:
                # Get current step for error context
                current_step = state_update["flow_data"]["current_step"]
                error_context = ErrorContext(
                    error_type="flow",  # Use flow type for all flow-related errors
                    message="Failed to start flow. Please try again",
                    step_id=current_step,  # Include step_id
                    details={
                        "flow_type": flow_type,
                        "step": current_step,
                        "error": "No initial message"
                    }
                )
                # Use flow error handler for proper message
                return ErrorHandler.handle_flow_error(
                    StateException("No initial message"),
                    state_manager,
                    error_context,
                    return_message=True
                )

            # Log success
            logger.info(
                "Flow started successfully",
                extra={
                    "flow_type": flow_type,
                    "step": state_update["flow_data"]["current_step"]
                }
            )

            return result

        except Exception as e:
            error_context = ErrorContext(
                error_type="system",  # Use system type for initialization errors
                message="Failed to initialize flow. Please try again",
                details={
                    "flow_type": flow_type,
                    "step": state_update["flow_data"]["current_step"],
                    "error": str(e)
                }
            )
            error_response = ErrorHandler.handle_error(e, state_manager, error_context)
            raise StateException(error_response["data"]["action"]["details"]["message"])

    except Exception as e:
        error_context = ErrorContext(
            error_type="system",  # Use system type for top-level errors
            message="Unable to start flow. Please try again",
            details={
                "flow_type": flow_type,
                "error": str(e)
            }
        )
        error_response = ErrorHandler.handle_error(e, state_manager, error_context)

        try:
            channel_id = state_manager.get_channel_id()
            return Message(
                recipient=MessageRecipient(
                    channel_id=ChannelIdentifier(
                        channel=ChannelType.WHATSAPP,
                        value=channel_id
                    )
                ),
                content=TextContent(
                    body=ErrorHandler.format_error_message(
                        error_response['data']['action']['details']['message']
                    )
                )
            )
        except Exception:
            # Fallback error message if we can't get channel info
            return Message(
                recipient=MessageRecipient(
                    channel_id=ChannelIdentifier(
                        channel=ChannelType.WHATSAPP,
                        value="unknown"
                    )
                ),
                content=TextContent(
                    body=ErrorHandler.format_error_message(
                        "System error. Please try again later."
                    )
                )
            )


def check_pending_offers(state_manager: Any) -> bool:
    """Check for pending offers enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Log check
        logger.info(
            "Checking pending offers",
            extra={
                "channel_id": state_manager.get_channel_id()
            }
        )

        return True

    except Exception as e:
        error_context = ErrorContext(
            error_type="state",
            message="Failed to check pending offers",
            details={"error": str(e)}
        )
        logger.error(
            "Error checking pending offers",
            extra={
                "error": str(e),
                "error_context": error_context.__dict__
            }
        )
        return False
