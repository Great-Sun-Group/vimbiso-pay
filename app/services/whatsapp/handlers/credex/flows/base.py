"""Base credex flow implementation"""
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Union

from core.messaging.flow import Flow, Step
from core.utils.flow_audit import FlowAuditLogger

from ..templates import CredexTemplates
from ..validator import CredexFlowValidator

audit = FlowAuditLogger()
logger = logging.getLogger(__name__)


class CredexFlow(Flow):
    """Base class for all credex flows"""

    VALID_DENOMINATIONS = {"USD", "ZWG", "XAU", "CAD"}
    AMOUNT_PATTERN = re.compile(r'^(?:([A-Z]{3})\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:\(?([A-Z]{3})\)?)|(\d+(?:\.\d+)?))$')
    HANDLE_PATTERN = re.compile(r'^[a-zA-Z0-9_]+$')

    def __init__(self, flow_type: str = None, state: Dict = None, **kwargs):
        """Initialize flow

        Args:
            flow_type: The type of flow (e.g. 'offer', 'accept', etc.)
            state: Optional state dictionary for flow restoration
            **kwargs: Additional keyword arguments
        """
        # Extract flow type from state if not provided directly
        if flow_type is None and state is not None:
            flow_data = state.get('flow_data', {})
            flow_type = flow_data.get('flow_type')

        if flow_type is None:
            raise ValueError("flow_type must be provided either directly or through state")

        self.flow_type = flow_type
        self.kwargs = kwargs
        self.validator = CredexFlowValidator()
        self.credex_service = None

        # Create steps before parent initialization
        steps = self._create_steps()

        # Initialize parent with flow ID and steps
        super().__init__(f"credex_{flow_type}", steps)

        # Restore state if provided
        if state is not None:
            self.set_state(state)

    def _create_steps(self) -> List[Step]:
        """Create flow steps based on type - to be implemented by subclasses"""
        raise NotImplementedError

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

    def _validate_button_response(self, response: Union[str, Dict[str, Any]]) -> bool:
        """Validate button response"""
        # Log the response for debugging
        logger.debug(f"Validating button response: {response}")

        # Handle string input (already parsed by BotServiceInterface)
        if isinstance(response, str):
            if response != "confirm_action":
                raise ValueError("Please use the confirmation button")
            return True

        # Handle dict input (from BotServiceInterface)
        if isinstance(response, dict):
            # Get message type and body from BotServiceInterface parsing
            msg_type = response.get("type")
            body = response.get("body", "")

            # Handle button press
            if msg_type == "button":
                if body != "confirm_action":
                    raise ValueError("Please use the confirmation button")
                return True

            # Handle text input (for backwards compatibility)
            if msg_type == "text":
                # Check if we're in a flow step
                if self.current_step and self.current_step.id == "confirm":
                    if body.lower() != "confirm_action":
                        raise ValueError("Please use the confirmation button")
                    return True
                raise ValueError("Invalid confirmation format")

        raise ValueError("Invalid confirmation format")

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
            if not ("amount" in amount_data and "denomination" in amount_data):
                raise ValueError("Amount data missing required fields")

            if not isinstance(amount_data["amount"], (int, float)):
                raise ValueError("Amount must be a number")

            if amount_data["denomination"] and amount_data["denomination"] not in self.VALID_DENOMINATIONS:
                raise ValueError(f"Invalid currency. Valid options are: {', '.join(self.VALID_DENOMINATIONS)}")

            return True

        # Handle string input
        if not amount_data:
            raise ValueError("Amount cannot be empty")

        # Try to match the pattern
        amount_str = str(amount_data).strip().upper()
        match = self.AMOUNT_PATTERN.match(amount_str)

        if not match:
            raise ValueError(
                "Invalid amount format. Examples:\n"
                "100     (USD)\n"
                "USD 100\n"
                "ZWG 100\n"
                "XAU 1"
            )

        # Validate denomination
        denom = match.group(1) or match.group(4)
        if denom and denom not in self.VALID_DENOMINATIONS:
            raise ValueError(f"Invalid currency. Valid options are: {', '.join(self.VALID_DENOMINATIONS)}")

        return True

    def _transform_amount(self, amount_str: str) -> Dict[str, Any]:
        """Transform amount string to structured data"""
        match = self.AMOUNT_PATTERN.match(amount_str.strip().upper())

        try:
            # Extract amount and denomination
            if match.group(1):  # Currency first
                denom, amount = match.group(1), match.group(2)
            elif match.group(3):  # Amount first
                amount, denom = match.group(3), match.group(4)
            else:  # Just amount
                amount, denom = match.group(5), None

            # Log transformation at INFO level
            logger.info(f"Transforming amount: {amount} {denom or 'USD'}")

            result = {
                "amount": float(amount),
                "denomination": denom or "USD"
            }

            # Log details at DEBUG level
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Input: {amount_str}")
                logger.debug(f"Parsed: {result}")

            return result

        except Exception as e:
            # Log error with context
            error_context = {
                "input": amount_str,
                "error": str(e),
                "error_type": type(e).__name__
            }
            logger.error("Amount transformation failed", extra=error_context, exc_info=True)
            raise ValueError(f"Failed to transform amount: {str(e)}")

    def _validate_handle(self, handle: Union[str, Dict[str, Any]]) -> bool:
        """Validate handle format"""
        # Handle interactive message
        if isinstance(handle, dict):
            interactive = handle.get("interactive", {})
            if interactive.get("type") == "text":
                text = interactive.get("text", {}).get("body", "")
                if not text:
                    raise ValueError("Handle cannot be empty")
                if not self.HANDLE_PATTERN.match(text.strip()):
                    raise ValueError("Handle can only contain letters, numbers, and underscores")
                return True
            raise ValueError("Invalid handle format")

        # Handle text input
        if not handle:
            raise ValueError("Handle cannot be empty")
        if not self.HANDLE_PATTERN.match(handle.strip()):
            raise ValueError("Handle can only contain letters, numbers, and underscores")
        return True

    def _transform_handle(self, handle: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Transform and validate handle"""
        if not self.credex_service:
            raise ValueError("Service not initialized")

        # Extract handle from interactive or text
        if isinstance(handle, dict):
            interactive = handle.get("interactive", {})
            if interactive.get("type") == "text":
                handle = interactive.get("text", {}).get("body", "")
            else:
                raise ValueError("Invalid handle format")

        handle = handle.strip()

        # Ensure we have profile data
        if not hasattr(self.credex_service, '_parent_service'):
            raise ValueError("Service not properly initialized")

        user_state = self.credex_service._parent_service.user.state
        if not user_state or not user_state.state:
            raise ValueError("State not initialized")

        current_state = user_state.state
        if not current_state.get("profile"):
            raise ValueError("Profile data not found")

        try:
            # Store validation context and current state
            validation_context = {
                "_validation_state": {
                    "step_id": "handle",
                    "input": handle,
                    "timestamp": audit.get_current_timestamp()
                },
                "_validation_context": self.data.get("_validation_context", {})
            }

            # Log validation attempt
            audit.log_validation_event(
                self.id,
                "handle",
                handle,
                True,
                "Attempting API validation"
            )

            # Validate handle through API
            success, response = self.credex_service._member.validate_handle(handle)
            if not success:
                # Log validation failure
                audit.log_validation_event(
                    self.id,
                    "handle",
                    handle,
                    False,
                    response.get("message", "Invalid handle")
                )
                raise ValueError(response.get("message", "Invalid handle"))

            # Get account data
            data = response.get("data", {})
            if not data or not data.get("accountID"):
                raise ValueError("Invalid account data received from API")

            # Create result with validation context
            result = {
                "handle": handle,
                "account_id": data.get("accountID"),
                "name": data.get("accountName", handle),
                **validation_context,
                "_validation_success": True
            }

            # Log successful validation
            audit.log_validation_event(
                self.id,
                "handle",
                handle,
                True,
                "Handle validated successfully"
            )

            return result

        except Exception as e:
            # Log validation error
            audit.log_flow_event(
                self.id,
                "handle_validation_error",
                "handle",
                {"error": str(e), "handle": handle},
                "failure"
            )
            raise ValueError(f"Handle validation failed: {str(e)}")

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

            # Validate state before update
            validation = self.validator.validate_flow_state(current_state)
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

            # Structure profile data properly
            action = response.get("data", {}).get("action", {})
            profile_data = {
                "action": {
                    "id": action.get("id", ""),
                    "type": action.get("type", self.flow_type),
                    "timestamp": datetime.now().isoformat(),
                    "actor": self.data.get("mobile_number", ""),
                    "details": action.get("details", {}),
                    "message": (
                        action.get("message") or  # Try direct message
                        action.get("details", {}).get("message") or  # Try details.message
                        ("CredEx offer created successfully" if action.get("type") == "CREDEX_CREATED" else "")  # Default
                    ),
                    "status": "success" if action.get("type") == "CREDEX_CREATED" else action.get("status", "")
                },
                "dashboard": dashboard
            }

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

            # Build complete state with all required components
            new_state = {
                # Core state fields
                "profile": profile_data,
                "current_account": personal_account,
                "jwt_token": current_state.get("jwt_token"),
                "member_id": current_state.get("member_id"),
                "account_id": current_state.get("account_id"),
                "authenticated": current_state.get("authenticated", True),
                "mobile_number": current_state.get("mobile_number"),

                # Flow data
                "flow_data": {
                    "id": self.id,
                    "step": self.current_index,
                    "data": self.data,
                    "flow_type": self.flow_type,
                    "_previous_data": self._previous_data
                },

                # Validation context
                "_validation_state": current_state.get("_validation_state", {}),
                "_validation_context": current_state.get("_validation_context", {})
            }

            # Preserve any additional validation or context fields
            for key in current_state:
                if key.startswith('_') and key not in new_state:
                    new_state[key] = current_state[key]

            # Validate new state before update
            validation = self.validator.validate_flow_state(new_state)
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
