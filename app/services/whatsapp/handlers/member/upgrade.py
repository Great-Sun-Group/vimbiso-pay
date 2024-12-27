"""Member tier upgrade flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from datetime import datetime
from typing import Any, Dict

from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator
from core.messaging.types import Message
from ...types import WhatsAppMessage
from .templates import MemberTemplates

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


def validate_button_response(response: Dict[str, Any]) -> bool:
    """Validate button response"""
    return (
        response.get("type") == "interactive" and
        response.get("interactive", {}).get("type") == "button_reply" and
        response.get("interactive", {}).get("button_reply", {}).get("id") == "confirm_action"
    )


def handle_upgrade_confirmation(state_manager: Any) -> Message:
    """Create tier upgrade confirmation message enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {
                "channel": state_manager.get("channel"),
                "member_id": state_manager.get("member_id")
            },
            {"channel", "member_id"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # Get required data
        channel = state_manager.get("channel")
        member_id = state_manager.get("member_id")

        return MemberTemplates.create_upgrade_confirmation(
            channel["identifier"],
            member_id
        )
    except ValueError as e:
        return WhatsAppMessage.create_text("unknown", f"Error: {str(e)}")


def handle_upgrade_completion(state_manager: Any, credex_service: Any) -> Message:
    """Complete tier upgrade flow enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {
                "channel": state_manager.get("channel"),
                "member_id": state_manager.get("member_id"),
                "account_id": state_manager.get("account_id")
            },
            {"channel", "member_id", "account_id"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # Get required data
        channel = state_manager.get("channel")
        member_id = state_manager.get("member_id")
        account_id = state_manager.get("account_id")

        # Create recurring payment
        success, response = credex_service['create_recurring']({
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

        # Log success
        audit.log_flow_event(
            f"upgrade_{member_id}",
            "complete",
            None,
            {
                "channel_id": channel["identifier"],
                "member_id": member_id,
                "account_id": account_id
            },
            "success"
        )

        # Clear flow data using proper method
        success, error = state_manager.update_state({"flow_data": None})
        if not success:
            raise ValueError(f"Failed to clear flow data: {error}")

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


def process_upgrade_step(state_manager: Any, step: str, input_data: Any = None) -> Message:
    """Process upgrade step enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {
                "channel": state_manager.get("channel"),
                "member_id": state_manager.get("member_id"),
                "account_id": state_manager.get("account_id"),
                "flow_data": state_manager.get("flow_data")
            },
            {"channel", "member_id", "account_id", "flow_data"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # Handle confirmation step
        if step == "confirm":
            if input_data:
                if not validate_button_response(input_data):
                    raise ValueError("Invalid confirmation response")
                success, error = state_manager.update_state({
                    "flow_data": {
                        **state_manager.get("flow_data", {}),
                        "confirmed": True,
                        "current_step": "complete"
                    }
                })
                if not success:
                    raise ValueError(f"Failed to update flow data: {error}")
            return handle_upgrade_confirmation(state_manager)

        else:
            raise ValueError(f"Invalid upgrade step: {step}")

    except ValueError as e:
        return WhatsAppMessage.create_text(
            state_manager.get("channel", {}).get("identifier", "unknown"),
            f"Error: {str(e)}"
        )
