"""Member tier upgrade flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from datetime import datetime
from typing import Any, Dict

from core.messaging.types import Message
from core.utils.exceptions import StateException
from core.utils.flow_audit import FlowAuditLogger

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
        # Get required data (StateManager validates)
        channel = state_manager.get("channel")
        member_id = state_manager.get("member_id")

        return MemberTemplates.create_upgrade_confirmation(
            channel["identifier"],
            member_id
        )
    except StateException as e:
        logger.error(f"Upgrade confirmation error: {str(e)}")
        raise


def handle_upgrade_completion(state_manager: Any, credex_service: Any) -> Message:
    """Complete tier upgrade flow enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get required data (StateManager validates)
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
            raise StateException(response.get("message", "Failed to process subscription"))

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

        # Transition to dashboard with success message
        success, error = state_manager.update_state({
            "flow_data": {
                "data": {
                    "message": "✅ Upgrade successful! Welcome to your new tier.",
                    "subscription_id": response.get("subscriptionId"),
                    "tier": 3,
                    "timestamp": datetime.now().isoformat()
                }
            }
        })
        if not success:
            raise StateException(f"Failed to transition flow: {error}")

        # Let dashboard handler show success message
        from ..member.dashboard import handle_dashboard_display
        return handle_dashboard_display(state_manager)

    except StateException as e:
        logger.error(f"Upgrade failed: {str(e)}")
        raise


def process_upgrade_step(state_manager: Any, step: str, input_data: Any = None) -> Message:
    """Process upgrade step enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get required data (StateManager validates)
        flow_data = state_manager.get("flow_data")

        # Handle confirmation step
        if step == "confirm":
            if input_data:
                if not validate_button_response(input_data):
                    raise StateException("Invalid confirmation response")
                success, error = state_manager.update_state({
                    "flow_data": {
                        **flow_data,
                        "confirmed": True,
                        "current_step": "complete"
                    }
                })
                if not success:
                    raise StateException(f"Failed to update flow data: {error}")
            return handle_upgrade_confirmation(state_manager)

        else:
            raise StateException(f"Invalid upgrade step: {step}")

    except StateException as e:
        logger.error(f"Upgrade step error: {str(e)}")
        raise
