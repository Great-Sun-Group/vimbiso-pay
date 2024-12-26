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
from core.messaging.flow import FlowState

from ...types import WhatsAppMessage
from ...state_manager import StateManager

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

    def _validate_service(self) -> Optional[str]:
        """Validate service initialization

        Returns:
            Optional[str]: Error message if validation fails
        """
        try:
            if not self.service.credex_service:
                return "CredEx service not initialized"

            if not hasattr(self.service.credex_service, '_parent_service'):
                return "Service missing parent reference"

            if not hasattr(self.service.credex_service, 'services'):
                return "Service missing required services"

            if not self.service.credex_service.services:
                return "Service has no initialized sub-services"

            return None

        except Exception as e:
            logger.error(f"Service validation error: {str(e)}")
            return str(e)

    def initialize_flow(self, flow_type: str, flow_class: Any) -> WhatsAppMessage:
        """Initialize a new flow with proper state management"""
        try:
            # Log flow start attempt
            audit.log_flow_event(
                "bot_service",
                "flow_start_attempt",
                None,
                {
                    "flow_type": flow_type,
                    "flow_class": flow_class.__name__ if hasattr(flow_class, '__name__') else str(flow_class)
                },
                "in_progress"
            )

            # Get member_id from top level state ONLY - SINGLE SOURCE OF TRUTH
            state = self.service.user.state.state
            member_id = state.get("member_id") if state else None
            # Get channel info from state - SINGLE SOURCE OF TRUTH
            channel_id = state.get("channel", {}).get("identifier") if state else None

            # Log full state for debugging
            logger.debug("=== Flow Start State Debug ===")
            logger.debug(f"Full state: {state}")
            logger.debug(f"Member ID from top level: {member_id}")
            logger.debug(f"Channel ID from state: {channel_id}")
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

            # Validate service initialization
            error_msg = self._validate_service()
            if error_msg:
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

            # Create flow ID from type and member ID
            flow_id = f"{flow_type}_{member_id}"

            # Initialize flow state with member_id from top level (SINGLE SOURCE OF TRUTH)
            flow_state = FlowState.create(
                flow_id=flow_id,
                member_id=member_id,  # From top level - SINGLE SOURCE OF TRUTH
                flow_type=flow_type
            )

            # Add channel info to state data (SINGLE SOURCE OF TRUTH)
            flow_state.data["channel"] = StateManager.prepare_state_update(
                current_state={},
                channel_identifier=channel_id
            )["channel"]

            # Create flow with proper initialization
            flow = flow_class(
                id=flow_id,
                flow_type=flow_type,
                state=flow_state
            )

            # Initialize service BEFORE any step operations
            flow.credex_service = self.service.credex_service

            # Initialize steps after service is ready
            flow.initialize_steps()

            # Get flow state and update through state manager
            flow_data = flow.get_state().to_dict()
            self.service.user.state.update_state({
                "flow_data": flow_data
            })

            # Get initial message
            result = (flow.current_step.get_message(flow.data) if flow.current_step
                      else WhatsAppMessage.create_text(channel_id, "Flow not properly initialized"))

            audit.log_flow_event(
                "bot_service",
                "flow_start_success",
                None,
                {"flow_id": flow.id},
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
                channel_id,
                f"❌ Failed to start flow: {str(e)}"
            )

    def _get_pending_offers(self) -> Dict[str, Any]:
        """Get current account data with pending offers from state"""
        return self.service.user.state.state.get("current_account", {})
