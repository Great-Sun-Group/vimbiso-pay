"""Member registration flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, List

from core.messaging.flow import Flow, Step, StepType
from core.messaging.types import Message
from core.utils.flow_audit import FlowAuditLogger

from ...types import WhatsAppMessage
from .templates import MemberTemplates
from .validator import MemberFlowValidator

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class RegistrationFlow(Flow):
    """Flow for member registration with strict state management"""

    def __init__(self, flow_type: str = "registration", state_manager: Any = None, **kwargs):
        """Initialize registration flow with proper state management"""
        if not state_manager:
            raise ValueError("State manager is required")

        # Get channel (already validated at service boundary)
        channel = state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            raise ValueError("Channel identifier required for registration")

        self.validator = MemberFlowValidator()
        self.state_manager = state_manager
        self.credex_service = state_manager.get_or_create_credex_service()

        # Create flow ID from channel (not member_id)
        channel = state_manager.get("channel")
        flow_id = f"{flow_type}_{channel.get('identifier', 'unknown')}"

        # Create steps before initializing base class
        steps = self._create_steps()

        # Initialize base Flow class with required arguments
        super().__init__(id=flow_id, steps=steps)

        # Log initialization
        audit.log_flow_event(
            self.id,
            "initialization",
            None,
            {"flow_type": flow_type},
            "success"
        )

    def _create_steps(self) -> List[Step]:
        """Create registration flow steps"""
        return [
            Step(
                id="first_name",
                type=StepType.TEXT,
                message=self._get_first_name_prompt,
                validator=self._validate_name,
                transformer=lambda value: {"first_name": value.strip()}
            ),
            Step(
                id="last_name",
                type=StepType.TEXT,
                message=self._get_last_name_prompt,
                validator=self._validate_name,
                transformer=lambda value: {"last_name": value.strip()}
            ),
            Step(
                id="confirm",
                type=StepType.BUTTON,
                message=self._create_confirmation_message,
                validator=self._validate_button_response
            )
        ]

    def _get_first_name_prompt(self, state: Dict[str, Any]) -> Message:
        """Get first name prompt"""
        try:
            # Get channel (already validated)
            channel = self.state_manager.get("channel")
            return MemberTemplates.create_first_name_prompt(channel["identifier"])
        except ValueError as e:
            return WhatsAppMessage.create_text("unknown", f"Error: {str(e)}")

    def _get_last_name_prompt(self, state: Dict[str, Any]) -> Message:
        """Get last name prompt"""
        try:
            # Get channel (already validated)
            channel = self.state_manager.get("channel")
            return MemberTemplates.create_last_name_prompt(channel["identifier"])
        except ValueError as e:
            return WhatsAppMessage.create_text("unknown", f"Error: {str(e)}")

    def _validate_name(self, name: str) -> bool:
        """Validate name input"""
        if not name:
            return False
        name = name.strip()
        return (
            3 <= len(name) <= 50 and
            name.replace(" ", "").isalpha()
        )

    def _validate_button_response(self, response: Dict[str, Any]) -> bool:
        """Validate button response"""
        return (
            response.get("type") == "interactive" and
            response.get("interactive", {}).get("type") == "button_reply" and
            response.get("interactive", {}).get("button_reply", {}).get("id") == "confirm_action"
        )

    def _create_confirmation_message(self, state: Dict[str, Any]) -> Message:
        """Create registration confirmation message"""
        try:
            # Get required data (validation handled by flow steps)
            channel = self.state_manager.get("channel")
            if not state.get("first_name") or not state.get("last_name"):
                raise ValueError("Name data required for confirmation")

            first_name = state["first_name"]["first_name"]
            last_name = state["last_name"]["last_name"]

            return MemberTemplates.create_registration_confirmation(
                channel["identifier"],
                first_name,
                last_name
            )
        except ValueError as e:
            return WhatsAppMessage.create_text("unknown", f"Error: {str(e)}")

    def complete(self) -> Message:
        """Complete registration flow"""
        try:
            # Get required data (validation handled by state manager)
            channel = self.state_manager.get("channel")
            first_name_data = self.state_manager.get("first_name")
            last_name_data = self.state_manager.get("last_name")

            if not first_name_data or not last_name_data:
                raise ValueError("Name data required for registration")

            first_name = first_name_data["first_name"]
            last_name = last_name_data["last_name"]

            # Register member
            member_data = {
                "firstname": first_name,
                "lastname": last_name,
                "defaultDenom": "USD"
            }
            success, response = self.credex_service.services['auth'].register_member(
                member_data,
                channel["identifier"]
            )

            if not success:
                raise ValueError(response.get("message", "Registration failed"))

            # Update state with new member info
            token = response.get("data.action.details.token")
            member_id = response.get("data.action.details.memberID")
            if token and member_id:
                new_state = {
                    "member_id": member_id,
                    "jwt_token": token,
                    "authenticated": True,
                    "_last_updated": audit.get_current_timestamp()
                }
                # Update through state manager (validation handled by manager)
                success, error = self.state_manager.update_state(new_state)
                if not success:
                    raise ValueError(f"Failed to update state: {error}")

            return MemberTemplates.create_registration_success(
                channel["identifier"],
                first_name,
                member_id
            )

        except ValueError as e:
            logger.error(f"Registration failed: {str(e)}")
            return WhatsAppMessage.create_text(
                "unknown",
                f"Registration failed: {str(e)}"
            )
