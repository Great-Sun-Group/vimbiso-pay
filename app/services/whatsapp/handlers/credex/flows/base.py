"""Base credex flow implementation"""
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Union, Optional

from core.messaging.flow import Flow, Step, FlowState, StepType
from core.utils.flow_audit import FlowAuditLogger
from services.whatsapp.state_manager import StateManager

from ..templates import CredexTemplates
from ..validator import CredexFlowValidator

audit = FlowAuditLogger()
logger = logging.getLogger(__name__)


class CredexFlow(Flow):
    """Base class for all credex flows"""

    VALID_DENOMINATIONS = {"USD", "ZWG", "XAU", "CAD"}
    AMOUNT_PATTERN = re.compile(r'^(?:([A-Z]{3})\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:\(?([A-Z]{3})\)?)|(\d+(?:\.\d+)?))$')
    HANDLE_PATTERN = re.compile(r'^[a-zA-Z0-9_]+$')

    def __init__(self, id: str, steps: Optional[List[Step]] = None, flow_type: str = None, state: Optional['FlowState'] = None):
        """Initialize flow with proper state management

        Args:
            id: Flow identifier
            steps: Optional list of steps (None to create through _create_steps)
            flow_type: Type of flow (e.g. 'offer', 'accept')
            state: Optional FlowState object

        Note:
            All required data is accessed from state through _get_service_state()
            Steps are created through _create_steps after service initialization
        """
        # Initialize core attributes
        self.validator = CredexFlowValidator()
        self.credex_service = None
        self.flow_type = flow_type or (state.data.get("flow_data", {}).get("data", {}).get("flow_type") if state else None)

        if not self.flow_type:
            raise ValueError("Flow type is required")

        # Validate state structure and required fields
        if not state:
            raise ValueError("State is required for CredexFlow")

        if not state.member_id:
            raise ValueError("State missing member_id")

        if not isinstance(state.data, dict):
            raise ValueError("State data must be dictionary")

        # Channel info will be retrieved from service state when needed

        # Initialize base class with empty steps - they'll be created after service init
        super().__init__(id=id, steps=[], state=state)

        # Log initialization with proper context
        logger.debug(f"Initialized {self.__class__.__name__}:")
        logger.debug(f"- Flow type: {self.flow_type}")
        logger.debug(f"- Flow ID: {self.id}")
        logger.debug(f"- Member ID: {self.member_id}")  # From state

    def _validate_service(self) -> None:
        """Validate service has required capabilities"""
        if not self.credex_service:
            raise ValueError("Service not initialized")

        if not hasattr(self.credex_service, 'services'):
            raise ValueError("Service missing required services")

        required_services = {'member', 'offers'}
        missing = required_services - set(self.credex_service.services.keys())
        if missing:
            raise ValueError(f"Service missing required capabilities: {', '.join(missing)}")

    def _create_steps(self) -> List[Step]:
        """Create flow steps after service initialization

        Note:
            This is called by Flow base class after service is initialized
            All steps must have access to properly initialized service
        """
        # Validate service has required capabilities
        self._validate_service()

        # Create steps with access to initialized service
        steps = [
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
                message=self._get_handle_prompt,
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

        # Log step creation
        logger.debug(f"Created steps: {[step.id for step in steps]}")

        return steps

    def _get_service_state(self) -> Dict[str, Any]:
        """Get current state from service"""
        # Validate service has required capabilities
        self._validate_service()

        state = self.credex_service.state_manager.state
        if not state:
            raise ValueError("State not initialized")

        # Validate critical state fields
        if not state.get("member_id"):
            raise ValueError("State missing member_id")
        if not state.get("channel", {}).get("identifier"):
            raise ValueError("State missing channel identifier")

        return state

    def process_input(self, input_data: Any) -> Optional[Dict[str, Any]]:
        """Override to handle WhatsApp messaging"""
        try:
            return super().process_input(input_data)
        except ValueError as e:
            # Get channel info from service state
            service_state = self._get_service_state()
            channel_id = service_state["channel"]["identifier"]

            # Create error message
            from services.whatsapp.types import WhatsAppMessage
            if str(e) == "Invalid input" and self.current_step and self.current_step.id == "amount":
                return WhatsAppMessage.create_text(
                    channel_id,
                    "Invalid amount format. Examples:\n"
                    "100     (USD)\n"
                    "USD 100\n"
                    "ZWG 100\n"
                    "XAU 1\n\n"
                    "Please ensure you enter a valid number with an optional currency code."
                )
            return WhatsAppMessage.create_text(channel_id, str(e))

    def _get_channel_identifier(self) -> str:
        """Get channel identifier from service state using StateManager"""
        state = self._get_service_state()
        return StateManager.get_channel_identifier(state)

    def _get_amount_prompt(self, _) -> Dict[str, Any]:
        """Get amount prompt message"""
        # Get service state - SINGLE SOURCE OF TRUTH
        service_state = self._get_service_state()
        if not service_state.get("member_id"):
            raise ValueError("Missing member_id in service state")

        return CredexTemplates.create_amount_prompt(
            self._get_channel_identifier(),
            service_state  # Pass top level state containing member_id
        )

    def _get_handle_prompt(self, _) -> Dict[str, Any]:
        """Get handle prompt message"""
        if not self.credex_service:
            raise ValueError("Service not initialized")
        return CredexTemplates.create_handle_prompt(
            self._get_channel_identifier(),
            self.credex_service.state_manager  # Pass state manager - SINGLE SOURCE OF TRUTH
        )

    def _create_list_message(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create list selection message"""
        if not self.credex_service:
            raise ValueError("Service not initialized")
        return CredexTemplates.create_pending_offers_list(
            self._get_channel_identifier(),
            self.data,
            self.credex_service.state_manager  # Pass state manager - SINGLE SOURCE OF TRUTH
        )

    def _create_confirmation_message(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create confirmation message based on flow type"""
        messages = {
            "offer": self._create_offer_confirmation,
            "cancel": self._create_cancel_confirmation,
            "accept": lambda s: self._create_action_confirmation(s, "Accept"),
            "decline": lambda s: self._create_action_confirmation(s, "Decline")
        }

        return messages[self.flow_type](state)

    def _create_offer_confirmation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create offer confirmation message"""
        if not self.credex_service:
            raise ValueError("Service not initialized")

        amount_data = state.get("amount_denom", {})
        amount = self._format_amount(
            amount_data.get("amount", 0),
            amount_data.get("denomination", "USD")
        )
        handle = state["handle"]["handle"]
        name = state["handle"]["name"]

        return CredexTemplates.create_offer_confirmation(
            self._get_channel_identifier(),
            amount,
            handle,
            name,
            self.credex_service.state_manager  # Pass state manager - SINGLE SOURCE OF TRUTH
        )

    def _create_cancel_confirmation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create cancel confirmation message"""
        if not self.credex_service:
            raise ValueError("Service not initialized")

        amount = state.get("amount", "0")
        counterparty = state.get("counterparty", "Unknown")

        return CredexTemplates.create_cancel_confirmation(
            self._get_channel_identifier(),
            amount,
            counterparty,
            self.credex_service.state_manager  # Pass state manager - SINGLE SOURCE OF TRUTH
        )

    def _create_action_confirmation(self, state: Dict[str, Any], action: str) -> Dict[str, Any]:
        """Create action confirmation message"""
        if not self.credex_service:
            raise ValueError("Service not initialized")

        amount = self._format_amount(
            float(state.get("amount", "0.00")),
            state.get("denomination", "USD")
        )
        counterparty = state.get("counterparty", "Unknown")

        return CredexTemplates.create_action_confirmation(
            self._get_channel_identifier(),
            amount,
            counterparty,
            action,
            self.credex_service.state_manager  # Pass state manager - SINGLE SOURCE OF TRUTH
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
        match = self.AMOUNT_PATTERN.match(str(amount_str).strip().upper())
        if not match:
            raise ValueError("Invalid amount format")

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

            # Validate amount is a positive number
            amount_float = float(amount)
            if amount_float <= 0:
                raise ValueError("Amount must be greater than 0")

            result = {
                "amount": amount_float,
                "denomination": denom or "USD"
            }

            # Log successful transformation
            audit.log_validation_event(
                self.id,
                "amount",
                amount_str,
                True,
                None
            )

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
        # Extract handle from interactive or text
        if isinstance(handle, dict):
            interactive = handle.get("interactive", {})
            if interactive.get("type") == "text":
                handle = interactive.get("text", {}).get("body", "")
            else:
                raise ValueError("Invalid handle format")

        handle = handle.strip()

        # Validate flow state - SINGLE SOURCE OF TRUTH
        if not self.state or not self.state.member_id:
            raise ValueError("Missing member ID in flow state")

        try:
            # Store validation context
            validation_context = {
                "_validation_state": {
                    "step_id": "handle",
                    "input": handle,
                    "timestamp": audit.get_current_timestamp()
                },
                "_validation_context": self.data.get("_validation_context", {})
            }

            # Validate handle through API
            success, response = self.credex_service.services['member'].validate_handle(handle)
            if not success:
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
            # Get current state and validate dashboard data
            current_state = self._get_service_state()
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

            # Get member ID from flow state - SINGLE SOURCE OF TRUTH
            if not self.state or not self.state.member_id:
                raise ValueError("Missing member ID in flow state")

            # Get channel ID from state
            channel_id = StateManager.get_channel_identifier(current_state)
            if not channel_id:
                raise ValueError("Missing channel identifier")

            # Structure profile data
            action = response.get("data", {}).get("action", {})
            profile_data = {
                "action": {
                    "id": action.get("id", ""),
                    "type": action.get("type"),
                    "timestamp": datetime.now().isoformat(),
                    "actor": self.state.member_id,  # From flow state
                    "details": action.get("details", {}),
                    "message": (
                        action.get("message") or
                        action.get("details", {}).get("message") or
                        ("CredEx offer created successfully" if action.get("type") == "CREDEX_CREATED" else "")
                    ),
                    "status": "success" if action.get("type") == "CREDEX_CREATED" else action.get("status", "")
                },
                "dashboard": dashboard
            }

            # Find personal account
            accounts = dashboard.get("accounts", [])
            personal_account = next(
                (account for account in accounts if account.get("accountType") == "PERSONAL"),
                next(
                    (account for account in accounts if account.get("accountHandle") == channel_id),
                    current_state.get("current_account")
                )
            )

            # Build new state following SINGLE SOURCE OF TRUTH
            new_state = {
                "member_id": self.state.member_id,  # From flow state - SINGLE SOURCE OF TRUTH
                "channel": StateManager.prepare_state_update(
                    current_state={},
                    channel_identifier=channel_id
                )["channel"],  # SINGLE SOURCE OF TRUTH
                "authenticated": current_state.get("authenticated", True),
                "jwt_token": current_state.get("jwt_token"),  # SINGLE SOURCE OF TRUTH
                "account_id": current_state.get("account_id"),
                "current_account": personal_account,
                "profile": profile_data,
                "flow_data": {
                    "id": self.id,
                    "step": self.current_index,
                    "data": self.data,
                    "_previous_data": self._previous_data
                },
                "_validation_context": current_state.get("_validation_context", {}),
                "_validation_state": current_state.get("_validation_state", {}),
                "_last_updated": audit.get_current_timestamp()
            }

            # Preserve additional fields
            for key in current_state:
                if key.startswith('_') and key not in new_state:
                    new_state[key] = current_state[key]

            # Update state
            self.credex_service.state_manager.update_state(new_state)

            # Log success
            audit.log_state_transition(
                self.id,
                current_state,
                new_state,
                "success"
            )

        except Exception as e:
            logger.error(f"Dashboard update error: {str(e)}")
