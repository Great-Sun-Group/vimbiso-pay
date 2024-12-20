"""WhatsApp message handling implementation"""
import logging
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
        # Handle interactive messages
        if self.message_type == "interactive":
            interactive = self.message.get("interactive", {})
            if interactive.get("type") == "list_reply":
                return interactive.get("list_reply", {}).get("id", "").lower()
            elif interactive.get("type") == "button_reply":
                return interactive.get("button_reply", {}).get("id", "").lower()

        # For text messages
        return self.body.strip().lower()

    def _get_flow_info(self, action: str) -> Optional[Tuple[str, Type[Flow], Dict[str, Any]]]:
        """Get flow type, class and kwargs for action"""
        # Check predefined flows
        if action in self.FLOW_TYPES:
            flow_type, flow_class = self.FLOW_TYPES[action]
            return flow_type, flow_class, {}

        # No direct commands in production - users will use the list interface
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
            # Start fresh flow
            flow = flow_class(flow_type=flow_type, **kwargs)
            flow.credex_service = self.credex_service
            flow.current_index = 0  # Ensure we start at first step
            flow.data = {}  # Start with empty data

            # Get member and account IDs
            member_id, account_id = self._get_member_info()
            if not member_id or not account_id:
                logger.error(f"Missing required IDs - member_id: {member_id}, account_id: {account_id}")
                return WhatsAppMessage.create_text(
                    self.user.mobile_number,
                    "Account not properly initialized. Please try sending 'hi' to restart."
                )

            # Set only essential base data
            flow.data = {
                "phone": self.user.mobile_number,
                "member_id": member_id,
                "account_id": account_id,
                "mobile_number": self.user.mobile_number
            }

            # Log flow initialization
            logger.debug(f"Initialized new flow: {flow.id} at step {flow.current_index}")
            logger.debug(f"Initial flow data: {flow.data}")

            # Add pending offers for cancel flow
            if flow_type == "cancel_credex":
                current_account = self.user.state.state.get("current_account", {})
                pending_out = current_account.get("pendingOutData", [])

                pending_offers = [{
                    "id": offer.get("credexID"),
                    "amount": offer.get("formattedInitialAmount", "0").lstrip("-"),
                    "to": offer.get("counterpartyAccountName")
                } for offer in pending_out if all(
                    offer.get(k) for k in ["credexID", "formattedInitialAmount", "counterpartyAccountName"]
                )]

                flow.data["pending_offers"] = pending_offers
                logger.debug(f"Added pending offers to flow: {pending_offers}")

            # Get initial message (already in WhatsAppMessage format)
            result = flow.current_step.get_message(flow.data)

            # Save flow state while preserving critical fields
            current_state = self.user.state.state or {}
            new_state = {
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
            }

            # Log state transition with detailed flow info
            logger.debug(
                f"Flow state transition [START - {flow_type}]:\n"
                f"Flow ID: {flow.id}\n"
                f"Initial step: {flow.current_index}\n"
                f"Initial data: {flow.data}\n"
                f"From state: {current_state}\n"
                f"To state: {new_state}"
            )

            self.user.state.update_state(new_state, "flow_start")

            return result  # Already in WhatsAppMessage format

        except Exception as e:
            logger.error(f"Flow start error: {str(e)}")
            return WhatsAppMessage.create_text(
                self.user.mobile_number,
                f"❌ Failed to start flow: {str(e)}"
            )

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

            # Log flow state before setting new state
            logger.debug(f"Flow continuation - Type: {flow_type}, ID: {flow_id}")
            logger.debug(f"Current flow data: {flow_data}")

            flow.set_state({
                "id": flow_data["id"],
                "step": flow_data["step"],
                "data": flow_data["data"]
            })

            # Process input
            result = None
            if self.message_type == "interactive":
                # Pass the original interactive message structure
                interactive = self.message.get("interactive", {})
                logger.debug(f"Processing interactive message: {interactive}")
                result = flow.process_input({
                    "type": "interactive",
                    "interactive": interactive
                })
            else:
                # Handle text messages
                logger.debug(f"Processing text message: {self.body}")
                result = flow.process_input(self.body)

            # Handle invalid input
            if result == "Invalid input":
                if flow.current_step and flow.current_step.id == "amount":
                    return WhatsAppMessage.create_text(
                        self.user.mobile_number,
                        "Invalid amount format. Examples:\n"
                        "100     (USD)\n"
                        "USD 100\n"
                        "ZWG 100\n"
                        "XAU 1"
                    )
                return WhatsAppMessage.create_text(
                    self.user.mobile_number,
                    "Invalid input"
                )

            # Handle flow completion
            if not result or flow.current_index >= len(flow.steps):
                # Log completion
                logger.debug(f"Flow completed - Type: {flow_type}, ID: {flow_id}")
                logger.debug(f"Final flow data: {flow.data}")

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

                return result  # Already in WhatsAppMessage format

            # Update flow state while preserving critical fields
            current_state = self.user.state.state or {}
            new_state = {
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
            }

            # Log state transition with detailed flow info
            logger.debug(
                f"Flow state transition [CONTINUE - {flow_type}]:\n"
                f"Flow ID: {flow.id}\n"
                f"Current step: {flow.current_index}\n"
                f"Current data: {flow.data}\n"
                f"From state: {current_state}\n"
                f"To state: {new_state}"
            )

            self.user.state.update_state(new_state, "flow_continue")

            return result  # Already in WhatsAppMessage format

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
            return WhatsAppMessage.create_text(
                self.user.mobile_number,
                f"❌ {str(e)}"
            )

    def _process_message(self) -> WhatsAppMessage:
        """Process incoming message"""
        try:
            # Check for active flow first
            flow_data = self.user.state.state.get("flow_data") if self.user.state.state else None
            if flow_data:
                return self._continue_flow(flow_data)

            # Handle greeting
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
                        "member_id": current_state.get("member_id"),
                        "account_id": current_state.get("account_id")
                    }, "clear_flow_greeting")
                return self.auth_handler.handle_action_menu(login=True)

            # Get action and check if it's a menu action
            action = self._get_action()
            logger.info(f"Processing action: {action}")

            if action in self.FLOW_TYPES:
                # First clean up any existing state while preserving critical fields
                if self.user.state.state:
                    current_state = self.user.state.state
                    preserve_fields = {"jwt_token", "profile", "current_account", "member_id", "account_id"}
                    logger.debug(f"Cleaning up state, preserving fields: {preserve_fields}")
                    success, error = self.user.state.cleanup_state(preserve_fields)
                    if not success:
                        logger.error(f"Failed to cleanup state: {error}")
                        return WhatsAppMessage.create_text(
                            self.user.mobile_number,
                            "Failed to initialize flow. Please try sending 'hi' to restart."
                        )

                    # Get preserved state after cleanup
                    preserved_state = self.user.state.state or {}

                    # Initialize new state with preserved fields
                    new_state = {
                        "flow_data": None,
                        "profile": preserved_state.get("profile", {}),
                        "current_account": preserved_state.get("current_account"),
                        "jwt_token": preserved_state.get("jwt_token"),
                        "member_id": preserved_state.get("member_id"),
                        "account_id": preserved_state.get("account_id")
                    }

                    # Log state transition with cleanup details
                    logger.debug(
                        "Flow state transition [CLEAR]:\n"
                        f"Action: {action}\n"
                        f"Preserved fields: {preserve_fields}\n"
                        f"From state: {current_state}\n"
                        f"To state: {new_state}"
                    )

                    # Update state with preserved fields
                    self.user.state.update_state(new_state, "clear_flow_menu_action")

                # Then start the new flow with a fresh state
                flow_type, flow_class = self.FLOW_TYPES[action]
                return self._start_flow(flow_type, flow_class)

            # If no active flow and not a menu action, default to menu
            return self.auth_handler.handle_action_menu()

        except Exception as e:
            logger.error(f"Message processing error: {str(e)}")
            return WhatsAppMessage.create_text(
                self.user.mobile_number,
                f"❌ {str(e)}"
            )

    def handle(self) -> WhatsAppMessage:
        """Return processed response"""
        return self.response
