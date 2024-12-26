"""Member registration flow implementation"""
import logging
from typing import Dict, List, Any

from core.messaging.flow import Flow, Step, StepType
from core.messaging.types import Message
from core.utils.flow_audit import FlowAuditLogger
from ...state_manager import StateManager
from .templates import MemberTemplates
from .validator import MemberFlowValidator

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class RegistrationFlow(Flow):
    """Flow for member registration"""

    def __init__(self, flow_type: str = "registration", state: Dict = None, **kwargs):
        """Initialize registration flow with proper state management"""
        self.validator = MemberFlowValidator()
        self.credex_service = None

        # Initialize base state if none provided
        if state is None:
            state = {}

        # Get member ID and channel info from top level - SINGLE SOURCE OF TRUTH
        member_id = state.get("member_id")
        channel_id = StateManager.get_channel_identifier(state)

        # Create flow ID from type and member ID
        flow_id = f"{flow_type}_{member_id}" if member_id else "registration"

        # Create steps before initializing base class
        steps = self._create_steps()

        # Initialize base Flow class with required arguments
        super().__init__(id=flow_id, steps=steps)

        # Log initialization with member context
        audit.log_flow_event(
            self.id,
            "initialization",
            None,
            {
                "flow_type": flow_type,
                "member_id": member_id,
                "channel": {
                    "type": "whatsapp",
                    "identifier": channel_id
                },
                **kwargs
            },
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

    def _get_channel_identifier(self) -> str:
        """Get channel identifier from state using StateManager"""
        if not hasattr(self.credex_service, '_parent_service'):
            raise ValueError("Service not properly initialized")
        current_state = self.credex_service._parent_service.user.state.state or {}
        return StateManager.get_channel_identifier(current_state)

    def _get_first_name_prompt(self, _) -> Message:
        """Get first name prompt"""
        return MemberTemplates.create_first_name_prompt(
            self._get_channel_identifier()
        )

    def _get_last_name_prompt(self, _) -> Message:
        """Get last name prompt"""
        return MemberTemplates.create_last_name_prompt(
            self._get_channel_identifier()
        )

    def _validate_name(self, name: str) -> bool:
        """Validate name input"""
        try:
            if not name:
                return False
            name = name.strip()
            is_valid = (
                3 <= len(name) <= 50 and
                name.replace(" ", "").isalpha()
            )

            audit.log_validation_event(
                self.id,
                self.current_step.id,
                name,
                is_valid,
                None if is_valid else "Invalid name format"
            )
            return is_valid

        except Exception as e:
            audit.log_validation_event(
                self.id,
                self.current_step.id,
                name,
                False,
                str(e)
            )
            return False

    def _validate_button_response(self, response: Dict[str, Any]) -> bool:
        """Validate button response"""
        try:
            is_valid = (
                response.get("type") == "interactive" and
                response.get("interactive", {}).get("type") == "button_reply" and
                response.get("interactive", {}).get("button_reply", {}).get("id") == "confirm_action"
            )

            audit.log_validation_event(
                self.id,
                self.current_step.id,
                response,
                is_valid,
                None if is_valid else "Invalid button response"
            )
            return is_valid

        except Exception as e:
            audit.log_validation_event(
                self.id,
                self.current_step.id,
                response,
                False,
                str(e)
            )
            return False

    def _create_confirmation_message(self, state: Dict[str, Any]) -> Message:
        """Create registration confirmation message"""
        first_name = state["first_name"]["first_name"]
        last_name = state["last_name"]["last_name"]

        return MemberTemplates.create_registration_confirmation(
            recipient=self._get_channel_identifier(),
            first_name=first_name,
            last_name=last_name
        )

    def complete(self) -> Message:
        """Complete registration flow"""
        try:
            # Get registration data
            first_name = self.data["first_name"]["first_name"]
            last_name = self.data["last_name"]["last_name"]
            channel_id = self._get_channel_identifier()

            if not channel_id:
                raise ValueError("Missing channel identifier")

            # Log registration attempt with channel info
            audit_context = {
                "first_name": first_name,
                "last_name": last_name,
                "channel": {
                    "type": "whatsapp",
                    "identifier": channel_id
                }
            }
            audit.log_flow_event(
                self.id,
                "registration_attempt",
                None,
                audit_context,
                "in_progress"
            )

            # Register member using channel identifier
            # Register member with channel identifier
            member_data = {
                "firstname": first_name,
                "lastname": last_name,
                "defaultDenom": "USD"
            }
            success, response = self.credex_service.services['auth'].register_member(
                member_data,
                channel_id  # Pass channel identifier separately
            )

            if not success:
                audit.log_flow_event(
                    self.id,
                    "registration_error",
                    None,
                    response,
                    "failure",
                    response.get("message", "Registration failed")
                )
                raise ValueError(response.get("message", "Registration failed"))

            # Store JWT token
            if token := (
                response.get("data", {})
                .get("action", {})
                .get("details", {})
                .get("token")
            ):
                if hasattr(self.credex_service, '_parent_service'):
                    # Get member ID from response
                    member_id = (
                        response.get("data", {})
                        .get("action", {})
                        .get("details", {})
                        .get("memberID")
                    )

                    # Prepare member-centric state
                    new_state = {
                        # Core identity
                        "member_id": member_id,  # Primary identifier

                        # Channel information - use prepare_state_update to get channel data
                        "channel": StateManager.prepare_state_update(
                            current_state={},
                            channel_identifier=channel_id
                        )["channel"],

                        # Authentication
                        "jwt_token": token,
                        "authenticated": True,

                        # Metadata
                        "_last_updated": audit.get_current_timestamp()
                    }

                    # Validate auth state
                    validation = self.validator.validate_flow_state(new_state)
                    if validation.is_valid:
                        self.credex_service._parent_service.user.state.update_state(
                            new_state
                        )

            audit.log_flow_event(
                self.id,
                "registration_complete",
                None,
                response,
                "success"
            )

            return MemberTemplates.create_registration_success(
                channel_id,  # Use channel identifier
                first_name
            )

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            audit.log_flow_event(
                self.id,
                "registration_error",
                None,
                self.data,
                "failure",
                str(e)
            )
            raise
