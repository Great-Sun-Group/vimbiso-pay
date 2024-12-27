"""Member tier upgrade flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from datetime import datetime
from typing import Any, Dict, List

from core.messaging.flow import Flow, Step, StepType
from core.messaging.types import Message
from core.utils.flow_audit import FlowAuditLogger

from ...types import WhatsAppMessage
from .templates import MemberTemplates
from .validator import MemberFlowValidator

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class UpgradeFlow(Flow):
    """Flow for member tier upgrade with strict state management"""

    def __init__(self, flow_type: str = "upgrade", state_manager: Any = None, **kwargs):
        """Initialize upgrade flow with proper state management"""
        if not state_manager:
            raise ValueError("State manager is required")

        # Get required state (already validated by message handler)
        member_id = state_manager.get("member_id")
        account_id = state_manager.get("account_id")
        if not member_id:
            raise ValueError("Member ID required for upgrade")
        if not account_id:
            raise ValueError("Account ID required for upgrade payment")

        self.validator = MemberFlowValidator()
        self.state_manager = state_manager
        self.credex_service = state_manager.get_or_create_credex_service()

        # Create flow ID from member_id
        member_id = state_manager.get("member_id")
        flow_id = f"{flow_type}_{member_id}"

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
        """Create upgrade flow steps"""
        return [
            Step(
                id="confirm",
                type=StepType.BUTTON,
                message=self._create_confirmation_message,
                validator=self._validate_button_response
            )
        ]

    def _validate_button_response(self, response: Dict[str, Any]) -> bool:
        """Validate button response"""
        return (
            response.get("type") == "interactive" and
            response.get("interactive", {}).get("type") == "button_reply" and
            response.get("interactive", {}).get("button_reply", {}).get("id") == "confirm_action"
        )

    def _create_confirmation_message(self, state: Dict[str, Any]) -> Message:
        """Create tier upgrade confirmation message"""
        try:
            # Get required state (already validated)
            channel = self.state_manager.get("channel")
            member_id = self.state_manager.get("member_id")

            return MemberTemplates.create_upgrade_confirmation(
                channel["identifier"],
                member_id
            )
        except ValueError as e:
            return WhatsAppMessage.create_text("unknown", f"Error: {str(e)}")

    def complete(self) -> Message:
        """Complete tier upgrade flow"""
        try:
            # Get required state (already validated)
            channel = self.state_manager.get("channel")
            member_id = self.state_manager.get("member_id")
            account_id = self.state_manager.get("account_id")

            # Create recurring payment
            success, response = self.credex_service.services['recurring'].create_recurring({
                "sourceAccountID": account_id,
                "memberID": member_id,
                "templateType": "MEMBERTIER_SUBSCRIPTION",
                "payFrequency": 28,
                "startDate": datetime.now().strftime("%Y-%m-%d"),
                "memberTier": 3,
                "securedCredex": True,
                "amount": 1.00,
                "denomination": "USD"
            })

            if not success:
                raise ValueError(response.get("message", "Failed to process subscription"))

            return MemberTemplates.create_upgrade_success(
                channel["identifier"],
                member_id
            )

        except ValueError as e:
            logger.error(f"Upgrade failed: {str(e)}")
            return WhatsAppMessage.create_text(
                "unknown",
                f"Upgrade failed: {str(e)}"
            )
