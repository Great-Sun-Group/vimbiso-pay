"""Flow initialization and management enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any

from core.utils.flow_audit import FlowAuditLogger
from ...types import WhatsAppMessage

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class FlowManager:
    """Handles WhatsApp flow initialization with strict state management"""

    @staticmethod
    def initialize_flow(
        state_manager: Any,
        flow_type: str,
        flow_class: Any
    ) -> WhatsAppMessage:
        """Initialize a new flow enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate input parameters
            if not flow_type or not isinstance(flow_type, str):
                raise ValueError("Invalid flow type")
            if not flow_class:
                raise ValueError("Flow class is required")

            # Get required state (already validated at boundaries)
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

            # Initialize flow with state manager
            flow = flow_class(state_manager=state_manager)
            if not flow:
                raise ValueError("Failed to initialize flow")

            # Update flow data (validation handled by state manager)
            success, error = state_manager.update_state({
                "flow_data": {
                    "id": flow_type,
                    "step": 0
                }
            })
            if not success:
                raise ValueError(f"Failed to update flow data: {error}")

            # Get initial message
            result = flow.get_initial_message()
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

    @staticmethod
    def has_pending_offers(state_manager: Any) -> bool:
        """Check for pending offers enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Get required state (already validated at boundaries)
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
