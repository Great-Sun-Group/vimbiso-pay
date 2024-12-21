"""Flow processing and continuation logic"""
import logging
from typing import Any, Dict, Type

from core.messaging.flow import Flow
from core.utils.flow_audit import FlowAuditLogger
from ..credex import CredexFlow
from ..member import RegistrationFlow, UpgradeFlow, DashboardFlow
from ...types import WhatsAppMessage

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
        if "member_registration" in flow_id:
            return RegistrationFlow
        elif "member_upgrade" in flow_id:
            return UpgradeFlow
        elif "offer_" in flow_id:
            return CredexFlow
        elif "accept_" in flow_id:
            return CredexFlow
        elif "decline_" in flow_id:
            return CredexFlow
        elif "cancel_" in flow_id:
            return CredexFlow
        return CredexFlow

    def initialize_flow(
        self,
        flow_class: Type[Flow],
        flow_type: str,
        flow_data: Dict,
        kwargs: Dict
    ) -> Flow:
        """Initialize flow with state"""
        initial_state = {
            "id": flow_data["id"],
            "step": flow_data["step"],
            "data": flow_data["data"]
        }

        if flow_class in {RegistrationFlow, UpgradeFlow}:
            flow = flow_class(**kwargs)
        else:
            # Initialize flow with state
            flow_kwargs = kwargs.copy()
            if flow_class == CredexFlow:
                flow_kwargs['flow_type'] = flow_type
            flow = flow_class(
                state=initial_state,
                **flow_kwargs
            )

        flow.credex_service = self.service.credex_service
        flow.current_index = flow_data["step"]
        return flow

    def process_flow(self, flow_data: Dict) -> WhatsAppMessage:
        """Process flow continuation"""
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
            result = flow.process_input(input_value)

            # Handle invalid input
            if result == "Invalid input":
                audit.log_flow_event(
                    "bot_service",
                    "invalid_input",
                    flow.current_step.id if flow.current_step else None,
                    {"input": self.service.body},
                    "failure"
                )

                error = self.state_handler.handle_invalid_input_state(
                    flow, flow_type, kwargs
                )
                if error:
                    return error

                return self.input_handler.handle_invalid_input(
                    flow.current_step.id if flow.current_step else None
                )

            # Handle flow completion
            if not result:
                return self.service.auth_handler.handle_action_menu()

            # Handle confirmation step
            if flow.current_step and flow.current_step.id == "confirm":
                return self._handle_confirmation_step(flow, flow_id)

            # Handle step completion
            if flow.current_index >= len(flow.steps):
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
            logger.error(f"Flow error: {str(e)}")
            audit.log_flow_event(
                "bot_service",
                "flow_error",
                None,
                {"error": str(e)},
                "failure"
            )
            return self.state_handler.handle_error_state(str(e))

    def _handle_confirmation_step(self, flow: Flow, flow_id: str) -> WhatsAppMessage:
        """Handle confirmation step processing"""
        audit.log_flow_event(
            "bot_service",
            "flow_complete",
            None,
            flow.data,
            "success"
        )

        if any(t in flow_id for t in ["offer_", "accept_", "decline_", "cancel_"]):
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

        # Update dashboard if needed
        api_response = result.get("response", {})
        if api_response:
            flow.credex_service._update_dashboard(api_response)

        # Handle completion state
        error = self.state_handler.handle_flow_completion()
        if error:
            return error

        # Show success message
        dashboard = DashboardFlow(
            success_message=result.get("message")
        )
        dashboard.credex_service = self.service.credex_service
        dashboard.data = {"mobile_number": self.service.user.mobile_number}
        return dashboard.complete()
