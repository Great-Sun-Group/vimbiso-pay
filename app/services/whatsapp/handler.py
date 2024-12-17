"""WhatsApp message handling implementation"""
import logging
from typing import Dict, Any

from .base_handler import BaseActionHandler
from .types import BotServiceInterface, WhatsAppMessage
from .auth_handlers import AuthActionHandler
from .handlers.credex import CredexFlow
from .handlers.member import MemberFlow

logger = logging.getLogger(__name__)


class CredexBotService(BotServiceInterface, BaseActionHandler):
    """Simplified WhatsApp bot service"""

    def __init__(self, payload: Dict[str, Any], user: Any):
        BotServiceInterface.__init__(self, payload=payload, user=user)
        BaseActionHandler.__init__(self, self)
        # Get or create the underlying CredEx service
        self.credex_service = user.state.get_or_create_credex_service()
        self.auth_handler = AuthActionHandler(self)
        self.response = self._process_message()

    def _get_action(self) -> str:
        """Extract action from message"""
        if self.message_type == "interactive":
            return (
                self.message.get("interactive", {})
                .get("button_reply", {})
                .get("id") or
                self.message.get("interactive", {})
                .get("list_reply", {})
                .get("id")
            )
        elif self.message_type == "text":
            return self.body.strip().lower()
        return ""

    def _start_flow(self, flow_type: str, flow_class, **kwargs) -> WhatsAppMessage:
        """Start a new flow"""
        flow = flow_class(flow_type=flow_type, **kwargs)
        # Pass the cached CredEx service to the flow
        flow.credex_service = self.credex_service

        # Initialize flow data
        profile = self.user.state.state.get("profile", {})
        current_account = self.user.state.state.get("current_account", {})
        member_id = profile.get("data", {}).get("action", {}).get("details", {}).get("memberID")
        account_id = current_account.get("data", {}).get("accountID")

        if not member_id or not account_id:
            return self.get_response_template("Account not properly initialized")

        flow.data = {
            "phone": self.user.mobile_number,
            "member_id": member_id,
            "account_id": account_id
        }

        # Get initial message
        result = flow.current_step.get_message(flow.data)

        # Save flow state
        flow_state = flow.get_state()  # Get base state (id, step, data)
        self.user.state.update_state({
            "flow_data": {
                **flow_state,  # Flow's internal state
                "flow_type": flow_type,  # Flow type for recreation
                "kwargs": kwargs  # Flow kwargs for recreation
            }
        }, "flow_start")

        return self.get_response_template(result)

    def _continue_flow(self, flow_data: Dict[str, Any]) -> WhatsAppMessage:
        """Continue an existing flow"""
        try:
            # Get flow type and kwargs from state
            flow_type = flow_data.get("flow_type")
            kwargs = flow_data.get("kwargs", {})
            if not flow_type:
                raise ValueError("Missing flow type")

            # Initialize correct flow type
            flow_id = flow_data.get("id", "")
            if "credex_" in flow_id:
                flow = CredexFlow(flow_type=flow_type, **kwargs)
            elif "member_" in flow_id:
                flow = MemberFlow(flow_type=flow_type, **kwargs)
            else:
                raise ValueError("Invalid flow ID")

            # Initialize flow with its expected state structure
            flow.credex_service = self.credex_service  # Pass the cached CredEx service
            flow_state = {
                "id": flow_data["id"],
                "step": flow_data["step"],
                "data": flow_data["data"]
            }
            flow.set_state(flow_state)

            # Process input
            result = flow.process_input(self.body)
            if result == "Invalid input":
                # Show more helpful error for amount validation
                if flow.current_step and flow.current_step.id == "amount":
                    result = (
                        "Invalid amount format. Examples:\n"
                        "100     (USD)\n"
                        "USD 100\n"
                        "ZWG 100\n"
                        "XAU 1"
                    )
                return self.get_response_template(result)
            elif not result:
                # Flow complete with no message
                self.user.state.update_state({
                    "flow_data": None
                }, "flow_complete")
                return self.auth_handler.handle_action_menu()
            elif flow.current_index >= len(flow.steps):
                # Flow complete with success message
                self.user.state.update_state({
                    "flow_data": None
                }, "flow_complete")
                # Return success message - dashboard data already updated by flow
                return self.get_response_template(result)

            # Update flow state
            flow_state = flow.get_state()  # Get updated state
            self.user.state.update_state({
                "flow_data": {
                    **flow_state,  # Flow's internal state
                    "flow_type": flow_type,  # Preserve flow type
                    "kwargs": kwargs  # Preserve flow kwargs
                }
            }, "flow_continue")

            return self.get_response_template(result)

        except Exception as e:
            logger.error(f"Flow error: {str(e)}")
            # Clear flow state on error
            self.user.state.update_state({
                "flow_data": None
            }, "flow_error")
            return self._format_error_response(str(e))

    def _process_message(self) -> WhatsAppMessage:
        """Process incoming message"""
        try:
            # Handle greeting
            if self.message_type == "text" and self.body.lower() in {"hi", "hello", "hey", "start"}:
                return self.auth_handler.handle_action_menu(login=True)

            # Get current flow from user's state
            state = self.user.state.state
            flow_data = state.get("flow_data", {})

            # Handle active flow
            if flow_data:
                return self._continue_flow(flow_data)

            # Handle menu actions
            action = self._get_action()

            # Start flows
            if action == "offer_credex":
                return self._start_flow("offer", CredexFlow)
            elif action == "start_registration":
                return self._start_flow("registration", MemberFlow)
            elif action == "upgrade_tier":
                return self._start_flow("upgrade", MemberFlow)
            elif action:
                return self.auth_handler.handle_action_menu()

            # Default to menu
            return self.auth_handler.handle_action_menu()

        except Exception as e:
            logger.error(f"Message processing error: {str(e)}")
            return self._format_error_response(str(e))

    def handle(self) -> WhatsAppMessage:
        """Return processed response"""
        return self.response
