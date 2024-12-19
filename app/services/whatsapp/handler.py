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
    BUTTON_ACTIONS = {"confirm_action"}

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
        # For all message types, use the parsed body
        return self.body.strip().lower()

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

    def _get_member_info(self) -> Tuple[Optional[str], Optional[str]]:
        """Extract member and account IDs from state"""
        try:
            state = self.user.state.state or {}

            # Get IDs directly from state root where auth_handlers.py stores them
            member_id = state.get("member_id")
            account_id = state.get("account_id")

            # Log the values for debugging
            logger.debug(f"Retrieved member_id: {member_id}, account_id: {account_id} from state")

            return member_id, account_id

        except Exception as e:
            logger.error(f"Error extracting member info: {str(e)}")
            return None, None

    def _start_flow(self, flow_type: str, flow_class: Type[Flow], **kwargs) -> WhatsAppMessage:
        """Start a new flow"""
        try:
            flow = flow_class(flow_type=flow_type, **kwargs)
            flow.credex_service = self.credex_service

            # Get member and account IDs
            member_id, account_id = self._get_member_info()
            if not member_id or not account_id:
                logger.error(f"Missing required IDs - member_id: {member_id}, account_id: {account_id}")
                return self.get_response_template(
                    "Account not properly initialized. Please try sending 'hi' to restart."
                )

            # Set base flow data
            flow.data = {
                "phone": self.user.mobile_number,
                "member_id": member_id,
                "account_id": account_id,
                "mobile_number": self.user.mobile_number
            }

            # Add pending offers for cancel flow
            if flow_type == "cancel_credex":
                current_account = self.user.state.state.get("current_account", {})
                pending_out = (
                    current_account.get("data", {})
                    .get("pendingOutData", {})
                    .get("data", [])
                )

                pending_offers = [{
                    "id": offer.get("credexID"),
                    "amount": offer.get("formattedInitialAmount", "0").lstrip("-"),
                    "to": offer.get("counterpartyAccountName")
                } for offer in pending_out if all(
                    offer.get(k) for k in ["credexID", "formattedInitialAmount", "counterpartyAccountName"]
                )]

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

            # Save flow state while preserving critical fields
            current_state = self.user.state.state or {}
            self.user.state.update_state({
                "flow_data": {
                    **flow.get_state(),
                    "flow_type": flow_type,
                    "kwargs": kwargs
                },
                "profile": current_state.get("profile", {}),
                "current_account": current_state.get("current_account"),
                "jwt_token": current_state.get("jwt_token"),
                "member_id": current_state.get("member_id"),  # Preserve member_id
                "account_id": current_state.get("account_id")  # Preserve account_id
            }, "flow_start")

            return (
                result if isinstance(result, dict) and
                result.get("messaging_product") == "whatsapp"
                else self.get_response_template(result)
            )

        except Exception as e:
            logger.error(f"Flow start error: {str(e)}")
            return self._format_error_response(f"Failed to start flow: {str(e)}")

    def _format_button_response(self, action: str) -> Dict[str, Any]:
        """Format text message as button response"""
        return {
            "type": "interactive",
            "interactive": {
                "type": "button_reply",
                "button_reply": {
                    "id": action
                }
            }
        }

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
                # Pass full message structure for validation
                result = flow.process_input({
                    "type": "interactive",
                    "interactive": {
                        "type": "button_reply",
                        "button_reply": {"id": self.body}
                    } if "button_reply" in self.message.get("interactive", {}) else {
                        "type": "list_reply",
                        "list_reply": {"id": self.body}
                    }
                })
            else:
                # Check if text message is a button action
                if self.body.strip().lower() in self.BUTTON_ACTIONS:
                    result = flow.process_input(self._format_button_response(self.body))
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
                # Preserve critical fields when clearing flow data
                current_state = self.user.state.state or {}
                self.user.state.update_state({
                    "flow_data": None,
                    "profile": current_state.get("profile", {}),
                    "current_account": current_state.get("current_account"),
                    "jwt_token": current_state.get("jwt_token"),
                    "member_id": current_state.get("member_id"),  # Preserve member_id
                    "account_id": current_state.get("account_id")  # Preserve account_id
                }, "flow_complete")

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

            # Update flow state while preserving critical fields
            current_state = self.user.state.state or {}
            self.user.state.update_state({
                "flow_data": {
                    **flow.get_state(),
                    "flow_type": flow_type,
                    "kwargs": kwargs
                },
                "profile": current_state.get("profile", {}),
                "current_account": current_state.get("current_account"),
                "jwt_token": current_state.get("jwt_token"),
                "member_id": current_state.get("member_id"),  # Preserve member_id
                "account_id": current_state.get("account_id")  # Preserve account_id
            }, "flow_continue")

            return (
                result if isinstance(result, dict) and
                result.get("messaging_product") == "whatsapp"
                else self.get_response_template(result)
            )

        except Exception as e:
            logger.error(f"Flow error: {str(e)}")
            # Preserve critical fields when clearing flow data on error
            current_state = self.user.state.state or {}
            self.user.state.update_state({
                "flow_data": None,
                "profile": current_state.get("profile", {}),
                "current_account": current_state.get("current_account"),
                "jwt_token": current_state.get("jwt_token"),
                "member_id": current_state.get("member_id"),  # Preserve member_id
                "account_id": current_state.get("account_id")  # Preserve account_id
            }, "flow_error")
            return self._format_error_response(str(e))

    def _process_message(self) -> WhatsAppMessage:
        """Process incoming message"""
        try:
            # Handle greeting first
            if (self.message_type == "text" and
                    self.body.lower() in self.GREETING_KEYWORDS):
                # Clear any existing flow data
                if self.user.state.state:
                    current_state = self.user.state.state
                    self.user.state.update_state({
                        "flow_data": None,
                        "profile": current_state.get("profile", {}),
                        "current_account": current_state.get("current_account"),
                        "jwt_token": current_state.get("jwt_token"),
                        "authenticated": current_state.get("authenticated", False),
                        "member_id": current_state.get("member_id"),  # Preserve member_id
                        "account_id": current_state.get("account_id")  # Preserve account_id
                    }, "clear_flow_greeting")
                return self.auth_handler.handle_action_menu(login=True)

            # Check for active flow
            flow_data = self.user.state.state.get("flow_data") if self.user.state.state else None
            if flow_data:
                return self._continue_flow(flow_data)

            # Get action
            action = self._get_action()
            logger.info(f"Processing action: {action}")

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
