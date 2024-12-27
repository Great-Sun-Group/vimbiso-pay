"""Flow initialization and management enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator
from ...types import WhatsAppMessage

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


def initialize_flow(state_manager: Any, flow_type: str) -> WhatsAppMessage:
    """Initialize a new flow enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate input parameters
        if not flow_type or not isinstance(flow_type, str):
            raise ValueError("Invalid flow type")
        if flow_type not in FLOW_HANDLERS:
            raise ValueError(f"Unknown flow type: {flow_type}")

        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {
                "channel": state_manager.get("channel"),
                "member_id": state_manager.get("member_id"),
                "authenticated": state_manager.get("authenticated")
            },
            {"channel", "member_id", "authenticated"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # Get required state
        channel = state_manager.get("channel")
        member_id = state_manager.get("member_id")
        authenticated = state_manager.get("authenticated")

        # Validate flow requirements
        if not authenticated:
            raise ValueError("Authentication required to start flow")
        if not member_id:
            raise ValueError("Member ID required to start flow")

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

        # Update flow data (validation handled by state manager)
        success, error = state_manager.update({
            "flow_data": {
                "id": flow_type,
                "step": 0,
                "current_step": "start"
            }
        })
        if not success:
            raise ValueError(f"Failed to update flow data: {error}")

        # Get initial message using handler function
        handler_name = FLOW_HANDLERS[flow_type]
        handler_module = __import__(f"..{flow_type}.handler", fromlist=[handler_name])
        handler_func = getattr(handler_module, handler_name)

        result = handler_func(state_manager, "start")
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
        return WhatsAppMessage.create_text(
            channel_id,
            "Error: Unable to start flow. Please try again."
        )


def check_pending_offers(state_manager: Any) -> bool:
    """Check for pending offers enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {
                "channel": state_manager.get("channel"),
                "member_id": state_manager.get("member_id"),
                "account_id": state_manager.get("account_id")
            },
            {"channel", "member_id", "account_id"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # Get required state
        channel = state_manager.get("channel")
        member_id = state_manager.get("member_id")
        account_id = state_manager.get("account_id")

        # Validate offer check requirements
        if not member_id:
            logger.error("Member ID required to check offers")
            return False
        if not account_id:
            logger.error("Account ID required to check offers")
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

    except ValueError as e:
        logger.error(f"Error checking pending offers: {str(e)}")
        return False
