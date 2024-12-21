"""WhatsApp message handling implementation"""
import logging
from typing import Any, Dict, Optional, Tuple, Type

from core.messaging.flow import Flow
from core.utils.flow_audit import FlowAuditLogger
from .types import WhatsAppMessage
from .state_manager import StateManager
from .handlers.credex import CredexFlow
from .handlers.member import RegistrationFlow, UpgradeFlow, DashboardFlow

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class MessageHandler:
    """Handler for WhatsApp messages and flows"""

    FLOW_TYPES = {
        "offer_credex": ("offer", CredexFlow),
        "accept_credex": ("accept", CredexFlow),
        "decline_credex": ("decline", CredexFlow),
        "cancel_credex": ("cancel_credex", CredexFlow),
        "start_registration": ("registration", RegistrationFlow),
        "upgrade_tier": ("upgrade", UpgradeFlow)
    }

    GREETING_KEYWORDS = {"hi", "hello", "hey", "start"}
    BUTTON_ACTIONS = {"confirm_action"}

    def __init__(self, service: Any):
        """Initialize handler with service reference"""
        self.service = service

    def _get_action(self) -> str:
        """Extract action from message"""
        # Handle interactive messages
        if self.service.message_type == "interactive":
            interactive = self.service.message.get("interactive", {})
            if interactive.get("type") == "list_reply":
                return interactive.get("list_reply", {}).get("id", "").lower()
            elif interactive.get("type") == "button_reply":
                return interactive.get("button_reply", {}).get("id", "").lower()

        # For text messages
        return self.service.body.strip().lower()

    def _get_member_info(self) -> Tuple[Optional[str], Optional[str]]:
        """Extract member and account IDs from state"""
        try:
            state = self.service.user.state.state or {}
            member_id = state.get("member_id")
            account_id = state.get("account_id")
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

            # Get member and account IDs
            member_id, account_id = self._get_member_info()
            if not member_id or not account_id:
                logger.error(f"Missing required IDs - member_id: {member_id}, account_id: {account_id}")
                return WhatsAppMessage.create_text(
                    self.service.user.mobile_number,
                    "Account not properly initialized. Please try sending 'hi' to restart."
                )

            # Prepare initial state
            initial_state = {
                "id": f"{flow_type}_{member_id}",
                "step": 0,
                "data": {
                    "phone": self.service.user.mobile_number,
                    "member_id": member_id,
                    "account_id": account_id,
                    "mobile_number": self.service.user.mobile_number
                }
            }

            # Add pending offers for cancel flow
            if flow_type == "cancel_credex":
                current_state = self.service.user.state.state or {}
                current_account = current_state.get("current_account", {})
                pending_out = current_account.get("pendingOutData", [])

                pending_offers = [{
                    "id": offer.get("credexID"),
                    "amount": offer.get("formattedInitialAmount", "0").lstrip("-"),
                    "to": offer.get("counterpartyAccountName")
                } for offer in pending_out if all(
                    offer.get(k) for k in ["credexID", "formattedInitialAmount", "counterpartyAccountName"]
                )]

                initial_state["data"]["pending_offers"] = pending_offers

            # Initialize flow with state
            flow = flow_class(**kwargs) if flow_class in {RegistrationFlow, UpgradeFlow} else flow_class(
                flow_type=flow_type,
                state=initial_state,
                **kwargs
            )
            flow.credex_service = self.service.credex_service

            # Get initial message
            result = flow.current_step.get_message(flow.data)

            # Prepare new state with flow data
            current_state = self.service.user.state.state or {}
            new_state = StateManager.prepare_state_update(
                current_state,
                flow_data={
                    **flow.get_state(),
                    "flow_type": flow_type,
                    "kwargs": kwargs
                },
                mobile_number=self.service.user.mobile_number
            )

            # Validate and update state
            error = StateManager.validate_and_update(
                self.service.user.state,
                new_state,
                current_state,
                "flow_start",
                self.service.user.mobile_number
            )
            if error:
                return error

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
                self.service.user.mobile_number,
                f"❌ Failed to start flow: {str(e)}"
            )

    def _continue_flow(self, flow_data: Dict[str, Any]) -> WhatsAppMessage:
        """Continue an existing flow"""
        try:
            # Check for greeting first
            if (self.service.message_type == "text" and
                    self.service.body.lower() in self.GREETING_KEYWORDS):
                current_state = self.service.user.state.state or {}
                new_state = StateManager.prepare_state_update(
                    current_state,
                    clear_flow=True,
                    mobile_number=self.service.user.mobile_number
                )
                error = StateManager.validate_and_update(
                    self.service.user.state,
                    new_state,
                    current_state,
                    "greeting_reset",
                    self.service.user.mobile_number
                )
                if error:
                    return error

                return self.service.auth_handler.handle_action_menu(login=True)

            # Get flow info
            flow_type = flow_data.get("flow_type")
            kwargs = flow_data.get("kwargs", {})
            if not flow_type:
                raise ValueError("Missing flow type")

            # Initialize flow with state
            flow_id = flow_data.get("id", "")
            if "member_registration" in flow_id:
                flow_class = RegistrationFlow
            elif "member_upgrade" in flow_id:
                flow_class = UpgradeFlow
            else:
                flow_class = CredexFlow

            # Create initial state
            initial_state = {
                "id": flow_data["id"],
                "step": flow_data["step"],
                "data": flow_data["data"]
            }

            # Initialize flow with state and ensure current_index matches step
            flow = flow_class(**kwargs) if flow_class in {RegistrationFlow, UpgradeFlow} else flow_class(
                flow_type=flow_type,
                state=initial_state,
                **kwargs
            )
            flow.credex_service = self.service.credex_service
            flow.current_index = flow_data["step"]  # Ensure we're on the correct step

            # Extract input value based on message type
            input_value = self.service.body
            if self.service.message_type == "interactive":
                interactive = self.service.message.get("interactive", {})
                if interactive.get("type") == "button_reply":
                    input_value = interactive.get("button_reply", {})
                elif interactive.get("type") == "list_reply":
                    input_value = interactive.get("list_reply", {})

            # Process input with proper value extraction
            result = flow.process_input(input_value)

            # Handle invalid input
            if result == "Invalid input":
                audit.log_flow_event(
                    "bot_service",
                    "invalid_input",
                    flow.current_step.id if flow.current_step else None,
                    {"input": self.service.body},
                    "failure"
                )

                # Get current state
                current_state = self.service.user.state.state or {}

                # Prepare error state
                error_state = StateManager.prepare_state_update(
                    current_state,
                    flow_data={
                        **flow.get_state(),
                        "flow_type": flow_type,
                        "kwargs": kwargs,
                        "_validation_error": True
                    },
                    mobile_number=self.service.user.mobile_number
                )

                # Update state with error
                error = StateManager.validate_and_update(
                    self.service.user.state,
                    error_state,
                    current_state,
                    "flow_validation_error",
                    self.service.user.mobile_number
                )
                if error:
                    return error

                if flow.current_step and flow.current_step.id == "amount":
                    return WhatsAppMessage.create_text(
                        self.service.user.mobile_number,
                        "Invalid amount format. Examples:\n"
                        "100     (USD)\n"
                        "USD 100\n"
                        "ZWG 100\n"
                        "XAU 1\n\n"
                        "Please ensure you enter a valid number with an optional currency code."
                    )
                return WhatsAppMessage.create_text(
                    self.service.user.mobile_number,
                    "Invalid input. Please try again with a valid option."
                )

            # Handle flow completion
            if not result:
                return self.service.auth_handler.handle_action_menu()

            # Check if we're at confirmation step
            if flow.current_step and flow.current_step.id == "confirm":
                audit.log_flow_event(
                    "bot_service",
                    "flow_complete",
                    None,
                    flow.data,
                    "success"
                )

                # Get current state
                current_state = self.service.user.state.state or {}

                if "credex_" in flow_id:
                    # Complete the flow and check result
                    result = flow.complete()

                    # Check if result indicates an error
                    if isinstance(result, dict):
                        if not result.get("success", False):
                            # Return error message if API call failed
                            return WhatsAppMessage.create_text(
                                self.service.user.mobile_number,
                                result.get("message", "Operation failed")
                            )

                        # Get API response for dashboard update
                        api_response = result.get("response", {})
                        if api_response:
                            # Update dashboard with API response
                            flow.credex_service._update_dashboard(api_response)

                        # Prepare completion state after successful API call
                        new_state = StateManager.prepare_state_update(
                            current_state,
                            clear_flow=True,
                            mobile_number=self.service.user.mobile_number
                        )

                        # Update state for completion
                        error = StateManager.validate_and_update(
                            self.service.user.state,
                            new_state,
                            current_state,
                            "flow_complete",
                            self.service.user.mobile_number
                        )
                        if error:
                            return error

                        # Only show success message if API call succeeded
                        dashboard = DashboardFlow(
                            success_message=result.get("message")
                        )
                        dashboard.credex_service = self.service.credex_service
                        dashboard.data = {"mobile_number": self.service.user.mobile_number}
                        return dashboard.complete()

                    # If not a dict response, treat as error
                    return WhatsAppMessage.create_text(
                        self.service.user.mobile_number,
                        "Operation failed: Invalid response format"
                    )

                return result

            # Not at confirmation step yet, continue flow
            if flow.current_index >= len(flow.steps):
                # Reset flow if we somehow got past all steps without confirmation
                current_state = self.service.user.state.state or {}
                new_state = StateManager.prepare_state_update(
                    current_state,
                    clear_flow=True,
                    mobile_number=self.service.user.mobile_number
                )
                StateManager.validate_and_update(
                    self.service.user.state,
                    new_state,
                    current_state,
                    "flow_reset",
                    self.service.user.mobile_number
                )
                return self.service.auth_handler.handle_action_menu()

            # Get current state
            current_state = self.service.user.state.state or {}
            flow_state = flow.get_state()

            # Prepare continuation state
            new_state = StateManager.prepare_state_update(
                current_state,
                flow_data={
                    **flow_state,
                    "flow_type": flow_type,
                    "kwargs": kwargs
                },
                mobile_number=self.service.user.mobile_number
            )

            # Update state for continuation
            error = StateManager.validate_and_update(
                self.service.user.state,
                new_state,
                current_state,
                "flow_continue",
                self.service.user.mobile_number
            )
            if error:
                return error

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

            # Get current state
            current_state = self.service.user.state.state or {}

            # Prepare error state
            error_state = StateManager.prepare_state_update(
                current_state,
                clear_flow=True,
                mobile_number=self.service.user.mobile_number
            )

            # Update state for error
            StateManager.validate_and_update(
                self.service.user.state,
                error_state,
                current_state,
                "flow_error",
                self.service.user.mobile_number
            )

            return WhatsAppMessage.create_text(
                self.service.user.mobile_number,
                f"❌ {str(e)}"
            )

    def process_message(self) -> WhatsAppMessage:
        """Process incoming message"""
        try:
            # Log message processing start
            audit.log_flow_event(
                "bot_service",
                "message_processing",
                None,
                {
                    "message_type": self.service.message_type,
                    "body": self.service.body if self.service.message_type == "text" else None
                },
                "in_progress"
            )

            # Handle greeting first - always reset state and show menu
            if (self.service.message_type == "text" and
                    self.service.body.lower() in self.GREETING_KEYWORDS):
                current_state = self.service.user.state.state or {}

                # Prepare new state with preserved context
                new_state = StateManager.prepare_state_update(
                    current_state,
                    clear_flow=True,
                    mobile_number=self.service.user.mobile_number
                )

                # Validate and update state
                error = StateManager.validate_and_update(
                    self.service.user.state,
                    new_state,
                    current_state,
                    "greeting_reset",
                    self.service.user.mobile_number
                )
                if error:
                    return error

                return self.service.auth_handler.handle_action_menu(login=True)

            # Check for active flow
            flow_data = self.service.user.state.state.get("flow_data") if self.service.user.state.state else None
            if flow_data:
                return self._continue_flow(flow_data)

            # Get action and check if it's a menu action
            action = self._get_action()
            logger.info(f"Processing action: {action}")

            if action in self.FLOW_TYPES:
                current_state = self.service.user.state.state or {}

                # Prepare new state for flow start
                new_state = StateManager.prepare_state_update(
                    current_state,
                    clear_flow=True,
                    mobile_number=self.service.user.mobile_number
                )

                # Validate and update state
                error = StateManager.validate_and_update(
                    self.service.user.state,
                    new_state,
                    current_state,
                    "clear_flow_menu_action",
                    self.service.user.mobile_number
                )
                if error:
                    return error

                # Start new flow
                flow_type, flow_class = self.FLOW_TYPES[action]
                return self._start_flow(flow_type, flow_class)

            # If no active flow and not a menu action, default to menu
            return self.service.auth_handler.handle_action_menu()

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
                self.service.user.mobile_number,
                f"❌ {str(e)}"
            )
