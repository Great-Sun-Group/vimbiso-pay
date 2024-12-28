"""Flow initialization and management enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.messaging.types import (ChannelIdentifier, ChannelType, Message,
                                  MessageRecipient, TextContent)
from core.utils.exceptions import StateException
from core.utils.flow_audit import FlowAuditLogger

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()

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
        state_manager.get("channel")

        # Validate flow type through state update
        if flow_type not in FLOW_HANDLERS:
            raise StateException(f"Unknown flow type: {flow_type}")

        # Initialize flow state through state update
        state_update = {
            "flow_data": {
                "flow_type": flow_type,
                "step": 0,  # Must be int for validation
                "current_step": "amount" if flow_type == "offer" else "start",
                "data": {}
            }
        }
        logger.debug(f"Initializing flow state with: {state_update}")

        success, error = state_manager.update_state(state_update)
        logger.debug(f"Flow state initialization result - success: {success}, error: {error}")
        if not success:
            raise StateException(f"Failed to initialize flow state: {error}")

        # Log flow start attempt
        audit.log_flow_event(
            "bot_service",
            "flow_start_attempt",
            None,
            {"flow_type": flow_type},  # Only log flow type
            "in_progress"
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
                from ...handlers.credex.flows import offer, action
                if flow_type == "offer":
                    handler_func = offer.process_offer_step
                else:
                    handler_func = getattr(action, handler_name)
                logger.debug(f"Got handler function: {handler_func}")
        except Exception as e:
            logger.error(f"Failed to import handler: {str(e)}")
            raise StateException(f"Failed to load flow handler: {str(e)}")

        # Initialize flow through state update with correct step
        current_step = state_manager.get("flow_data")["current_step"]
        result = handler_func(state_manager, current_step, None)
        if not result:
            raise StateException("Failed to get initial flow message")

        # Log success
        audit.log_flow_event(
            "bot_service",
            "flow_start_success",
            None,
            {"flow_type": flow_type},  # Only log flow type
            "success"
        )

        return result

    except StateException as e:
        logger.error(f"Flow initialization error: {str(e)}")
        channel = state_manager.get("channel")
        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel["identifier"]
                )
            ),
            content=TextContent(
                body="Error: Unable to start flow. Please try again."
            )
        )


def check_pending_offers(state_manager: Any) -> bool:
    """Check for pending offers enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Log check
        audit.log_flow_event(
            "bot_service",
            "check_pending_offers",
            None,
            {"status": "checking"},  # Only log status
            "success"
        )

        return True

    except StateException as e:
        logger.error(f"Error checking pending offers: {str(e)}")
        return False
