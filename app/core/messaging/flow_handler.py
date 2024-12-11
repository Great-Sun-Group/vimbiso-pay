"""Handler for WhatsApp interaction flows"""
import logging
from typing import Any, Dict, Optional, Type, Union

from services.state.service import StateService, StateStage
from .flow import Flow, StepType
from .types import Message as WhatsAppMessage, MessageRecipient, TextContent
from .templates import ProgressiveInput

logger = logging.getLogger(__name__)


class FlowHandler:
    """Handles WhatsApp interaction flows with state management"""

    def __init__(self, state_service: StateService):
        self.state_service = state_service
        self._registered_flows: Dict[str, Type[Flow]] = {}
        self._service_injectors: Dict[str, callable] = {}

    def register_flow(self, flow_class: Type[Flow], service_injector: Optional[callable] = None) -> None:
        """Register a flow class and optional service injector"""
        # Register both by class name and flow ID for flexibility
        self._registered_flows[flow_class.__name__] = flow_class
        if hasattr(flow_class, 'FLOW_ID'):
            self._registered_flows[flow_class.FLOW_ID] = flow_class
            if service_injector:
                self._service_injectors[flow_class.FLOW_ID] = service_injector

    def get_flow(self, flow_id: str, state: Optional[Dict[str, Any]] = None) -> Optional[Flow]:
        """Get flow instance by ID and optionally restore its state"""
        flow_class = self._registered_flows.get(flow_id)
        if flow_class:
            flow = flow_class(flow_id, [])  # Steps defined in subclass
            # Inject services if injector exists
            if flow_id in self._service_injectors:
                self._service_injectors[flow_id](flow)
            # Restore state if provided
            if state:
                flow.state = state
                # Initialize from profile if available
                if isinstance(flow, Flow) and hasattr(flow, 'initialize_from_profile'):
                    profile_data = state.get('profile', {}).get('data', {})
                    if profile_data:
                        flow.initialize_from_profile(profile_data)
            return flow
        return None

    def handle_message(self, user_id: str, message: Dict[str, Any]) -> WhatsAppMessage:
        """Handle incoming message for active flow"""
        try:
            # Get current state
            state = self.state_service.get_state(user_id)
            logger.debug(f"Current state: {state}")

            # Get flow data from state
            flow_data = state.get("flow_data", {})
            flow_id = flow_data.get("id")

            if not flow_id:
                logger.warning(f"No active flow for user {user_id}")
                return self._format_error("No active flow", user_id)

            # Get flow instance using registered flow class and restore its state
            flow = self.get_flow(flow_id, flow_data.get("data", {}))
            if not flow:
                logger.error(f"Flow {flow_id} not registered")
                return self._format_error("Invalid flow", user_id)

            # Restore flow step
            flow.current_step_index = flow_data.get("current_step", 0)
            logger.debug(f"Flow state after restore: {flow.state}")

            # Get current step
            current_step = flow.current_step
            if not current_step:
                logger.error(f"No current step for flow {flow.id}")
                return self._format_error("Invalid flow state", user_id)

            # Process input based on step type
            logger.debug(f"Extracting input for step type {current_step.type}")
            logger.debug(f"Message content: {message}")
            input_value = self._extract_input(message, current_step.type)
            logger.debug(f"Extracted input value: '{input_value}'")

            # Handle button responses
            if current_step.type == StepType.BUTTON_SELECT and input_value == "cancel":
                # Clear flow data and return to menu
                state.pop("flow_data", None)
                self.state_service.update_state(
                    user_id=user_id,
                    new_state=state,
                    stage=StateStage.MENU.value,
                    update_from="flow_cancelled"
                )
                return self._format_message("Operation cancelled", user_id)

            # Validate input
            if not current_step.validate(input_value):
                return ProgressiveInput.create_validation_error(
                    "Invalid input",
                    user_id
                )

            # Transform input and update flow state
            transformed_input = current_step.transform_input(input_value)
            flow.update_state(current_step.id, transformed_input)
            logger.debug(f"Flow state after update: {flow.state}")

            # Get next step
            next_step = flow.next()
            if not next_step:
                # Flow complete - attempt to submit
                if hasattr(flow, 'complete_flow'):
                    success, message = flow.complete_flow()
                    if not success:
                        return self._format_error(message, user_id)

                # Update state with final flow state before clearing
                state["flow_data"]["data"] = flow.state
                self.state_service.update_state(
                    user_id=user_id,
                    new_state=state,
                    stage=StateStage.MENU.value,
                    update_from="flow_update"
                )

                # Return None to indicate flow completion to handler
                return None

            # Update state with new step
            state["flow_data"] = {
                "id": flow.id,
                "current_step": flow.current_step_index,
                "data": flow.state
            }

            # Preserve profile and account data in flow state
            if "profile" in state:
                state["flow_data"]["data"]["profile"] = state["profile"]
            if "current_account" in state:
                state["flow_data"]["data"]["current_account"] = state["current_account"]

            # Log state for debugging
            logger.debug(f"Updated flow state: {flow.state}")
            logger.debug(f"Updated state data: {state['flow_data']['data']}")

            self.state_service.update_state(
                user_id=user_id,
                new_state=state,
                stage=next_step.stage,
                update_from="flow_next",
                option=f"flow_{flow.id}"
            )

            # Return next step's message
            message = next_step.message
            if callable(message):
                message = message(flow.state)
            return message

        except Exception as e:
            logger.exception(f"Error handling flow message: {str(e)}")
            return self._format_error(str(e), user_id)

    def start_flow(self, flow_id: str, user_id: str) -> Union[Flow, WhatsAppMessage]:
        """Start a new flow for user"""
        try:
            # Get current state
            state = self.state_service.get_state(user_id)
            logger.debug(f"Starting flow with state: {state}")

            # Get flow instance
            flow = self.get_flow(flow_id)
            if not flow:
                logger.error(f"Flow {flow_id} not found")
                return self._format_error("Invalid flow", user_id)

            # Initialize flow state with user ID, profile, and account
            initial_state = {
                "phone": user_id,
                "profile": state.get("profile", {}),  # Include profile data
                "current_account": state.get("current_account")  # Include current account
            }
            flow.state = initial_state

            # Initialize from profile if available
            if isinstance(flow, Flow) and hasattr(flow, 'initialize_from_profile'):
                profile_data = state.get('profile', {}).get('data', {})
                if profile_data:
                    flow.initialize_from_profile(profile_data)

            # Update state with flow data
            state["flow_data"] = {
                "id": flow.id,
                "current_step": flow.current_step_index,
                "data": flow.state
            }

            # Log initial state for debugging
            logger.debug(f"Initial flow state: {flow.state}")
            logger.debug(f"Initial state data: {state['flow_data']['data']}")

            self.state_service.update_state(
                user_id=user_id,
                new_state=state,
                stage=flow.current_step.stage if flow.current_step else StateStage.INIT.value,
                update_from="flow_start",
                option=f"flow_{flow_id}"
            )

            # Return flow instance for further setup
            return flow

        except Exception as e:
            logger.exception(f"Error starting flow: {str(e)}")
            return self._format_error(str(e), user_id)

    def _extract_input(self, message: Dict[str, Any], step_type: StepType) -> Any:
        """Extract input value from message based on step type"""
        logger.debug(f"Extracting input for message: {message}")

        if step_type == StepType.TEXT_INPUT:
            # Extract from messages array if present
            messages = (
                message.get("entry", [{}])[0]
                .get("changes", [{}])[0]
                .get("value", {})
                .get("messages", [{}])
            )
            if messages:
                return messages[0].get("text", {}).get("body", "")
            # Fallback to direct text field
            return message.get("text", {}).get("body", "")

        elif step_type == StepType.LIST_SELECT:
            interactive = message.get("interactive", {})
            if interactive.get("type") == "list_reply":
                return interactive.get("list_reply", {}).get("id")

        elif step_type == StepType.BUTTON_SELECT:
            # Try interactive button reply first
            interactive = message.get("interactive", {})
            if interactive.get("type") == "button_reply":
                return interactive.get("button_reply", {}).get("id")

            # If not interactive, try text message
            messages = (
                message.get("entry", [{}])[0]
                .get("changes", [{}])[0]
                .get("value", {})
                .get("messages", [{}])
            )
            if messages and messages[0].get("type") == "text":
                text = messages[0].get("text", {}).get("body", "").lower()
                # Map text responses to button IDs
                if text == "confirm_registration":
                    return "confirm_registration"
                elif text == "edit_registration":
                    return "edit_registration"
                elif text == "confirm":
                    return "confirm"
                elif text == "cancel":
                    return "cancel"

        return None

    def _format_error(self, message: str, user_id: str) -> WhatsAppMessage:
        """Format error message"""
        return WhatsAppMessage(
            recipient=MessageRecipient(phone_number=user_id),
            content=TextContent(body=f"❌ Error: {message}")
        )

    def _format_message(self, message: str, user_id: str) -> WhatsAppMessage:
        """Format generic message"""
        return WhatsAppMessage(
            recipient=MessageRecipient(phone_number=user_id),
            content=TextContent(body=message)
        )
