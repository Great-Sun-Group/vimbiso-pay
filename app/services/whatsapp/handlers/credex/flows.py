"""Unified credex flow implementation"""
import logging
import re
from typing import Any, Dict, List, Union

from core.messaging.flow import Flow, Step, StepType
from core.utils.state_validator import StateValidator
from core.utils.flow_audit import FlowAuditLogger
from ...handlers.member.dashboard import DashboardFlow
from .templates import CredexTemplates

audit = FlowAuditLogger()

logger = logging.getLogger(__name__)


class CredexFlow(Flow):
    """Base class for all credex flows"""

    VALID_DENOMINATIONS = {"USD", "ZWG", "XAU", "CAD"}
    AMOUNT_PATTERN = re.compile(r'^(?:([A-Z]{3})\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:\(?([A-Z]{3})\)?)|(\d+(?:\.\d+)?))$')
    HANDLE_PATTERN = re.compile(r'^[a-zA-Z0-9_]+$')

    def __init__(self, flow_type: str, **kwargs):
        """Initialize flow"""
        self.flow_type = flow_type
        self.kwargs = kwargs
        steps = self._create_steps()
        super().__init__(f"credex_{flow_type}", steps)
        self.credex_service = None

    def _create_steps(self) -> List[Step]:
        """Create flow steps based on type"""
        if self.flow_type == "offer":
            return [
                Step(
                    id="amount",
                    type=StepType.TEXT,
                    message=self._get_amount_prompt,
                    validator=self._validate_amount,
                    transformer=self._transform_amount
                ),
                Step(
                    id="handle",
                    type=StepType.TEXT,
                    message=lambda s: CredexTemplates.create_handle_prompt(
                        self.data.get("mobile_number")
                    ),
                    validator=self._validate_handle,
                    transformer=self._transform_handle
                ),
                Step(
                    id="confirm",
                    type=StepType.BUTTON,
                    message=self._create_confirmation_message,
                    validator=self._validate_button_response
                )
            ]
        elif self.flow_type == "cancel_credex":
            return [
                Step(
                    id="list",
                    type=StepType.LIST,
                    message=self._create_list_message,
                    validator=lambda x: x.startswith("cancel_"),
                    transformer=self._transform_cancel_selection
                ),
                Step(
                    id="confirm",
                    type=StepType.BUTTON,
                    message=self._create_confirmation_message,
                    validator=self._validate_button_response
                )
            ]
        else:
            return [
                Step(
                    id="confirm",
                    type=StepType.BUTTON,
                    message=self._create_confirmation_message,
                    validator=self._validate_button_response
                )
            ]

    def _get_amount_prompt(self, _) -> Dict[str, Any]:
        """Get amount prompt message"""
        return CredexTemplates.create_amount_prompt(
            self.data.get("mobile_number")
        )

    def _create_list_message(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create list selection message"""
        return CredexTemplates.create_pending_offers_list(
            self.data.get("mobile_number"),
            state.get("pending_offers", [])
        )

    def _create_confirmation_message(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create confirmation message based on flow type"""
        messages = {
            "offer": self._create_offer_confirmation,
            "cancel_credex": self._create_cancel_confirmation,
            "accept": lambda s: self._create_action_confirmation(s, "Accept"),
            "decline": lambda s: self._create_action_confirmation(s, "Decline")
        }

        return messages[self.flow_type](state)

    def _create_offer_confirmation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create offer confirmation message"""
        amount_data = state.get("amount_denom", {})
        amount = self._format_amount(
            amount_data.get("amount", 0),
            amount_data.get("denomination", "USD")
        )
        handle = state["handle"]["handle"]
        name = state["handle"]["name"]

        return CredexTemplates.create_offer_confirmation(
            self.data.get("mobile_number"),
            amount,
            handle,
            name
        )

    def _create_cancel_confirmation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create cancel confirmation message"""
        amount = state.get("amount", "0")
        counterparty = state.get("counterparty", "Unknown")

        return CredexTemplates.create_cancel_confirmation(
            self.data.get("mobile_number"),
            amount,
            counterparty
        )

    def _create_action_confirmation(self, state: Dict[str, Any], action: str) -> Dict[str, Any]:
        """Create action confirmation message"""
        amount = self._format_amount(
            float(state.get("amount", "0.00")),
            state.get("denomination", "USD")
        )
        counterparty = state.get("counterparty", "Unknown")

        return CredexTemplates.create_action_confirmation(
            self.data.get("mobile_number"),
            amount,
            counterparty,
            action
        )

    def _validate_button_response(self, response: Dict[str, Any]) -> bool:
        """Validate button response"""
        if not isinstance(response, dict):
            return False

        if response.get("type") != "interactive":
            return False

        interactive = response.get("interactive", {})
        if not interactive:
            return False

        # Handle both button and list replies
        if interactive.get("type") == "button_reply":
            return interactive.get("button_reply", {}).get("id") == "confirm_action"
        elif interactive.get("type") == "list_reply":
            return interactive.get("list_reply", {}).get("id") == "offer_credex"

        return False

    def _transform_cancel_selection(self, selection: str) -> Dict[str, Any]:
        """Transform cancel selection"""
        credex_id = selection[7:] if selection.startswith("cancel_") else None
        if not credex_id:
            return {"error": "Invalid selection"}

        pending_offers = self.data.get("pending_offers", [])
        selected_offer = next(
            (offer for offer in pending_offers if offer["id"] == credex_id),
            None
        )

        if not selected_offer:
            return {"error": "Selected offer not found"}

        return {
            "credex_id": credex_id,
            "amount": selected_offer["amount"],
            "counterparty": selected_offer["to"]
        }

    def _validate_amount(self, amount_data: Union[str, Dict[str, Any]]) -> bool:
        """Validate amount format"""
        # Handle already transformed amount
        if isinstance(amount_data, dict):
            return (
                "amount" in amount_data and
                "denomination" in amount_data and
                isinstance(amount_data["amount"], (int, float)) and
                (not amount_data["denomination"] or amount_data["denomination"] in self.VALID_DENOMINATIONS)
            )

        # Handle string input
        if not amount_data:
            return False
        match = self.AMOUNT_PATTERN.match(str(amount_data).strip().upper())
        if not match:
            return False
        denom = match.group(1) or match.group(4)
        return not denom or denom in self.VALID_DENOMINATIONS

    def _transform_amount(self, amount_str: str) -> Dict[str, Any]:
        """Transform amount string to structured data"""
        match = self.AMOUNT_PATTERN.match(amount_str.strip().upper())
        if match.group(1):  # Currency first
            denom, amount = match.group(1), match.group(2)
        elif match.group(3):  # Amount first
            amount, denom = match.group(3), match.group(4)
        else:  # Just amount
            amount, denom = match.group(5), None
        return {
            "amount": float(amount),
            "denomination": denom or "USD"
        }

    def _validate_handle(self, handle: Union[str, Dict[str, Any]]) -> bool:
        """Validate handle format"""
        # Handle interactive message
        if isinstance(handle, dict):
            interactive = handle.get("interactive", {})
            if interactive.get("type") == "text":
                text = interactive.get("text", {}).get("body", "")
                return bool(text and self.HANDLE_PATTERN.match(text.strip()))
            return False

        # Handle text input
        return bool(handle and self.HANDLE_PATTERN.match(handle.strip()))

    def _transform_handle(self, handle: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Transform and validate handle"""
        if not self.credex_service:
            return {"error": "Service not initialized"}

        # Extract handle from interactive or text
        if isinstance(handle, dict):
            interactive = handle.get("interactive", {})
            if interactive.get("type") == "text":
                handle = interactive.get("text", {}).get("body", "")
            else:
                return {"error": "Invalid handle format"}

        handle = handle.strip()

        # Ensure we have profile data
        if not hasattr(self.credex_service, '_parent_service'):
            return {"error": "Service not properly initialized"}

        user_state = self.credex_service._parent_service.user.state
        if not user_state or not user_state.state:
            return {"error": "State not initialized"}

        current_state = user_state.state
        if not current_state.get("profile"):
            return {"error": "Profile data not found"}

        # Validate handle
        success, response = self.credex_service._member.validate_handle(handle)
        if not success:
            return {"error": response.get("message", "Invalid handle")}

        data = response.get("data", {})
        return {
            "handle": handle,
            "account_id": data.get("accountID"),
            "name": data.get("accountName", handle)
        }

    def _format_amount(self, amount: float, denomination: str) -> str:
        """Format amount based on denomination"""
        if denomination in {"USD", "ZWG", "CAD"}:
            return f"${amount:.2f} {denomination}"
        elif denomination == "XAU":
            return f"{amount:.4f} {denomination}"
        return f"{amount} {denomination}"

    def _update_dashboard(self, response: Dict[str, Any]) -> None:
        """Update dashboard state"""
        try:
            if not hasattr(self.credex_service, '_parent_service'):
                audit.log_flow_event(
                    self.id,
                    "dashboard_update_error",
                    None,
                    self.data,
                    "failure",
                    "Service not properly initialized"
                )
                return

            dashboard = response.get("data", {}).get("dashboard")
            if not dashboard:
                audit.log_flow_event(
                    self.id,
                    "dashboard_update_error",
                    None,
                    self.data,
                    "failure",
                    "No dashboard data in response"
                )
                return

            user_state = self.credex_service._parent_service.user.state
            current_state = user_state.state
            current_profile = current_state.get("profile", {}).copy()

            # Validate state before update
            validation = StateValidator.validate_state(current_state)
            if not validation.is_valid:
                audit.log_flow_event(
                    self.id,
                    "state_validation_error",
                    None,
                    current_state,
                    "failure",
                    validation.error_message
                )
                # Attempt recovery from last valid state
                last_valid = audit.get_last_valid_state(self.id)
                if last_valid:
                    current_state = last_valid
                    current_profile = current_state.get("profile", {}).copy()

            # Update profile with new dashboard data
            current_profile["dashboard"] = dashboard

            # Find personal account in new dashboard data
            accounts = dashboard.get("accounts", [])
            mobile_number = self.data.get("mobile_number")
            personal_account = next(
                (account for account in accounts if account.get("accountType") == "PERSONAL"),
                next(
                    (account for account in accounts if account.get("accountHandle") == mobile_number),
                    current_state.get("current_account")
                )
            )

            # Update state while preserving other critical fields
            new_state = {
                "profile": current_profile,
                "current_account": personal_account,
                "jwt_token": current_state.get("jwt_token")
            }

            # Validate new state before update
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                audit.log_flow_event(
                    self.id,
                    "state_validation_error",
                    None,
                    new_state,
                    "failure",
                    validation.error_message
                )
                return

            # Log state transition
            audit.log_state_transition(
                self.id,
                current_state,
                new_state,
                "success"
            )

            user_state.update_state(new_state, "dashboard_update")

        except Exception as e:
            logger.error(f"Dashboard update error: {str(e)}")

    def complete(self) -> Dict[str, Any]:
        """Complete the flow"""
        try:
            # Validate final state
            validation = StateValidator.validate_flow_state(
                self.data,
                {"mobile_number", "member_id"}
            )
            if not validation.is_valid:
                audit.log_flow_event(
                    self.id,
                    "completion_validation_error",
                    None,
                    self.data,
                    "failure",
                    validation.error_message
                )
                return CredexTemplates.create_error_message(
                    self.data.get("mobile_number"),
                    f"Invalid flow state: {validation.error_message}"
                )

            if not self.credex_service:
                audit.log_flow_event(
                    self.id,
                    "completion_error",
                    None,
                    self.data,
                    "failure",
                    "Service not initialized"
                )
                return CredexTemplates.create_error_message(
                    self.data.get("mobile_number"),
                    "Service not initialized"
                )

            handlers = {
                "offer": self._complete_offer,
                "cancel_credex": self._complete_cancel,
                "accept": lambda: self._complete_action("accept"),
                "decline": lambda: self._complete_action("decline")
            }

            return handlers[self.flow_type]()

        except Exception as e:
            logger.error(f"Flow completion error: {str(e)}")
            return CredexTemplates.create_error_message(
                self.data.get("mobile_number"),
                str(e)
            )

    def _complete_cancel(self) -> Dict[str, Any]:
        """Complete cancel flow"""
        if self.current_step.id != "confirm":
            return self._create_list_message(self.data)

        credex_id = self.data.get("credex_id")
        if not credex_id:
            return CredexTemplates.create_error_message(
                self.data.get("mobile_number"),
                "Missing credex ID"
            )

        success, response = self.credex_service.cancel_credex(credex_id)
        if not success:
            return CredexTemplates.create_error_message(
                self.data.get("mobile_number"),
                response.get("message", "Failed to cancel offer")
            )

        self._update_dashboard(response)
        return self._show_dashboard("Credex successfully cancelled")

    def _complete_offer(self) -> Dict[str, Any]:
        """Complete offer flow"""
        try:
            # Prepare offer data in the format expected by the API
            amount_data = self.data.get("amount_denom", {})
            offer_data = {
                "authorizer_member_id": self.data.get("member_id"),
                "issuerAccountID": self.data.get("account_id"),
                "receiverAccountID": self.data.get("handle", {}).get("account_id"),
                "InitialAmount": amount_data.get("amount", 0),
                "Denomination": amount_data.get("denomination", "USD"),
                "credexType": "PURCHASE",
                "OFFERSorREQUESTS": "OFFERS",
                "securedCredex": True,
                "handle": self.data.get("handle", {}).get("handle"),
                "metadata": {"name": self.data.get("handle", {}).get("name")}
            }

            success, response = self.credex_service.offer_credex(offer_data)

            if not success:
                return CredexTemplates.create_error_message(
                    self.data.get("mobile_number"),
                    response.get("message", "Offer failed")
                )

            self._update_dashboard(response)
            return self._show_dashboard("Credex successfully offered")

        except Exception as e:
            logger.error(f"Error completing offer: {str(e)}")
            return CredexTemplates.create_error_message(
                self.data.get("mobile_number"),
                f"An error occurred: {str(e)}"
            )

    def _complete_action(self, action: str) -> Dict[str, Any]:
        """Complete action flow"""
        credex_id = self.kwargs.get("credex_id")
        if not credex_id:
            return CredexTemplates.create_error_message(
                self.data.get("mobile_number"),
                "Missing credex ID"
            )

        actions = {
            "accept": self.credex_service.accept_credex,
            "decline": self.credex_service.decline_credex
        }

        success, response = actions[action](credex_id)
        if not success:
            return CredexTemplates.create_error_message(
                self.data.get("mobile_number"),
                response.get("message", f"Failed to {action} offer")
            )

        self._update_dashboard(response)
        return self._show_dashboard(f"Successfully {action}ed credex offer")

    def _show_dashboard(self, message: str) -> Dict[str, Any]:
        """Show dashboard with success message"""
        dashboard = DashboardFlow(success_message=message)
        dashboard.credex_service = self.credex_service
        dashboard.data = {"mobile_number": self.data.get("mobile_number")}
        return dashboard.complete()
