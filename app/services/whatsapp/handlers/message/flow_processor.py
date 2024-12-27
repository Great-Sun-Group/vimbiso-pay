"""Flow processing and continuation logic"""
import logging
from typing import Any, Dict, Type

# Core imports
from core.messaging.flow import Flow
from core.utils.flow_audit import FlowAuditLogger

# Local imports
from ...types import WhatsAppMessage
from ...state_manager import StateManager
from ..credex.flows.action import AcceptFlow, CancelFlow, DeclineFlow
from ..credex.flows.base import CredexFlow
from ..credex.flows.offer import OfferFlow
from ..member.dashboard import DashboardFlow
from ..member.registration import RegistrationFlow
from ..member.upgrade import UpgradeFlow

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class FlowProcessor:
    """Handles flow processing and continuation"""

    def __init__(self, service: Any, input_handler: Any, state_handler: Any):
        self.service = service
        self.input_handler = input_handler
        self.state_handler = state_handler

    def determine_flow_class(self, flow_id: str) -> Type[Flow]:
        """Determine flow class based on flow ID"""
        if flow_id.startswith("member_registration"):
            return RegistrationFlow
        elif flow_id.startswith("member_upgrade"):
            return UpgradeFlow
        elif flow_id.startswith("offer_"):
            return OfferFlow
        elif flow_id.startswith("accept_"):
            return AcceptFlow
        elif flow_id.startswith("decline_"):
            return DeclineFlow
        elif flow_id.startswith("cancel_"):
            return CancelFlow
        # Log warning for unknown flow type
        logger.warning(f"Unknown flow type for ID: {flow_id}, using base CredexFlow")
        return CredexFlow

    def initialize_flow(
        self,
        flow_class: Type[Flow],
        flow_type: str,
        flow_data: Dict,
        kwargs: Dict
    ) -> Flow:
        """Initialize flow with proper state management

        Args:
            flow_class: The class of the flow to create
            flow_type: The type of flow to initialize
            flow_data: Existing flow data if any
            kwargs: Additional keyword arguments

        Returns:
            Flow: Initialized flow instance

        Note:
            Uses simple state structure with member_id and channel info at top level
        """
        try:
            # Get member ID from top level state - SINGLE SOURCE OF TRUTH
            state_data = self.service.user.state.state
            member_id = StateManager.get_member_id(state_data)
            if not member_id:
                raise ValueError("Missing member ID in state")

            # Create flow ID
            flow_id = f"{flow_type}_{member_id}"

            # Log flow initialization
            logger.debug(f"Initializing flow {flow_type}:")
            logger.debug(f"- Flow ID: {flow_id}")
            logger.debug(f"- Member ID: {member_id}")
            logger.debug(f"- Flow data keys: {list(flow_data.keys())}")

            # Simple flow data - no nesting madness
            flow_data = {
                "step": 0,
                "flow_type": flow_type
            }

            # Update state with simple flow data
            self.service.user.state.update_state({
                "flow_data": flow_data
            })

            # Create flow with proper initialization
            flow = flow_class(
                id=flow_id,
                flow_type=flow_type
            )

            # Set service for Credex flows and initialize steps
            if isinstance(flow, CredexFlow):
                flow.credex_service = self.service.credex_service
                flow.initialize_steps()

            return flow

        except Exception as e:
            logger.error(f"Flow initialization error: {str(e)}")
            audit.log_flow_event(
                "bot_service",
                "flow_init_error",
                None,
                {"error": str(e)},
                "failure"
            )
            raise

    def process_flow(self, flow_data: Dict) -> WhatsAppMessage:
        """Process flow continuation"""
        # Initialize variables outside try block
        flow = None
        flow_type = None
        flow_id = None
        input_value = None

        try:
            # Get flow info and validate structure
            if not isinstance(flow_data, dict):
                logger.error("Flow data must be a dictionary")
                return WhatsAppMessage.create_text(
                    self.service.user.channel_identifier,
                    "❌ Error: Invalid flow data"
                )

            # Get flow type from flow_data
            flow_type = flow_data.get("flow_type")
            if not flow_type:
                logger.error("Missing flow type in flow_data")
                return WhatsAppMessage.create_text(
                    self.service.user.channel_identifier,
                    "❌ Error: Missing flow type in flow data"
                )

            kwargs = flow_data.get("kwargs", {})

            # Log flow data for debugging
            logger.debug("Processing flow data:")
            logger.debug(f"- Flow type: {flow_type}")
            logger.debug(f"- Flow data structure: {flow_data.keys()}")

            # Initialize flow
            flow_id = f"{flow_type}_{self.service.user.state.state.get('member_id')}"
            flow_class = self.determine_flow_class(flow_id)
            flow = self.initialize_flow(flow_class, flow_type, flow_data, kwargs)

            # Process input
            input_value = self.input_handler.extract_input_value()

            # High-level flow info at INFO level
            logger.info(f"Processing {flow_type} flow step {flow.current_step.id if flow.current_step else 'None'}")

            # Detailed state at DEBUG level
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("=== Flow Processing Details ===")
                logger.debug(f"Input: {input_value}")
                logger.debug(f"Flow ID: {flow.id}")
                logger.debug(f"Initial state: {flow.get_state()}")

            # Process input through flow
            result = flow.process_input(input_value)

            # If result is a WhatsAppMessage, it's a direct response (error/validation)
            if isinstance(result, WhatsAppMessage):
                return result

            # If no result, flow is complete
            if not result:
                return WhatsAppMessage.from_core_message(self.service.auth_handler.handle_action_menu())

            # Handle flow completion
            if flow.current_index >= len(flow.steps):
                # Only complete the flow if we've processed the confirmation
                if flow.current_step and flow.current_step.id == "confirm":
                    return WhatsAppMessage.from_core_message(self._handle_confirmation_step(flow, flow_id))

                error = self.state_handler.handle_flow_completion()
                if error:
                    return error
                return WhatsAppMessage.from_core_message(self.service.auth_handler.handle_action_menu())

            # Continue flow
            error = self.state_handler.handle_flow_continuation(
                flow, flow_type, kwargs
            )
            if error:
                return error

            return WhatsAppMessage.from_core_message(result)

        except Exception as e:
            # Only log detailed context if we have an empty error
            error_msg = str(e)
            error_context = {
                "error_type": type(e).__name__,
                "flow_type": flow_type,
                "flow_id": flow_id,
                "step": flow.current_step.id if flow and flow.current_step else None,
                "input": input_value,
                "state": flow.get_state() if flow else None
            }

            if not error_msg:
                logger.error(
                    "Flow processing failed with empty error message",
                    extra=error_context,
                    exc_info=True
                )
            else:
                logger.error(f"Flow error: {error_msg}", extra=error_context)

            # Log flow event with safe access to flow properties
            step_id = flow.current_step.id if flow and flow.current_step else None
            audit.log_flow_event(
                "bot_service",
                "flow_error",
                step_id,
                {"error": error_msg or "Empty error - check logs for context"},
                "failure"
            )

            return WhatsAppMessage.from_core_message(
                self.state_handler.handle_error_state(
                    str(e) or "Flow processing failed - check logs for details"
                )
            )

    def _handle_confirmation_step(self, flow: Flow, flow_id: str) -> WhatsAppMessage:
        """Handle confirmation step processing"""
        audit.log_flow_event(
            "bot_service",
            "flow_complete",
            None,
            flow.data,
            "success"
        )

        if any(flow_id.startswith(t) for t in ["offer_", "accept_", "decline_", "cancel_"]):
            return self._complete_credex_flow(flow)

        return WhatsAppMessage.from_core_message(flow.complete())

    def _complete_credex_flow(self, flow: Flow) -> WhatsAppMessage:
        """Complete credex flow and handle result"""
        result = flow.complete()

        if not isinstance(result, dict):
            return WhatsAppMessage.create_text(
                self.service.user.channel_identifier,
                "Operation failed: Invalid response format"
            )

        if not result.get("success", False):
            return WhatsAppMessage.create_text(
                self.service.user.channel_identifier,
                result.get("message", "Operation failed")
            )

        # Get success message and API response
        success_message = result.get("message")
        api_response = result.get("response", {})

        # Update dashboard with API response
        if api_response:
            # Add success message to API response action
            if "data" in api_response and "action" in api_response["data"]:
                api_response["data"]["action"]["message"] = success_message

            # Update dashboard state
            flow.credex_service._update_dashboard(api_response)

        # Handle completion state
        error = self.state_handler.handle_flow_completion()
        if error:
            return error

        # Show dashboard with success message
        dashboard = DashboardFlow(
            flow_type="view",
            success_message=success_message
        )
        dashboard.credex_service = self.service.credex_service

        # Get member ID from top level state - SINGLE SOURCE OF TRUTH
        state_data = self.service.user.state.state
        member_id = StateManager.get_member_id(state_data)
        if not member_id:
            raise ValueError("Missing member ID")

        # Create simple dashboard flow data
        flow_data = {
            "step": 0,
            "flow_type": "view"
        }

        # Update state with simple flow data
        self.service.user.state.update_state({
            "flow_data": flow_data
        })

        # Initialize dashboard with proper initialization
        dashboard = DashboardFlow(
            id=f"dashboard_view_{member_id}",
            flow_type="view"
        )
        dashboard.credex_service = self.service.credex_service

        return WhatsAppMessage.from_core_message(dashboard.complete())
