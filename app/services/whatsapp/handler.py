"""WhatsApp message handling implementation"""
import logging
from typing import Dict, Any, Optional, Type, Tuple

from core.messaging.flow import Flow
from core.transactions import create_transaction_service
from services.state.manager import StateManager
from services.state.data import StateData
from .base_handler import BaseActionHandler
from .types import BotServiceInterface, WhatsAppMessage
from .handlers.credex.offer_flow import CredexOfferFlow
from .auth_handlers import AuthActionHandler

logger = logging.getLogger(__name__)


class MessageHandler:
    """Simple WhatsApp message processing"""

    def __init__(self, state_manager: StateManager):
        self.state = state_manager
        self.flows: Dict[str, Type[Flow]] = {}
        self._register_default_flows()

    def _register_default_flows(self) -> None:
        """Register default flows"""
        self.register_flow("credex_offer", CredexOfferFlow)

    def register_flow(self, flow_id: str, flow_class: Type[Flow]) -> None:
        """Register a flow class"""
        self.flows[flow_id] = flow_class

    def _extract_input(self, message: Dict[str, Any]) -> Any:
        """Extract input value from message"""
        # Handle interactive messages
        if "interactive" in message:
            interactive = message["interactive"]
            if interactive.get("type") == "button_reply":
                return interactive.get("button_reply", {}).get("id")
            if interactive.get("type") == "list_reply":
                return interactive.get("list_reply", {}).get("id")

        # Handle text messages
        if "text" in message:
            return message.get("text", {}).get("body")

        return None

    def _get_flow(self, state: Dict[str, Any]) -> Optional[Flow]:
        """Get flow from state"""
        flow_data = state.get("flow_data", {})
        if not flow_data:
            return None

        flow_id = flow_data.get("id")
        if not flow_id or flow_id not in self.flows:
            return None

        # Create and restore flow
        flow = self.flows[flow_id](flow_id, [])
        flow.set_state(flow_data)
        return flow

    def handle(self, user_id: str, message: Dict[str, Any]) -> Optional[str]:
        """Handle incoming message"""
        try:
            # Get state and input
            state = self.state.get(user_id)
            input_data = self._extract_input(message)
            if input_data is None:
                return "Invalid message"

            # Get flow
            flow = self._get_flow(state)
            if not flow:
                return "No active flow"

            # Process input
            result = flow.process_input(input_data)

            # Update state
            new_state = StateData.merge(state, {
                "flow_data": flow.get_state()
            })
            self.state.set(user_id, new_state)

            return result

        except Exception as e:
            logger.error(f"Message handling error: {str(e)}")
            return f"Error: {str(e)}"

    def start_flow(self, user_id: str, flow_id: str, initial_data: Dict[str, Any] = None) -> Optional[str]:
        """Start a new flow"""
        try:
            # Validate flow
            if flow_id not in self.flows:
                return f"Unknown flow: {flow_id}"

            # Create flow
            flow = self.flows[flow_id](flow_id, [])
            if initial_data:
                flow.data.update(initial_data)

            # Get initial message
            if not flow.current_step:
                return "Flow has no steps"
            message = flow.current_step.get_message(flow.data)

            # Update state
            state = self.state.get(user_id)
            new_state = StateData.merge(state, {
                "flow_data": flow.get_state()
            })
            self.state.set(user_id, new_state)

            return message

        except Exception as e:
            logger.error(f"Flow start error: {str(e)}")
            return f"Error: {str(e)}"


class CredexBotService(BotServiceInterface, BaseActionHandler):
    """Bridge between webhook and new message handling"""

    def __init__(self, payload: Dict[str, Any], user: Any):
        super().__init__(user)  # Initialize BaseActionHandler
        self.payload = payload
        self.user = user
        self.service = self  # Required for BaseActionHandler
        self.state = user.state  # Required for BotServiceInterface
        self.credex_service = None  # Will be set by service layer
        self.transaction_service = None
        self.auth_handler = AuthActionHandler(self)
        self.response = self._process_message()

    def _validate_and_get_profile(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Validate and get profile data"""
        current_state = self.user.state.__dict__
        if not current_state.get("jwt_token"):
            raise ValueError("Authentication required")

        profile = current_state.get("profile", {})
        if not profile or not isinstance(profile, dict):
            raise ValueError("Invalid profile data")

        return current_state, profile

    def _is_greeting(self, message: Dict[str, Any]) -> bool:
        """Check if message is a greeting"""
        if message.get("type") == "text":
            text = message.get("text", {}).get("body", "").lower()
            return text in {"hi", "hello", "hey", "start"}
        return False

    def _process_message(self) -> WhatsAppMessage:
        """Process message using new handler"""
        try:
            # Extract message from payload
            messages = self.payload.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {}).get("messages", [])
            if not messages:
                return self._format_error_response("No message found")

            message = messages[0]

            # Handle greeting with auth flow
            if self._is_greeting(message):
                return self.auth_handler.handle_action_menu(login=True)

            # Initialize services if needed
            if not self.transaction_service and self.credex_service:
                self.transaction_service = create_transaction_service(
                    api_client=self.credex_service
                )

            # Get profile data
            try:
                current_state, profile = self._validate_and_get_profile()
            except ValueError:
                # Handle auth error with menu
                return self.auth_handler.handle_action_menu(login=True)

            # Use new handler
            handler = MessageHandler(StateManager(self.user.state_redis))

            # Extract action from message
            action = None
            if message.get("type") == "interactive":
                interactive = message["interactive"]
                if interactive.get("type") == "button_reply":
                    action = interactive["button_reply"].get("id")
                elif interactive.get("type") == "list_reply":
                    action = interactive["list_reply"].get("id")

            # Handle specific actions
            if action == "offer_credex":
                return self.get_response_template(
                    handler.start_flow(
                        self.user.mobile_number,
                        "credex_offer",
                        {"profile": profile}
                    )
                )

            # Process normal message
            result = handler.handle(self.user.mobile_number, message)

            # Format response using base handler
            return self.get_response_template(result or "No response")

        except Exception as e:
            logger.error(f"Message processing error: {str(e)}")
            return self._format_error_response(str(e))
