"""Handler for WhatsApp interaction flows"""
import logging
from typing import Any, Dict, Optional, Type

from services.state.service import StateService, StateStage
from .flow import Flow, StepType
from .types import Message as WhatsAppMessage
from .templates import ProgressiveInput

logger = logging.getLogger(__name__)


class FlowHandler:
    """Handles WhatsApp interaction flows with state management"""

    def __init__(self, state_service: StateService):
        self.state_service = state_service
        self._registered_flows: Dict[str, Type[Flow]] = {}

    def register_flow(self, flow_class: Type[Flow]) -> None:
        """Register a flow class"""
        self._registered_flows[flow_class.__name__] = flow_class

    def get_flow(self, flow_id: str) -> Optional[Flow]:
        """Get flow instance by ID"""
        flow_class = self._registered_flows.get(flow_id)
        if flow_class:
            return flow_class(flow_id, [])  # Steps defined in subclass
        return None

    def handle_message(self, user_id: str, message: Dict[str, Any]) -> WhatsAppMessage:
        """Handle incoming message for active flow"""
        try:
            # Get current state
            state = self.state_service.get_state(user_id)

            # Check if there's an active flow
            flow = Flow.from_state_data(state)
            if not flow:
                logger.warning(f"No active flow for user {user_id}")
                return self._format_error("No active flow")

            # Get current step
            current_step = flow.current_step
            if not current_step:
                logger.error(f"No current step for flow {flow.id}")
                return self._format_error("Invalid flow state")

            # Process input based on step type
            input_value = self._extract_input(message, current_step.type)

            # Validate input
            if not current_step.validate(input_value):
                return ProgressiveInput.create_validation_error(
                    "Invalid input"
                )

            # Transform input if needed
            transformed_input = current_step.transform_input(input_value)

            # Update flow state with input
            flow.state[current_step.id] = transformed_input

            # Get next step
            next_step = flow.next()
            if not next_step:
                # Flow complete - clear flow data
                state.pop("flow_data", None)
                self.state_service.update_state(
                    user_id=user_id,
                    new_state=state,
                    stage=StateStage.MENU.value,
                    update_from="flow_complete"
                )
                return self._format_completion(flow)

            # Update state with new step
            state.update(flow.to_state_data())
            self.state_service.update_state(
                user_id=user_id,
                new_state=state,
                stage=next_step.stage,
                update_from="flow_next",
                option=f"flow_{flow.id}"
            )

            # Return next step's message
            return next_step.message

        except Exception as e:
            logger.exception(f"Error handling flow message: {str(e)}")
            return self._format_error(str(e))

    def start_flow(self, flow_id: str, user_id: str) -> WhatsAppMessage:
        """Start a new flow for user"""
        try:
            # Get flow instance
            flow = self.get_flow(flow_id)
            if not flow:
                logger.error(f"Flow {flow_id} not found")
                return self._format_error("Invalid flow")

            # Get current state
            state = self.state_service.get_state(user_id)

            # Update state with flow data
            state.update(flow.to_state_data())
            self.state_service.update_state(
                user_id=user_id,
                new_state=state,
                stage=flow.current_step.stage if flow.current_step else StateStage.INIT.value,
                update_from="flow_start",
                option=f"flow_{flow_id}"
            )

            # Return first step's message
            return flow.current_step.message if flow.current_step else self._format_error("No steps defined")

        except Exception as e:
            logger.exception(f"Error starting flow: {str(e)}")
            return self._format_error(str(e))

    def _extract_input(self, message: Dict[str, Any], step_type: StepType) -> Any:
        """Extract input value from message based on step type"""
        if step_type == StepType.TEXT_INPUT:
            return message.get("text", {}).get("body", "")

        elif step_type == StepType.LIST_SELECT:
            interactive = message.get("interactive", {})
            if interactive.get("type") == "list_reply":
                return interactive.get("list_reply", {}).get("id")

        elif step_type == StepType.BUTTON_SELECT:
            interactive = message.get("interactive", {})
            if interactive.get("type") == "button_reply":
                return interactive.get("button_reply", {}).get("id")

        return None

    def _format_error(self, message: str) -> WhatsAppMessage:
        """Format error message"""
        return WhatsAppMessage(
            content={
                "type": "text",
                "text": {
                    "body": f"❌ Error: {message}"
                }
            }
        )

    def _format_completion(self, flow: Flow) -> WhatsAppMessage:
        """Format flow completion message"""
        return WhatsAppMessage(
            content={
                "type": "text",
                "text": {
                    "body": "✅ Flow completed successfully"
                }
            }
        )
