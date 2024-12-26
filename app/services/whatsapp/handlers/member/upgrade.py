"""Member tier upgrade flow implementation"""
import logging
from datetime import datetime
from typing import Dict, List, Any

from core.messaging.flow import Flow, Step, StepType
from core.messaging.types import Message
from core.utils.flow_audit import FlowAuditLogger
from ...state_manager import StateManager
from .templates import MemberTemplates
from .validator import MemberFlowValidator

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class UpgradeFlow(Flow):
    """Flow for member tier upgrade"""

    def __init__(self, flow_type: str = "upgrade", state: Dict = None, **kwargs):
        """Initialize upgrade flow with proper state management"""
        self.validator = MemberFlowValidator()
        self.credex_service = None

        # Initialize base state if none provided
        if state is None:
            state = {}

        # Get member ID and channel info from top level - SINGLE SOURCE OF TRUTH
        member_id = state.get("member_id")
        if not member_id:
            raise ValueError("Missing member ID")

        channel_id = StateManager.get_channel_identifier(state)
        if not channel_id:
            raise ValueError("Missing channel identifier")

        # Create flow ID from type and member ID
        flow_id = f"{flow_type}_{member_id}"

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
        """Create upgrade flow steps"""
        return [
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

    def _create_confirmation_message(self, _: Dict[str, Any]) -> Message:
        """Create tier upgrade confirmation message"""
        return MemberTemplates.create_upgrade_confirmation(
            self._get_channel_identifier()
        )

    def complete(self) -> Message:
        """Complete tier upgrade flow"""
        try:
            # Get required data
            account_id = self.data.get("account_id")
            if not account_id:
                raise ValueError("Missing account ID")

            # Get member_id from top level state - SINGLE SOURCE OF TRUTH
            current_state = self.credex_service._parent_service.user.state.state
            member_id = current_state.get("member_id")
            if not member_id:
                raise ValueError("Missing member ID in state")

            channel_id = self._get_channel_identifier()
            if not channel_id:
                raise ValueError("Missing channel identifier")

            # Log upgrade attempt with member and channel context
            audit_context = {
                "member_id": member_id,
                "account_id": account_id,
                "channel": {
                    "type": "whatsapp",
                    "identifier": channel_id
                }
            }
            audit.log_flow_event(
                self.id,
                "upgrade_attempt",
                None,
                audit_context,
                "in_progress"
            )

            # Create recurring payment with member context
            success, response = self.credex_service.services['recurring'].create_recurring({
                "sourceAccountID": account_id,
                "memberID": member_id,  # Include member ID
                "templateType": "MEMBERTIER_SUBSCRIPTION",
                "payFrequency": 28,
                "startDate": datetime.now().strftime("%Y-%m-%d"),
                "memberTier": 3,
                "securedCredex": True,
                "amount": 1.00,
                "denomination": "USD",
                "channel": {  # Include channel info
                    "type": "whatsapp",
                    "identifier": channel_id
                }
            })

            if not success:
                audit.log_flow_event(
                    self.id,
                    "upgrade_error",
                    None,
                    {**audit_context, "response": response},
                    "failure",
                    response.get("message", "Failed to process subscription")
                )
                raise ValueError(response.get("message", "Failed to process subscription"))

            audit.log_flow_event(
                self.id,
                "upgrade_complete",
                None,
                {**audit_context, "response": response},
                "success"
            )

            return MemberTemplates.create_upgrade_success(
                channel_id  # Use channel identifier
            )

        except Exception as e:
            logger.error(f"Upgrade error: {str(e)}")
            audit.log_flow_event(
                self.id,
                "upgrade_error",
                None,
                self.data,
                "failure",
                str(e)
            )
            raise
