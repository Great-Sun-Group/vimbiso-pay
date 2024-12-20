"""WhatsApp message handling implementation"""
import logging
from typing import Dict, Any, Optional, Tuple, Type

from core.messaging.flow import Flow
from core.utils.state_validator import StateValidator
from core.utils.flow_audit import FlowAuditLogger
from .base_handler import BaseActionHandler
from .types import BotServiceInterface, WhatsAppMessage
from .auth_handlers import AuthActionHandler
from .handlers.credex import CredexFlow
from .handlers.member.flows import MemberFlow
from .handlers.member.dashboard import DashboardFlow

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


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

        # Log service initialization
        audit.log_flow_event(
            "bot_service",
            "initialization",
            None,
            {"mobile_number": user.mobile_number},
            "in_progress"
        )

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

            # Validate state
            validation = StateValidator.validate_state(state)
            if not validation.is_valid:
                audit.log_flow_event(
                    "bot_service",
                    "state_validation_error",
                    None,
                    state,
                    "failure",
                    validation.error_message
                )
                return None, None

            # Get IDs directly from state root where auth_handlers.py stores them
            member_id = state.get("member_id")
            account_id = state.get("account_id")

            # Log the values for debugging
            logger.debug(f"Retrieved member_id: {member_id}, account_id: {account_id} from state")

            return member_id, account_id

        except Exception as e:
            logger.error(f"Error extracting member info: {str(e)}")
            audit.log_flow_event(
                "bot_service",
                "member_info_error",
                None,
                {"error": str(e)},
                "failure"
            )
            return None, None

    def _start_flow(self, flow_type: str, flow_class: Type[Flow], **kwargs) -> WhatsAppMessage:
        """Start a new flow"""
        try:
            # Log flow start attempt
            audit.log_flow_event(
                "bot_service",
                "flow_start_attempt",
                None,
                {
                    "flow_type": flow_type,
                    "flow_class": flow_class.__name__,
                    **kwargs
                },
                "in_progress"
            )

            # Preserve existing state before starting new flow
            current_state = self.user.state.state or {}

            # Validate current state
            validation = StateValidator.validate_state(current_state)
            if not validation.is_valid:
                audit.log_flow_event(
                    "bot_service",
                    "state_validation_error",
                    None,
                    current_state,
                    "failure",
                    validation.error_message
                )
                # Attempt recovery from last valid state
                last_valid = audit.get_last_valid_state("bot_service")
                if last_valid:
                    current_state = last_valid

            existing_flow_data = current_state.get("flow_data", {})

            # Start fresh flow
            flow = flow_class(flow_type=flow_type, **kwargs)
            flow.credex_service = self.credex_service
            flow.current_index = 0  # Ensure we start at first step

            # Initialize with existing data if available
            flow.data = existing_flow_data.get("data", {}) if existing_flow_data else {}

            # Get member and account IDs
            member_id, account_id = self._get_member_info()
            if not member_id or not account_id:
                logger.error(f"Missing required IDs - member_id: {member_id}, account_id: {account_id}")
                audit.log_flow_event(
                    "bot_service",
                    "flow_start_error",
                    None,
                    {"error": "Missing required IDs"},
                    "failure"
                )
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

            # Add pending offers for cancel flow
            if flow_type == "cancel_credex":
                current_account = current_state.get("current_account", {})
                pending_out = current_account.get("pendingOutData", [])

                pending_offers = [{
                    "id": offer.get("credexID"),
                    "amount": offer.get("formattedInitialAmount", "0").lstrip("-"),
                    "to": offer.get("counterpartyAccountName")
                } for offer in pending_out if all(
                    offer.get(k) for k in ["credexID", "formattedInitialAmount", "counterpartyAccountName"]
                )]

                flow.data["pending_offers"] = pending_offers

            # Get initial message (already in WhatsAppMessage format)
            result = flow.current_step.get_message(flow.data)

            # Prepare new state
            new_state = {
                "flow_data": {
                    **flow.get_state(),
                    "flow_type": flow_type,
                    "kwargs": kwargs
                },
                "profile": current_state.get("profile", {}),
                "current_account": current_state.get("current_account"),
                "jwt_token": current_state.get("jwt_token"),
                "member_id": current_state.get("member_id"),
                "account_id": current_state.get("account_id")
            }

            # Validate new state
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                audit.log_flow_event(
                    "bot_service",
                    "state_validation_error",
                    None,
                    new_state,
                    "failure",
                    validation.error_message
                )
                return WhatsAppMessage.create_text(
                    self.user.mobile_number,
                    f"Failed to start flow: {validation.error_message}"
                )

            # Log state transition
            audit.log_state_transition(
                "bot_service",
                current_state,
                new_state,
                "success"
            )

            self.user.state.update_state(new_state, "flow_start")

            audit.log_flow_event(
                "bot_service",
                "flow_start_success",
                None,
                {"flow_id": flow.id},
                "success"
            )

            return result

        except Exception as e:
            logger.error(f"Flow start error: {str(e)}")
            audit.log_flow_event(
                "bot_service",
                "flow_start_error",
                None,
                {"error": str(e)},
                "failure"
            )
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
            # Log flow continuation attempt
            audit.log_flow_event(
                "bot_service",
                "flow_continue_attempt",
                None,
                flow_data,
                "in_progress"
            )

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
                result = flow.process_input({
                    "type": "interactive",
                    "interactive": interactive
                })
            else:
                result = flow.process_input(self.body)

            # Enhanced invalid input handling
            if result == "Invalid input":
                audit.log_flow_event(
                    "bot_service",
                    "invalid_input",
                    flow.current_step.id if flow.current_step else None,
                    {"input": self.body},
                    "failure"
                )
                if flow.current_step and flow.current_step.id == "amount":
                    return WhatsAppMessage.create_text(
                        self.user.mobile_number,
                        "Invalid amount format. Examples:\n"
                        "100     (USD)\n"
                        "USD 100\n"
                        "ZWG 100\n"
                        "XAU 1\n\n"
                        "Please ensure you enter a valid number with an optional currency code."
                    )
                return WhatsAppMessage.create_text(
                    self.user.mobile_number,
                    "Invalid input. Please try again with a valid option."
                )

            # Handle flow completion
            if not result or flow.current_index >= len(flow.steps):
                audit.log_flow_event(
                    "bot_service",
                    "flow_complete",
                    None,
                    flow.data,
                    "success"
                )

                # Get current state for transition logging
                current_state = self.user.state.state or {}

                # Prepare new state
                new_state = {
                    "flow_data": None,
                    "profile": current_state.get("profile", {}),
                    "current_account": current_state.get("current_account"),
                    "jwt_token": current_state.get("jwt_token"),
                    "member_id": current_state.get("member_id"),
                    "account_id": current_state.get("account_id")
                }

                # Validate new state
                validation = StateValidator.validate_state(new_state)
                if not validation.is_valid:
                    audit.log_flow_event(
                        "bot_service",
                        "state_validation_error",
                        None,
                        new_state,
                        "failure",
                        validation.error_message
                    )
                    return WhatsAppMessage.create_text(
                        self.user.mobile_number,
                        f"Failed to update state: {validation.error_message}"
                    )

                # Log state transition
                audit.log_state_transition(
                    "bot_service",
                    current_state,
                    new_state,
                    "success"
                )

                self.user.state.update_state(new_state, "flow_complete")

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

                return result

            # Get current state for transition logging
            current_state = self.user.state.state or {}
            flow_state = flow.get_state()

            # Preserve previous flow data if it exists
            if "_previous_data" in flow_state:
                flow_state["_previous_data"] = {
                    **flow_state.get("_previous_data", {}),
                    **current_state.get("flow_data", {}).get("_previous_data", {})
                }

            # Prepare new state
            new_state = {
                "flow_data": {
                    **flow_state,
                    "flow_type": flow_type,
                    "kwargs": kwargs,
                },
                "profile": current_state.get("profile", {}),
                "current_account": current_state.get("current_account"),
                "jwt_token": current_state.get("jwt_token"),
                "member_id": current_state.get("member_id"),
                "account_id": current_state.get("account_id"),
                "_previous_state": current_state
            }

            # Validate new state
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                audit.log_flow_event(
                    "bot_service",
                    "state_validation_error",
                    None,
                    new_state,
                    "failure",
                    validation.error_message
                )
                return WhatsAppMessage.create_text(
                    self.user.mobile_number,
                    f"Failed to update state: {validation.error_message}"
                )

            # Log state transition
            audit.log_state_transition(
                "bot_service",
                current_state,
                new_state,
                "success"
            )

            self.user.state.update_state(new_state, "flow_continue")

            return result

        except Exception as e:
            logger.error(f"Flow error: {str(e)}")
            audit.log_flow_event(
                "bot_service",
                "flow_error",
                None,
                {"error": str(e)},
                "failure"
            )

            # Get current state for transition logging
            current_state = self.user.state.state or {}

            # Prepare new state
            new_state = {
                "flow_data": None,
                "profile": current_state.get("profile", {}),
                "current_account": current_state.get("current_account"),
                "jwt_token": current_state.get("jwt_token"),
                "member_id": current_state.get("member_id"),
                "account_id": current_state.get("account_id")
            }

            # Validate new state
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                audit.log_flow_event(
                    "bot_service",
                    "state_validation_error",
                    None,
                    new_state,
                    "failure",
                    validation.error_message
                )
                return WhatsAppMessage.create_text(
                    self.user.mobile_number,
                    f"Failed to update state: {validation.error_message}"
                )

            # Log state transition
            audit.log_state_transition(
                "bot_service",
                current_state,
                new_state,
                "success"
            )

            self.user.state.update_state(new_state, "flow_error")

            return WhatsAppMessage.create_text(
                self.user.mobile_number,
                f"❌ {str(e)}"
            )

    def _process_message(self) -> WhatsAppMessage:
        """Process incoming message"""
        try:
            # Log message processing start
            audit.log_flow_event(
                "bot_service",
                "message_processing",
                None,
                {
                    "message_type": self.message_type,
                    "body": self.body if self.message_type == "text" else None
                },
                "in_progress"
            )

            # Check for active flow first
            flow_data = self.user.state.state.get("flow_data") if self.user.state.state else None
            if flow_data:
                return self._continue_flow(flow_data)

            # Handle greeting
            if (self.message_type == "text" and
                    self.body.lower() in self.GREETING_KEYWORDS):
                # Get current state for transition logging
                current_state = self.user.state.state or {}

                # Prepare new state
                new_state = {
                    "flow_data": None,
                    "profile": current_state.get("profile", {}),
                    "current_account": current_state.get("current_account"),
                    "jwt_token": current_state.get("jwt_token"),
                    "authenticated": current_state.get("authenticated", False),
                    "member_id": current_state.get("member_id"),
                    "account_id": current_state.get("account_id")
                }

                # Validate new state
                validation = StateValidator.validate_state(new_state)
                if not validation.is_valid:
                    audit.log_flow_event(
                        "bot_service",
                        "state_validation_error",
                        None,
                        new_state,
                        "failure",
                        validation.error_message
                    )
                    return WhatsAppMessage.create_text(
                        self.user.mobile_number,
                        f"Failed to update state: {validation.error_message}"
                    )

                # Log state transition
                audit.log_state_transition(
                    "bot_service",
                    current_state,
                    new_state,
                    "success"
                )

                self.user.state.update_state(new_state, "clear_flow_greeting")
                return self.auth_handler.handle_action_menu(login=True)

            # Get action and check if it's a menu action
            action = self._get_action()
            logger.info(f"Processing action: {action}")

            if action in self.FLOW_TYPES:
                # Get current state for transition logging
                current_state = self.user.state.state or {}

                # Prepare new state
                new_state = {
                    "flow_data": None,
                    "profile": current_state.get("profile", {}),
                    "current_account": current_state.get("current_account"),
                    "jwt_token": current_state.get("jwt_token"),
                    "member_id": current_state.get("member_id"),
                    "account_id": current_state.get("account_id")
                }

                # Validate new state
                validation = StateValidator.validate_state(new_state)
                if not validation.is_valid:
                    audit.log_flow_event(
                        "bot_service",
                        "state_validation_error",
                        None,
                        new_state,
                        "failure",
                        validation.error_message
                    )
                    return WhatsAppMessage.create_text(
                        self.user.mobile_number,
                        f"Failed to update state: {validation.error_message}"
                    )

                # Log state transition
                audit.log_state_transition(
                    "bot_service",
                    current_state,
                    new_state,
                    "success"
                )

                self.user.state.update_state(new_state, "clear_flow_menu_action")

                # Then start the new flow with a fresh state
                flow_type, flow_class = self.FLOW_TYPES[action]
                return self._start_flow(flow_type, flow_class)

            # If no active flow and not a menu action, default to menu
            return self.auth_handler.handle_action_menu()

        except Exception as e:
            logger.error(f"Message processing error: {str(e)}")
            audit.log_flow_event(
                "bot_service",
                "message_processing_error",
                None,
                {"error": str(e)},
                "failure"
            )
            return WhatsAppMessage.create_text(
                self.user.mobile_number,
                f"❌ {str(e)}"
            )

    def handle(self) -> WhatsAppMessage:
        """Return processed response"""
        return self.response
