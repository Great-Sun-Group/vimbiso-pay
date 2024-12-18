"""WhatsApp message handling implementation"""
import logging
import re
from typing import Dict, Any

from .base_handler import BaseActionHandler
from .types import BotServiceInterface, WhatsAppMessage
from .auth_handlers import AuthActionHandler
from .handlers.credex import CredexFlow
from .handlers.member.flows import MemberFlow
from .handlers.member.dashboard import DashboardFlow

logger = logging.getLogger(__name__)


class CredexBotService(BotServiceInterface, BaseActionHandler):
    """Simplified WhatsApp bot service"""

    def __init__(self, payload: Dict[str, Any], user: Any):
        BotServiceInterface.__init__(self, payload=payload, user=user)
        BaseActionHandler.__init__(self, self)
        # Get or create the underlying CredEx service
        self.credex_service = user.state.get_or_create_credex_service()
        # Set parent service reference for dashboard updates
        self.credex_service._parent_service = self
        self.auth_handler = AuthActionHandler(self)
        self.response = self._process_message()

    def _get_action(self) -> str:
        """Extract action from message"""
        # Check for direct message action
        if isinstance(self.message, dict):
            action = self.message.get("message")
            if action:
                logger.info(f"Found direct action: {action}")
                return action

        # Check list reply for cancel actions
        if self.message_type == "interactive":
            interactive = self.message.get("interactive", {})
            list_reply = interactive.get("list_reply", {})
            if list_reply:
                action = list_reply.get("id")
                logger.info(f"Found list action: {action}")
                return action

        # Check text message
        if self.message_type == "text":
            action = self.body.strip().lower()
            logger.info(f"Found text action: {action}")
            return action

        logger.info("No action found")
        return ""

    def _start_flow(self, flow_type: str, flow_class, **kwargs) -> WhatsAppMessage:
        """Start a new flow"""
        try:
            logger.info(f"Starting flow: {flow_type}")
            flow = flow_class(flow_type=flow_type, **kwargs)
            # Pass the cached CredEx service to the flow
            flow.credex_service = self.credex_service

            # Initialize flow data
            profile = self.user.state.state.get("profile", {})
            current_account = self.user.state.state.get("current_account", {})

            # Get member_id from profile.action.details.memberID
            member_id = (
                profile.get("action", {})
                .get("details", {})
                .get("memberID")
            )

            # Get account_id from current_account.data.accountID
            account_id = (
                current_account.get("data", {})
                .get("accountID")
            )

            logger.info(f"Initializing flow with member_id: {member_id}, account_id: {account_id}")

            if not member_id or not account_id:
                logger.error(f"Missing required IDs - member_id: {member_id}, account_id: {account_id}")
                return self.get_response_template("Account not properly initialized")

            # Initialize base flow data
            flow.data = {
                "phone": self.user.mobile_number,
                "member_id": member_id,
                "account_id": account_id,
                "mobile_number": self.user.mobile_number
            }

            # For cancel_credex flow, add pending offers to flow data
            if flow_type == "cancel_credex":
                logger.info("Adding pending offers to cancel_credex flow")
                # Get current account's pending outgoing offers
                pending_out = (
                    current_account.get("data", {})
                    .get("pendingOutData", {})
                    .get("data", [])
                )

                logger.info(f"Found {len(pending_out)} pending offers")

                # Format pending offers for display
                pending_offers = []
                for offer in pending_out:
                    amount = offer.get("formattedInitialAmount", "0")
                    if amount.startswith("-"):  # Remove negative sign
                        amount = amount[1:]
                    pending_offers.append({
                        "id": offer.get("credexID"),
                        "amount": amount,
                        "to": offer.get("counterpartyAccountName")
                    })

                # Add pending offers to flow data
                flow.data["pending_offers"] = pending_offers

                # Check for direct cancel command
                if self.message_type == "text":
                    cancel_match = re.match(r'cancel_([0-9a-f-]+)', self.body.strip().lower())
                    if cancel_match:
                        credex_id = cancel_match.group(1)
                        logger.info(f"Found direct cancel command for credex ID: {credex_id}")
                        # Verify the credex ID exists in pending offers
                        if any(offer["id"] == credex_id for offer in pending_offers):
                            # Find the matching offer
                            selected_offer = next(
                                offer for offer in pending_offers
                                if offer["id"] == credex_id
                            )
                            # Set up flow data for confirmation
                            flow.data.update({
                                "credex_id": credex_id,
                                "selection": f"cancel_{credex_id}",
                                "amount": selected_offer["amount"],
                                "counterparty": selected_offer["to"]
                            })
                            # Skip to confirmation step
                            flow.current_index = 1
                            result = flow.current_step.get_message(flow.data)
                            # Ensure result is properly formatted as WhatsApp message
                            if isinstance(result, str):
                                return self.get_response_template(result)
                            return result

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

            # If result is already a WhatsApp message, return it directly
            if isinstance(result, dict) and result.get("messaging_product") == "whatsapp":
                return result

            # Otherwise wrap it in a template
            return self.get_response_template(result)

        except Exception as e:
            logger.error(f"Error starting flow: {str(e)}")
            return self._format_error_response(f"Failed to start flow: {str(e)}")

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

            # Process input based on message type
            if self.message_type == "interactive":
                # For interactive messages, pass exact WhatsApp format
                interactive = self.message.get("interactive", {})
                logger.debug(f"Processing interactive message: {interactive}")

                # Check for button reply
                if interactive.get("type") == "button_reply":
                    button_reply = interactive.get("button_reply", {})
                    logger.debug(f"Found button reply: {button_reply}")
                    result = flow.process_input({
                        "type": "interactive",
                        "interactive": {
                            "type": "button_reply",
                            "button_reply": button_reply
                        }
                    })
                # Check for list reply
                elif interactive.get("type") == "list_reply":
                    list_reply = interactive.get("list_reply", {})
                    logger.debug(f"Found list reply: {list_reply}")
                    result = flow.process_input({
                        "type": "interactive",
                        "interactive": {
                            "type": "list_reply",
                            "list_reply": list_reply
                        }
                    })
                else:
                    logger.warning(f"Unknown interactive type: {interactive.get('type')}")
                    result = "Invalid input"
            else:
                # For text messages, pass the body
                logger.debug("Processing text message")
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

                # For any credex flow completion, show updated dashboard with success message
                if "credex_" in flow_id:
                    # Get appropriate success message based on flow type
                    success_messages = {
                        "offer": "Credex successfully offered",
                        "accept": "Credex successfully accepted",
                        "decline": "Credex successfully declined",
                        "cancel_credex": "Credex successfully cancelled"
                    }
                    success_message = success_messages.get(flow_type, "Operation successful")

                    # Initialize dashboard flow with success message
                    dashboard_flow = DashboardFlow(success_message=success_message)
                    dashboard_flow.credex_service = self.credex_service
                    dashboard_flow.data = {
                        "mobile_number": self.user.mobile_number
                    }
                    # Return dashboard view
                    return dashboard_flow.complete()

                # If result is already a WhatsApp message, return it directly
                if isinstance(result, dict) and result.get("messaging_product") == "whatsapp":
                    return result

                # Otherwise wrap it in a template
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

            # If result is already a WhatsApp message, return it directly
            if isinstance(result, dict) and result.get("messaging_product") == "whatsapp":
                return result

            # Otherwise wrap it in a template
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

            # Get action
            action = self._get_action()
            logger.info(f"Processing action: {action}")

            # Handle menu actions first
            if action == "offer_credex":
                return self._start_flow("offer", CredexFlow)
            elif action == "accept_credex":
                return self._start_flow("accept", CredexFlow)
            elif action == "decline_credex":
                return self._start_flow("decline", CredexFlow)
            elif action == "cancel_credex" or (
                self.message_type == "text" and
                re.match(r'cancel_[0-9a-f-]+', self.body.strip().lower())
            ):
                logger.info("Starting cancel_credex flow")
                return self._start_flow("cancel_credex", CredexFlow)
            elif action == "view_transactions":
                return self._start_flow("transactions", MemberFlow)
            elif action == "start_registration":
                return self._start_flow("registration", MemberFlow)
            elif action == "upgrade_tier":
                return self._start_flow("upgrade", MemberFlow)

            # Then check for active flow
            state = self.user.state.state
            flow_data = state.get("flow_data", {})
            if flow_data:
                logger.info("Continuing existing flow")
                return self._continue_flow(flow_data)

            # Default to menu for unknown actions
            if action:
                return self.auth_handler.handle_action_menu()

            # Default to menu
            return self.auth_handler.handle_action_menu()

        except Exception as e:
            logger.error(f"Message processing error: {str(e)}")
            return self._format_error_response(str(e))

    def handle(self) -> WhatsAppMessage:
        """Return processed response"""
        return self.response
