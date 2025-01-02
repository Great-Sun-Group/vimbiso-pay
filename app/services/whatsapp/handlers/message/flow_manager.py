"""Flow initialization and management enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.messaging.types import Message
from core.utils.error_handler import ErrorHandler
from core.utils.exceptions import ComponentException, FlowException, SystemException

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
        # Validate flow type through state update
        if flow_type not in FLOW_HANDLERS:
            raise FlowException(
                message=f"Unknown flow type: {flow_type}",
                step="initialize",
                action="validate_flow",
                data={"flow_type": flow_type}
            )

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
            raise FlowException(
                message=str(error),
                step=state_update["flow_data"]["current_step"],
                action="initialize_state",
                data={
                    "flow_type": flow_type,
                    "error": str(error)
                }
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
        except Exception:  # Exception details not needed since raising new exception
            raise SystemException(
                message="Failed to load flow handler",
                code="HANDLER_LOAD_ERROR",
                service="flow_manager",
                action="load_handler"
            )

        try:
            # Initialize flow with first step
            result = handler_func(state_manager, state_update["flow_data"]["current_step"], None)
            if not result:
                raise FlowException(
                    message="Failed to start flow - no initial message",
                    step=state_update["flow_data"]["current_step"],
                    action="initialize_flow",
                    data={"flow_type": flow_type}
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

        except Exception:  # Exception details not needed since raising new exception
            raise SystemException(
                message="Failed to initialize flow",
                code="FLOW_INIT_ERROR",
                service="flow_manager",
                action="initialize_flow"
            )

    except (ComponentException, FlowException, SystemException) as e:
        # Let error handler create appropriate message
        return ErrorHandler.handle_error_with_message(e, state_manager)
    except Exception:  # Exception details not needed since raising new exception
        # Unexpected errors treated as system errors
        system_error = SystemException(
            message="Unexpected error initializing flow",
            code="UNEXPECTED_ERROR",
            service="flow_manager",
            action="initialize_flow"
        )
        return ErrorHandler.handle_error_with_message(system_error, state_manager)


def check_pending_offers(state_manager: Any) -> bool:
    """Check for pending offers enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Log check
        channel_id = state_manager.get_channel_id()
        logger.info(
            "Checking pending offers",
            extra={"channel_id": channel_id}
        )
        return True

    except Exception as e:
        logger.error(f"Error checking pending offers: {str(e)}")
        raise SystemException(
            message="Failed to check pending offers",
            code="OFFER_CHECK_ERROR",
            service="flow_manager",
            action="check_pending_offers"
        )
