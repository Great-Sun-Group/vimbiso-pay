"""WhatsApp message handling implementation"""
import logging
import re
from typing import Dict, Any, Optional, Tuple, Type

from core.messaging.flow import Flow
from .base_handler import BaseActionHandler
from .types import BotServiceInterface, WhatsAppMessage
from .auth_handlers import AuthActionHandler
from .handlers.credex import CredexFlow
from .handlers.member.flows import MemberFlow
from .handlers.member.dashboard import DashboardFlow


logger = logging.getLogger(__name__)


class CredexBotService(BotServiceInterface, BaseActionHandler):
    """WhatsApp bot service implementation"""

    FLOW_TYPES = {
        "offer_credex": ("offer", CredexFlow),
        "accept_credex": ("accept", CredexFlow),
        "decline_credex": ("decline", CredexFlow),
        "cancel_credex": ("cancel_credex", CredexFlow),
        "view_transactions": ("transactions", MemberFlow),
        "start_registration": ("registration", MemberFlow),
        "upgrade_tier": ("upgrade", MemberFlow)
    }

    GREETING_KEYWORDS = {"hi", "hello", "hey", "start"}

    def __init__(self, payload: Dict[str, Any], user: Any):
        """Initialize bot service"""
        BotServiceInterface.__init__(self, payload=payload, user=user)
        BaseActionHandler.__init__(self, self)
        self.credex_service = user.state.get_or_create_credex_service()
        self.credex_service._parent_service = self
        self.auth_handler = AuthActionHandler(self)
        self.response = self._process_message()

    def _get_action(self) -> str:
        """Extract action from message"""
        # Direct message action
        if isinstance(self.message, dict) and "message" in self.message:
            return self.message["message"]

        # Interactive list reply
        if self.message_type == "interactive":
            interactive = self.message.get("interactive", {})
            if list_reply := interactive.get("list_reply", {}):
                return list_reply.get("id", "")

        # Text message
        if self.message_type == "text":
            return self.body.strip().lower()

        return ""

    def _get_flow_info(self, action: str) -> Optional[Tuple[str, Type[Flow], Dict[str, Any]]]:
        """Get flow type, class and kwargs for action"""
        # Check predefined flows
        if action in self.FLOW_TYPES:
            flow_type, flow_class = self.FLOW_TYPES[action]
            return flow_type, flow_class, {}

        # Check direct cancel command
        if self.message_type == "text":
            if match := re.match(r'cancel_([0-9a-f-]+)', action):
                return "cancel_credex", CredexFlow, {"credex_id": match.group(1)}

        return None

    def _start_flow(self, flow_type: str, flow_class: Type[Flow], **kwargs) -> WhatsAppMessage:
        """Start a new flow"""
        try:
            flow = flow_class(flow_type=flow_type, **kwargs)
            flow.credex_service = self.credex_service

            # Initialize flow data
            profile = self.user.state.state.get("profile", {})
            current_account = self.user.state.state.get("current_account", {})

            member_id = (
                profile.get("action", {})
                .get("details", {})
                .get("memberID")
            )
            account_id = (
                current_account.get("data", {})
                .get("accountID")
            )

            if not member_id or not account_id:
                return self.get_response_template("Account not properly initialized")

            # Set base flow data
            flow.data = {
                "phone": self.user.mobile_number,
                "member_id": member_id,
                "account_id": account_id,
                "mobile_number": self.user.mobile_number
            }

            # Add pending offers for cancel flow
            if flow_type == "cancel_credex":
                pending_out = (
                    current_account.get("data", {})
                    .get("pendingOutData", {})
                    .get("data", [])
                )

                pending_offers = [{
                    "id": offer.get("credexID"),
                    "amount": offer.get("formattedInitialAmount", "0").lstrip("-"),
                    "to": offer.get("counterpartyAccountName")
                } for offer in pending_out]

                flow.data["pending_offers"] = pending_offers

                # Handle direct cancel command
                if credex_id := kwargs.get("credex_id"):
                    if selected_offer := next(
                        (o for o in pending_offers if o["id"] == credex_id),
                        None
                    ):
                        flow.data.update({
                            "credex_id": credex_id,
                            "selection": f"cancel_{credex_id}",
                            "amount": selected_offer["amount"],
                            "counterparty": selected_offer["to"]
                        })
                        flow.current_index = 1
                        return flow.current_step.get_message(flow.data)

            # Get initial message
            result = flow.current_step.get_message(flow.data)

            # Save flow state
            self.user.state.update_state({
                "flow_data": {
                    **flow.get_state(),
                    "flow_type": flow_type,
                    "kwargs": kwargs
                }
            }, "flow_start")

            return (
                result if isinstance(result, dict) and
                result.get("messaging_product") == "whatsapp"
                else self.get_response_template(result)
            )

        except Exception as e:
            logger.error(f"Flow start error: {str(e)}")
            return self._format_error_response(f"Failed to start flow: {str(e)}")

    def _continue_flow(self, flow_data: Dict[str, Any]) -> WhatsAppMessage:
        """Continue an existing flow"""
        try:
            flow_type = flow_data.get("flow_type")
            kwargs = flow_data.get("kwargs", {})
            if not flow_type:
                raise ValueError("Missing flow type")

            # Initialize correct flow
            flow_id = flow_data.get("id", "")
            flow_class = CredexFlow if "credex_" in flow_id else MemberFlow
            flow = flow_class(flow_type=flow_type, **kwargs)
            flow.credex_service = self.credex_service
            flow.set_state({
                "id": flow_data["id"],
                "step": flow_data["step"],
                "data": flow_data["data"]
            })

            # Process input
            result = None
            if self.message_type == "interactive":
                interactive = self.message.get("interactive", {})
                if interactive.get("type") == "button_reply":
                    result = flow.process_input({
                        "type": "interactive",
                        "interactive": {
                            "type": "button_reply",
                            "button_reply": interactive.get("button_reply", {})
                        }
                    })
                elif interactive.get("type") == "list_reply":
                    result = flow.process_input({
                        "type": "interactive",
                        "interactive": {
                            "type": "list_reply",
                            "list_reply": interactive.get("list_reply", {})
                        }
                    })
            else:
                result = flow.process_input(self.body)

            # Handle invalid input
            if result == "Invalid input":
                if flow.current_step and flow.current_step.id == "amount":
                    result = (
                        "Invalid amount format. Examples:\n"
                        "100     (USD)\n"
                        "USD 100\n"
                        "ZWG 100\n"
                        "XAU 1"
                    )
                return self.get_response_template(result)

            # Handle flow completion
            if not result or flow.current_index >= len(flow.steps):
                self.user.state.update_state({"flow_data": None}, "flow_complete")

                if not result:
                    return self.auth_handler.handle_action_menu()

                if "credex_" in flow_id:
                    success_messages = {
                        "offer": "Credex successfully offered",
                        "accept": "Credex successfully accepted",
                        "decline": "Credex successfully declined",
                        "cancel_credex": "Credex successfully cancelled"
                    }
                    dashboard = DashboardFlow(
                        success_message=success_messages.get(flow_type)
                    )
                    dashboard.credex_service = self.credex_service
                    dashboard.data = {"mobile_number": self.user.mobile_number}
                    return dashboard.complete()

                return (
                    result if isinstance(result, dict) and
                    result.get("messaging_product") == "whatsapp"
                    else self.get_response_template(result)
                )

            # Update flow state
            self.user.state.update_state({
                "flow_data": {
                    **flow.get_state(),
                    "flow_type": flow_type,
                    "kwargs": kwargs
                }
            }, "flow_continue")

            return (
                result if isinstance(result, dict) and
                result.get("messaging_product") == "whatsapp"
                else self.get_response_template(result)
            )

        except Exception as e:
            logger.error(f"Flow error: {str(e)}")
            self.user.state.update_state({"flow_data": None}, "flow_error")
            return self._format_error_response(str(e))

    def _process_message(self) -> WhatsAppMessage:
        """Process incoming message"""
        try:
            # Handle greeting
            if (self.message_type == "text" and
                    self.body.lower() in self.GREETING_KEYWORDS):
                return self.auth_handler.handle_action_menu(login=True)

            # Get action
            action = self._get_action()
            logger.info(f"Processing action: {action}")

            # Check for active flow
            flow_data = self.user.state.state.get("flow_data")
            if flow_data:
                return self._continue_flow(flow_data)

            # Start new flow if action matches
            if flow_info := self._get_flow_info(action):
                flow_type, flow_class, kwargs = flow_info
                return self._start_flow(flow_type, flow_class, **kwargs)

            # Default to menu
            return self.auth_handler.handle_action_menu()

        except Exception as e:
            logger.error(f"Message processing error: {str(e)}")
            return self._format_error_response(str(e))

    def handle(self) -> WhatsAppMessage:
        """Return processed response"""
        return self.response
