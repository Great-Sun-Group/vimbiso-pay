"""Flow initialization and management for WhatsApp conversations

This module provides the FlowManager class which handles the lifecycle of WhatsApp
conversation flows with member-centric state management. Key features include:

- Member-centric state management with member_id as SINGLE SOURCE OF TRUTH at top level
- Flow initialization and state updates with validation
- Error handling and recovery mechanisms
- Comprehensive audit logging
- State preservation across flow transitions
"""
import logging
from typing import Any, Dict, Optional

from core.utils.flow_audit import FlowAuditLogger

from ...types import WhatsAppMessage

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class FlowManager:
    """Handles WhatsApp flow initialization and state management"""

    def __init__(self, service: Any):
        self.service = service

    def _get_member_info(self) -> Optional[str]:
        """Get member ID from top level state ONLY

        Returns:
            Optional[str]: member_id from top level state
        """
        try:
            # Access member_id ONLY from top level - SINGLE SOURCE OF TRUTH
            return self.service.user.state.state.get("member_id")
        except Exception as e:
            logger.error(f"Error getting member info: {str(e)}")
            audit.log_flow_event(
                "bot_service",
                "member_info_error",
                None,
                {"error": str(e)},
                "failure"
            )
            return None

    def initialize_flow(self, flow_type: str, flow_class: Any, **kwargs) -> WhatsAppMessage:
        """Initialize a new flow with proper state management"""
        try:
            # Log flow start attempt
            audit.log_flow_event(
                "bot_service",
                "flow_start_attempt",
                None,
                {
                    "flow_type": flow_type,
                    "flow_class": flow_class.__name__ if hasattr(flow_class, '__name__') else str(flow_class),
                    **kwargs
                },
                "in_progress"
            )

            # Get member_id from top level state ONLY - SINGLE SOURCE OF TRUTH
            state = self.service.user.state.state
            member_id = state.get("member_id") if state else None
            channel_id = kwargs.get("channel", {}).get("identifier")

            # Log full state for debugging
            logger.debug("=== Flow Start State Debug ===")
            logger.debug(f"Full state: {state}")
            logger.debug(f"Member ID from top level: {member_id}")
            logger.debug(f"Channel ID from kwargs: {channel_id}")
            logger.debug(f"Authenticated: {state.get('authenticated') if state else False}")
            logger.debug("============================")

            # Validate member_id exists at top level
            if not member_id:
                error_msg = "Missing member ID"
                logger.error(f"Flow start error: {error_msg}")
                audit.log_flow_event(
                    "bot_service",
                    "flow_start_error",
                    None,
                    {
                        "error": error_msg,
                        "state": state,
                        "channel_id": channel_id
                    },
                    "failure"
                )
                return WhatsAppMessage.create_text(channel_id, f"❌ Failed to start flow: {error_msg}")

            # Create flow with minimal state
            flow_id = f"{flow_type}_{member_id}"
            flow = flow_class(id=flow_id, steps=[])
            flow.credex_service = self.service.credex_service

            # Get flow state and update through state manager
            flow_data = flow.get_state().to_dict()
            self.service.user.state.update_state({"flow_data": flow_data}, "flow_init")

            # Get initial message
            result = (flow.current_step.get_message(flow.data) if flow.current_step
                      else WhatsAppMessage.create_text(channel_id, "Flow not properly initialized"))

            audit.log_flow_event(
                "bot_service",
                "flow_start_success",
                None,
                {"flow_id": flow_id},
                "success"
            )
            return result

        except Exception as e:
            logger.error(f"Flow start error: {str(e)}")
            audit.log_flow_event(
                "bot_service",
                "flow_start_error",
                None,
                {"error": str(e)},
                "failure"
            )
            return WhatsAppMessage.create_text(
                kwargs.get("channel", {}).get("identifier"),
                f"❌ Failed to start flow: {str(e)}"
            )

    def _get_pending_offers(self) -> Dict[str, Any]:
        """Get current account data with pending offers from state"""
        return self.service.user.state.state.get("current_account", {})
