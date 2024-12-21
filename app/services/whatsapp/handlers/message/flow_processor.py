"""Flow processing and continuation logic"""
import logging
from typing import Any, Dict, Type

from core.messaging.flow import Flow
from core.utils.flow_audit import FlowAuditLogger

from ...types import WhatsAppMessage
from ..credex.flows import (AcceptFlow, CancelFlow, CredexFlow, DeclineFlow,
                            OfferFlow)
from ..member import DashboardFlow, RegistrationFlow, UpgradeFlow

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
        """Initialize flow with state"""
        # Get member ID from data
        member_id = flow_data.get("data", {}).get("member_id")
        if not member_id:
            raise ValueError("Missing member ID in flow data")

        # Prepare complete state including flow data
        state = {
            "id": f"{flow_type}_{member_id}",  # Construct proper flow ID
            "step": flow_data["step"],
            "data": flow_data["data"],
            "flow_data": {
                "flow_type": flow_type,
                **flow_data
            }
        }

        # Initialize flow with state and kwargs
        flow = flow_class(state=state, **kwargs)

        # Set service for Credex flows
        if isinstance(flow, CredexFlow):
            flow.credex_service = self.service.credex_service

        return flow

    def process_flow(self, flow_data: Dict) -> WhatsAppMessage:
        """Process flow continuation"""
        # Initialize variables outside try block
        flow = None
        flow_type = None
        flow_id = None
        input_value = None

        try:
            # Get flow info
            flow_type = flow_data.get("flow_type")
            kwargs = flow_data.get("kwargs", {})
            if not flow_type:
                raise ValueError("Missing flow type")

            # Initialize flow
            flow_id = flow_data.get("id", "")
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
                return self.service.auth_handler.handle_action_menu()

            # Handle flow completion
            if flow.current_index >= len(flow.steps):
                # Only complete the flow if we've processed the confirmation
                if flow.current_step and flow.current_step.id == "confirm":
                    return self._handle_confirmation_step(flow, flow_id)

                error = self.state_handler.handle_flow_completion()
                if error:
                    return error
                return self.service.auth_handler.handle_action_menu()

            # Continue flow
            error = self.state_handler.handle_flow_continuation(
                flow, flow_type, kwargs
            )
            if error:
                return error

            return result

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

            return self.state_handler.handle_error_state(
                str(e) or "Flow processing failed - check logs for details"
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

        return flow.complete()

    def _complete_credex_flow(self, flow: Flow) -> WhatsAppMessage:
        """Complete credex flow and handle result"""
        result = flow.complete()

        if not isinstance(result, dict):
            return WhatsAppMessage.create_text(
                self.service.user.mobile_number,
                "Operation failed: Invalid response format"
            )

        if not result.get("success", False):
            return WhatsAppMessage.create_text(
                self.service.user.mobile_number,
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
        dashboard.data = {
            "mobile_number": self.service.user.mobile_number,
            "success_message": success_message  # Also store in data for state preservation
        }
        return dashboard.complete()
