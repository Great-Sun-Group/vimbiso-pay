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

    def _validate_profile_data(self, profile_data: Dict[str, Any]) -> bool:
        """Validate profile data structure"""
        try:
            if not isinstance(profile_data, dict):
                logger.error("Profile data is not a dictionary")
                return False

            # Handle both direct and nested data structures
            data = profile_data.get("data", profile_data)
            if not isinstance(data, dict):
                logger.error("Profile data['data'] is not a dictionary")
                return False

            # Ensure profile structure exists
            if "action" not in data:
                data["action"] = {}
            if not isinstance(data["action"], dict):
                data["action"] = {}
            if "details" not in data["action"]:
                data["action"]["details"] = {}
            if not isinstance(data["action"]["details"], dict):
                data["action"]["details"] = {}

            # Update profile_data with structured data
            if "data" not in profile_data:
                profile_data["data"] = data
            else:
                profile_data["data"] = data

            return True
        except Exception as e:
            logger.error(f"Profile validation error: {str(e)}")
            return False

    def _preserve_critical_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Preserve critical state data during cleanup"""
        preserved_state = {}
        critical_fields = [
            "profile",
            "current_account",
            "jwt_token",
            "authorizer_member_id",
            "issuer_member_id",
            "sender_account",
            "sender_account_id",
            "phone"
        ]
        for field in critical_fields:
            if field in state:
                preserved_state[field] = state[field]
        return preserved_state

    def get_flow(self, flow_id: str, state: Optional[Dict[str, Any]] = None) -> Optional[Flow]:
        """Get flow instance by ID and optionally restore its state"""
        try:
            flow_class = self._registered_flows.get(flow_id)
            if not flow_class:
                logger.error(f"Flow {flow_id} not registered")
                return None

            # Create flow instance
            flow = flow_class(flow_id, [])  # Steps defined in subclass

            # Inject services if injector exists
            if flow_id in self._service_injectors:
                try:
                    self._service_injectors[flow_id](flow)
                except Exception as e:
                    logger.error(f"Service injection failed for flow {flow_id}: {str(e)}")
                    return None

            # Restore and validate state if provided
            if state:
                try:
                    # Validate profile data first
                    profile_data = state.get('profile', {})
                    if profile_data and not self._validate_profile_data(profile_data):
                        logger.error("Invalid profile data structure")
                        return None

                    flow.state = state
                    if not flow.validate_state():
                        if not flow.recover_state():
                            logger.error(f"Flow state validation failed for {flow_id}")
                            return None
                except Exception as e:
                    logger.error(f"Flow state restoration failed for {flow_id}: {str(e)}")
                    return None

                # Initialize from profile if available
                if isinstance(flow, Flow) and hasattr(flow, 'initialize_from_profile'):
                    profile_data = state.get('profile', {}).get('data', {})
                    if profile_data:
                        try:
                            flow.initialize_from_profile(profile_data)
                        except Exception as e:
                            logger.error(f"Profile initialization failed: {str(e)}")
                            return None

            return flow

        except Exception as e:
            logger.error(f"Error getting flow {flow_id}: {str(e)}")
            return None

    def _cleanup_flow_state(self, user_id: str, state: Dict[str, Any], update_from: str = "flow_cleanup") -> None:
        """Clean up flow state data while preserving critical data"""
        try:
            # Preserve critical state data
            preserved_state = self._preserve_critical_state(state)

            # Remove flow data
            if "flow_data" in preserved_state:
                del preserved_state["flow_data"]

            # Update state with preserved data
            self.state_service.update_state(
                user_id=user_id,
                new_state=preserved_state,
                stage=StateStage.MENU.value,
                update_from=update_from
            )
            logger.debug(f"Flow state cleaned up from {update_from}")
            logger.debug(f"Preserved state: {preserved_state}")
        except Exception as e:
            logger.error(f"Flow cleanup failed: {str(e)}")
            # Attempt emergency cleanup while preserving critical data
            try:
                preserved_state = self._preserve_critical_state(state)
                self.state_service.reset_state(user_id)
                if preserved_state:
                    self.state_service.update_state(
                        user_id=user_id,
                        new_state=preserved_state,
                        stage=StateStage.MENU.value,
                        update_from="emergency_cleanup"
                    )
            except Exception:
                pass

    def handle_message(self, user_id: str, message: Dict[str, Any]) -> WhatsAppMessage:
        """Handle incoming message for active flow"""
        try:
            # Get current state
            state = self.state_service.get_state(user_id)
            logger.debug(f"Current state: {state}")

            # Validate state structure
            if not isinstance(state, dict):
                logger.error("Invalid state type")
                return self._format_error("Invalid state", user_id)

            # Get flow data from state
            flow_data = state.get("flow_data", {})
            flow_id = flow_data.get("id")

            if not flow_id:
                logger.warning(f"No active flow for user {user_id}")
                return self._format_error("No active flow", user_id)

            # Get flow instance using registered flow class and restore its state
            flow = self.get_flow(flow_id, flow_data.get("data", {}))
            if not flow:
                logger.error(f"Flow {flow_id} not registered or state invalid")
                self._cleanup_flow_state(user_id, state, "flow_invalid")
                return self._format_error("Invalid flow", user_id)

            # Restore flow step
            flow.current_step_index = flow_data.get("current_step", 0)
            logger.debug(f"Flow state after restore: {flow.state}")

            # Validate flow state
            if not flow.validate_state():
                if not flow.recover_state():
                    logger.error(f"Flow state validation failed for {flow_id}")
                    self._cleanup_flow_state(user_id, state, "flow_corrupted")
                    return self._format_error("Flow state corrupted", user_id)

            # Get current step
            current_step = flow.current_step
            if not current_step:
                logger.error(f"No current step for flow {flow.id}")
                self._cleanup_flow_state(user_id, state, "step_invalid")
                return self._format_error("Invalid flow state", user_id)

            # Process input based on step type
            logger.debug(f"Extracting input for step type {current_step.type}")
            logger.debug(f"Message content: {message}")
            input_value = self._extract_input(message, current_step.type)
            logger.debug(f"Extracted input value: '{input_value}'")

            # Handle button responses
            if current_step.type == StepType.BUTTON_SELECT and input_value == "cancel":
                # Clear flow data and return to menu
                self._cleanup_flow_state(user_id, state, "flow_cancelled")
                return self._format_message("Operation cancelled", user_id)

            # Validate input
            if not current_step.validate(input_value):
                return ProgressiveInput.create_validation_error(
                    "Invalid input",
                    user_id
                )

            try:
                # Transform input and update flow state
                transformed_input = current_step.transform_input(input_value)
                flow.update_state(current_step.id, transformed_input)
                logger.debug(f"Flow state after update: {flow.state}")
            except Exception as e:
                logger.error(f"Input processing failed: {str(e)}")
                return self._format_error("Failed to process input", user_id)

            # Get next step
            next_step = flow.next()
            if not next_step:
                # Flow complete - attempt to submit
                if hasattr(flow, 'complete_flow'):
                    try:
                        success, message = flow.complete_flow()
                        if not success:
                            self._cleanup_flow_state(user_id, state, "flow_completion_failed")
                            return self._format_error(message, user_id)
                    except Exception as e:
                        logger.error(f"Flow completion failed: {str(e)}")
                        self._cleanup_flow_state(user_id, state, "flow_completion_error")
                        return self._format_error("Flow completion failed", user_id)

                # Update state with final flow state before clearing
                state["flow_data"]["data"] = flow.state
                self.state_service.update_state(
                    user_id=user_id,
                    new_state=state,
                    stage=StateStage.MENU.value,
                    update_from="flow_complete"
                )

                # Return None to indicate flow completion to handler
                return None

            # Update state with new step
            state["flow_data"] = {
                "id": flow.id,
                "current_step": flow.current_step_index,
                "data": flow.state
            }

            # Preserve critical data in flow state
            preserved_data = self._preserve_critical_state(state)
            state["flow_data"]["data"].update(preserved_data)

            # Log state for debugging
            logger.debug(f"Updated flow state: {flow.state}")
            logger.debug(f"Updated state data: {state['flow_data']['data']}")

            try:
                self.state_service.update_state(
                    user_id=user_id,
                    new_state=state,
                    stage=next_step.stage,
                    update_from="flow_next",
                    option=f"flow_{flow.id}"
                )
            except Exception as e:
                logger.error(f"State update failed: {str(e)}")
                return self._format_error("Failed to update state", user_id)

            # Return next step's message
            message = next_step.message
            if callable(message):
                try:
                    message = message(flow.state)
                except Exception as e:
                    logger.error(f"Message generation failed: {str(e)}")
                    return self._format_error("Failed to generate message", user_id)
            return message

        except Exception as e:
            logger.exception(f"Error handling flow message: {str(e)}")
            # Attempt to cleanup on error while preserving critical data
            try:
                self._cleanup_flow_state(user_id, state, "flow_error")
            except Exception:
                pass
            return self._format_error(str(e), user_id)

    def start_flow(self, flow_id: str, user_id: str) -> Union[Flow, WhatsAppMessage]:
        """Start a new flow for user"""
        try:
            # Get current state
            state = self.state_service.get_state(user_id)
            logger.debug(f"Starting flow with state: {state}")

            # Validate state structure
            if not isinstance(state, dict):
                logger.error("Invalid state type")
                return self._format_error("Invalid state", user_id)

            # Get flow instance
            flow = self.get_flow(flow_id)
            if not flow:
                logger.error(f"Flow {flow_id} not found")
                return self._format_error("Invalid flow", user_id)

            # Initialize flow state with critical data
            initial_state = self._preserve_critical_state(state)
            initial_state["phone"] = user_id

            # Validate and structure profile data if present
            profile_data = state.get("profile", {})
            if profile_data:
                if not self._validate_profile_data(profile_data):
                    logger.error("Invalid profile data structure")
                    return self._format_error("Invalid profile data", user_id)
                initial_state["profile"] = profile_data

            try:
                flow.state = initial_state
            except Exception as e:
                logger.error(f"Flow state initialization failed: {str(e)}")
                return self._format_error("Failed to initialize flow", user_id)

            # Initialize from profile if available
            if isinstance(flow, Flow) and hasattr(flow, 'initialize_from_profile'):
                profile_data = state.get('profile', {}).get('data', {})
                if profile_data:
                    try:
                        flow.initialize_from_profile(profile_data)
                    except Exception as e:
                        logger.error(f"Profile initialization failed: {str(e)}")
                        return self._format_error("Failed to initialize profile", user_id)

            # Validate initial state
            if not flow.validate_state():
                logger.error(f"Initial flow state validation failed for {flow_id}")
                return self._format_error("Invalid flow state", user_id)

            # Update state with flow data
            state["flow_data"] = {
                "id": flow.id,
                "current_step": flow.current_step_index,
                "data": flow.state
            }

            # Log initial state for debugging
            logger.debug(f"Initial flow state: {flow.state}")
            logger.debug(f"Initial state data: {state['flow_data']['data']}")

            try:
                self.state_service.update_state(
                    user_id=user_id,
                    new_state=state,
                    stage=flow.current_step.stage if flow.current_step else StateStage.INIT.value,
                    update_from="flow_start",
                    option=f"flow_{flow_id}"
                )
            except Exception as e:
                logger.error(f"State update failed: {str(e)}")
                return self._format_error("Failed to start flow", user_id)

            # Return flow instance for further setup
            return flow

        except Exception as e:
            logger.exception(f"Error starting flow: {str(e)}")
            return self._format_error(str(e), user_id)

    def _extract_input(self, message: Dict[str, Any], step_type: StepType) -> Any:
        """Extract input value from message based on step type"""
        logger.debug(f"Extracting input for message: {message}")

        try:
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

        except Exception as e:
            logger.error(f"Input extraction failed: {str(e)}")
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
