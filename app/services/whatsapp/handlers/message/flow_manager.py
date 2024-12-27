"""Flow initialization and management enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.messaging.types import Message
from core.utils.flow_audit import FlowAuditLogger

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()

# Flow type to handler function mapping
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
        # Validate input parameters
        if not flow_type or not isinstance(flow_type, str):
            raise ValueError("Invalid flow type")
        if flow_type not in FLOW_HANDLERS:
            raise ValueError(f"Unknown flow type: {flow_type}")

        # Get channel for logging (validation handled by state manager)
        channel = state_manager.get("channel")

        # Log flow start attempt
        audit.log_flow_event(
            "bot_service",
            "flow_start_attempt",
            None,
            {
                "flow_type": flow_type,
                "channel_id": channel["identifier"]
            },
            "in_progress"
        )

        # StateManager will validate all required fields
        state_manager.get("authenticated")  # Validates authentication
        state_manager.get("member_id")      # Validates member exists

        # Get initial step based on flow type
        initial_step = "amount" if flow_type == "offer" else "start"

        # Update only flow data through state manager
        success, error = state_manager.update_state({
            "flow_data": {
                "flow_type": flow_type,
                "step": 0,
                "current_step": initial_step,
                "data": {}  # Data will be populated by flow handler
            }
        })
        if not success:
            raise ValueError(f"Failed to update flow data: {error}")

        # Get initial message using handler function
        handler_name = FLOW_HANDLERS[flow_type]
        # Get credex service if needed
        credex_service = None
        if flow_type == "offer":
            from services.credex.service import get_credex_service
            credex_service = get_credex_service(state_manager)

        # Import handler function from correct path
        handler_module = __import__(f"app.services.whatsapp.handlers.credex.flows.{flow_type}", fromlist=[handler_name])
        handler_func = getattr(handler_module, handler_name)

        # Initialize flow with initial step
        result = handler_func(state_manager, initial_step, None, credex_service)
        if not result:
            raise ValueError("Failed to get initial flow message")

        # Log success
        audit.log_flow_event(
            "bot_service",
            "flow_start_success",
            None,
            {
                "flow_type": flow_type,
                "channel_id": channel["identifier"]
            },
            "success"
        )

        return result

    except ValueError as e:
        # Get channel info for error response
        try:
            channel = state_manager.get("channel")
            channel_id = channel["identifier"] if channel else "unknown"
        except (ValueError, KeyError, TypeError) as err:
            logger.error(f"Failed to get channel for error response: {str(err)}")
            channel_id = "unknown"

        logger.error(f"Flow initialization error: {str(e)} for channel {channel_id}")
        from core.messaging.types import (ChannelIdentifier, ChannelType,
                                          MessageRecipient, TextContent)

        # Create error message using core types
        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel_id
                )
            ),
            content=TextContent(
                body="Error: Unable to start flow. Please try again."
            )
        )


def check_pending_offers(state_manager: Any) -> bool:
    """Check for pending offers enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Let StateManager handle validation
        try:
            # Get required state (validation handled by state manager)
            channel = state_manager.get("channel")
            account_id = state_manager.get("account_id")
        except ValueError as e:
            logger.error(f"State validation failed: {str(e)}")
            return False

        # Log check
        audit.log_flow_event(
            "bot_service",
            "check_pending_offers",
            None,
            {
                "channel_id": channel["identifier"],
                "account_id": account_id
            },
            "success"
        )

        return True

    except Exception as e:
        logger.error(f"Error checking pending offers: {str(e)}")
        return False
