"""Progressive flow mixin for credex handlers"""
import logging
from typing import Any, Dict, Tuple

from core.messaging.flow_handler import FlowHandler
from .offer_flow_v2 import CredexOfferFlow
from .action_flows import AcceptCredexFlow, DeclineCredexFlow, CancelCredexFlow
from ...types import WhatsAppMessage
from ...base_handler import BaseActionHandler

logger = logging.getLogger(__name__)


class ProgressiveFlowMixin(BaseActionHandler):
    """Mixin for handling progressive flows"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.flow_handler = FlowHandler(self.service.state)
        self._register_flows()

    def _register_flows(self):
        """Register all flows with service injector"""
        flows = [
            CredexOfferFlow,
            AcceptCredexFlow,
            DeclineCredexFlow,
            CancelCredexFlow
        ]
        for flow_class in flows:
            self.flow_handler.register_flow(
                flow_class,
                service_injector=self._inject_flow_services
            )
        logger.debug("Progressive flows registered with service injector")

    def _inject_flow_services(self, flow: Any) -> None:
        """Inject required services into flow"""
        flow.transaction_service = self.transaction_service
        flow.credex_service = self.service.credex_service
        flow.state_service = self.service.state
        logger.debug(f"Services injected into flow: {type(flow).__name__}")

    def _extract_member_id(self, profile_data: Dict[str, Any]) -> str:
        """Extract member ID from profile data"""
        try:
            # Try to get from action details first
            data = profile_data.get("data", profile_data)
            action = data.get("action", {})
            if action:
                # Try details.memberID
                member_id = action.get("details", {}).get("memberID")
                if member_id:
                    return member_id
                # Try action.actor as fallback
                return action.get("actor")

            # Try dashboard path as fallback
            dashboard = data.get("dashboard", {})
            if dashboard:
                # Look in accounts for owned account
                accounts = dashboard.get("accounts", [])
                for account in accounts:
                    if account.get("success") and account.get("data", {}).get("isOwnedAccount"):
                        auth_for = account.get("data", {}).get("authFor", [])
                        if auth_for:
                            return auth_for[0].get("memberID")

                # Try direct memberID as final fallback
                if dashboard.get("memberID"):
                    return dashboard["memberID"]

            return None
        except Exception as e:
            logger.error(f"Error extracting member ID: {str(e)}")
            return None

    def _extract_sender_account_info(self, profile_data: Dict[str, Any], selected_profile: Dict[str, Any]) -> Tuple[str, str]:
        """Extract sender account info from profile data"""
        try:
            if selected_profile and isinstance(selected_profile, dict):
                account_data = selected_profile.get("data", {})
                if account_data.get("isOwnedAccount"):
                    return account_data.get("accountID"), account_data.get("accountName", "Your Account")

            # Handle both direct and nested data structures
            data = profile_data.get("data", profile_data)
            dashboard = data.get("dashboard", {})
            accounts = dashboard.get("accounts", [])
            for account in accounts:
                if (account.get("success") and
                        account["data"].get("accountHandle") == self.service.user.mobile_number):
                    account_data = account["data"]
                    return account_data.get("accountID"), account_data.get("accountName", "Your Account")

            # If no account found but have dashboard memberID, use that
            if dashboard.get("memberID"):
                return dashboard["memberID"], "Your Account"

            return None, "Your Account"
        except Exception as e:
            logger.error(f"Error extracting sender account info: {str(e)}")
            return None, "Your Account"

    def _initialize_flow_state(
            self, current_state: Dict[str, Any], member_id: str,
            sender_account_id: str, sender_account_name: str) -> Dict[str, Any]:
        """Initialize flow state with required fields"""
        flow_state = {
            "id": "credex_offer",
            "current_step": 0,
            "data": {
                "profile": current_state.get("profile", {}),
                "current_account": current_state.get("current_account"),
                "authorizer_member_id": member_id,
                "issuer_member_id": member_id,
                "sender_account": sender_account_name,
                "sender_account_id": sender_account_id,
                "phone": self.service.user.mobile_number
            }
        }

        # Preserve JWT token
        if self.service.credex_service and self.service.credex_service.jwt_token:
            flow_state["data"]["jwt_token"] = self.service.credex_service.jwt_token

        return flow_state

    def _handle_progressive_flow(
        self,
        current_state: Dict[str, Any],
        selected_profile: Dict[str, Any]
    ) -> Tuple[bool, WhatsAppMessage]:
        """Handle progressive flow"""
        try:
            # Validate current state
            if not isinstance(current_state, dict):
                raise ValueError("Invalid current state type")

            # Log message details for debugging
            logger.debug(f"Message type: {self.service.message_type}")
            logger.debug(f"Message: {self.service.message}")
            logger.debug(f"Current state: {current_state}")

            # Check if this is a menu selection or text command
            interactive = self.service.message.get("interactive", {})
            button_reply = interactive.get("button_reply", {})
            list_reply = interactive.get("list_reply", {})

            is_menu_selection = (
                self.service.message_type == "interactive" and
                (
                    (button_reply and button_reply.get("id") == "handle_action_offer_credex") or
                    (list_reply and list_reply.get("id") == "handle_action_offer_credex")
                )
            )

            is_text_command = (
                self.service.message_type == "text" and
                isinstance(self.service.body, str) and
                self.service.body == "handle_action_offer_credex"
            )

            # Handle menu selection or text command
            if is_menu_selection or is_text_command:
                logger.debug("Starting new credex offer flow")

                # Extract required data from profile
                member_id = self._extract_member_id(current_state.get("profile", {}))
                if not member_id:
                    logger.error("Could not find member ID in profile data")
                    return True, self.get_response_template("Please start over by sending 'hi' to refresh your session.")

                sender_account_id, sender_account_name = self._extract_sender_account_info(
                    current_state.get("profile", {}), selected_profile
                )
                if not sender_account_id:
                    logger.error("Could not find sender account info")
                    return True, self.get_response_template("Please start over by sending 'hi' to refresh your session.")

                # Initialize flow state
                flow_state = self._initialize_flow_state(
                    current_state, member_id, sender_account_id, sender_account_name
                )
                current_state["flow_data"] = flow_state

                # Start flow
                result = self.flow_handler.start_flow(
                    "credex_offer",
                    self.service.user.mobile_number
                )

                if isinstance(result, CredexOfferFlow):
                    result.initialize_from_profile(current_state.get("profile", {}).get("data", {}))
                    result.state.update(flow_state["data"])
                    message = result.current_step.message
                    if callable(message):
                        message = message(result.state)
                    return True, WhatsAppMessage.from_core_message(message)
                return True, WhatsAppMessage.from_core_message(result)

            # Check if there's an active flow
            if "flow_data" in current_state:
                logger.debug("Found active flow, handling message")

                # Handle message
                message = self.flow_handler.handle_message(
                    self.service.user.mobile_number,
                    self.service.message
                )

                if message is None:
                    # Flow completed successfully
                    logger.debug("Flow completed successfully")
                    # Return to menu with success message
                    menu_message = self.service.action_handler.auth_handler.handle_action_menu(
                        message="✅ Credex offer created successfully!\n\n",
                        login=False  # Don't need API call since we have fresh data
                    )
                    return True, WhatsAppMessage.from_core_message(menu_message)
                return True, WhatsAppMessage.from_core_message(message)

            # Now check for numeric input without active flow
            if (self.service.message_type == "text" and
                isinstance(self.service.body, str) and
                    self.service.body.replace(".", "").isdigit()):
                logger.debug("Received numeric input without active flow")
                return True, WhatsAppMessage.from_core_message({
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": self.service.user.mobile_number,
                    "type": "text",
                    "text": {
                        "body": "❌ Please start from the menu by selecting 'Offer Secured Credex' first."
                    }
                })

            # Return error for any other input without active flow
            logger.debug("Received input without active flow")
            return True, WhatsAppMessage.from_core_message({
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self.service.user.mobile_number,
                "type": "text",
                "text": {
                    "body": "❌ Please start over by sending 'hi' to refresh your session."
                }
            })

        except Exception as e:
            logger.exception(f"Error handling progressive flow: {str(e)}")
            error_message = self._format_error_response(str(e))
            return True, WhatsAppMessage.from_core_message(error_message)
