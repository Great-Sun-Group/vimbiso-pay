"""Member tier upgrade flow implementation"""
import logging
from datetime import datetime
from typing import Dict, List, Any

from core.messaging.flow import Flow, Step, StepType
from core.messaging.types import Message
from core.utils.flow_audit import FlowAuditLogger
from .templates import MemberTemplates
from .validator import MemberFlowValidator

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class UpgradeFlow(Flow):
    """Flow for member tier upgrade"""

    def __init__(self, **kwargs):
        self.validator = MemberFlowValidator()
        steps = self._create_steps()
        super().__init__("member_upgrade", steps)
        self.credex_service = None

        # Log flow initialization
        audit.log_flow_event(
            self.id,
            "initialization",
            None,
            {"flow_type": "upgrade", **kwargs},
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
            self.data.get("mobile_number")
        )

    def complete(self) -> Message:
        """Complete tier upgrade flow"""
        try:
            account_id = self.data.get("account_id")
            if not account_id:
                raise ValueError("Missing account ID")

            # Log upgrade attempt
            audit.log_flow_event(
                self.id,
                "upgrade_attempt",
                None,
                {"account_id": account_id},
                "in_progress"
            )

            # Create recurring payment
            success, response = self.credex_service._recurring.create_recurring({
                "sourceAccountID": account_id,
                "templateType": "MEMBERTIER_SUBSCRIPTION",
                "payFrequency": 28,
                "startDate": datetime.now().strftime("%Y-%m-%d"),
                "memberTier": 3,
                "securedCredex": True,
                "amount": 1.00,
                "denomination": "USD"
            })

            if not success:
                audit.log_flow_event(
                    self.id,
                    "upgrade_error",
                    None,
                    response,
                    "failure",
                    response.get("message", "Failed to process subscription")
                )
                raise ValueError(response.get("message", "Failed to process subscription"))

            audit.log_flow_event(
                self.id,
                "upgrade_complete",
                None,
                response,
                "success"
            )

            return MemberTemplates.create_upgrade_success(
                self.data.get("mobile_number")
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
