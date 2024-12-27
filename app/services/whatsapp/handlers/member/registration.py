"""Member registration flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.messaging.types import Message
from core.utils.exceptions import StateException
from core.utils.flow_audit import FlowAuditLogger

from .templates import MemberTemplates

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


def validate_name(name: str) -> bool:
    """Validate name input"""
    if not name:
        return False
    name = name.strip()
    return (
        3 <= len(name) <= 50 and
        name.replace(" ", "").isalpha()
    )


def validate_button_response(response: Dict[str, Any]) -> bool:
    """Validate button response"""
    return (
        response.get("type") == "interactive" and
        response.get("interactive", {}).get("type") == "button_reply" and
        response.get("interactive", {}).get("button_reply", {}).get("id") == "confirm_action"
    )


def handle_first_name_prompt(state_manager: Any) -> Message:
    """Get first name prompt enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get channel (StateManager validates)
        channel = state_manager.get("channel")
        return MemberTemplates.create_first_name_prompt(channel["identifier"])
    except StateException as e:
        logger.error(f"First name prompt error: {str(e)}")
        raise


def handle_last_name_prompt(state_manager: Any) -> Message:
    """Get last name prompt enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get channel (StateManager validates)
        channel = state_manager.get("channel")
        return MemberTemplates.create_last_name_prompt(channel["identifier"])
    except StateException as e:
        logger.error(f"Last name prompt error: {str(e)}")
        raise


def handle_confirmation(state_manager: Any) -> Message:
    """Create registration confirmation message enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get required data (StateManager validates)
        channel = state_manager.get("channel")
        flow_data = state_manager.get("flow_data")

        return MemberTemplates.create_registration_confirmation(
            channel["identifier"],
            flow_data["first_name"],
            flow_data["last_name"]
        )
    except StateException as e:
        logger.error(f"Confirmation error: {str(e)}")
        raise


def handle_registration_completion(state_manager: Any, credex_service: Any) -> Message:
    """Complete registration flow enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get required data (StateManager validates)
        channel = state_manager.get("channel")
        flow_data = state_manager.get("flow_data")

        # Register member
        member_data = {
            "firstname": flow_data["first_name"],
            "lastname": flow_data["last_name"],
            "defaultDenom": "USD"
        }
        success, response = credex_service['register_member'](
            member_data,
            channel["identifier"]
        )

        if not success:
            raise StateException(response.get("message", "Registration failed"))

        # Get registration data
        action_details = response.get("data", {}).get("action", {}).get("details", {})
        token = action_details.get("token")
        member_id = action_details.get("memberID")

        # Update state
        success, error = state_manager.update_state({
            "member_id": member_id,
            "jwt_token": token,
            "authenticated": True,
            "flow_data": {
                "flow_type": "dashboard",
                "step": 0,
                "current_step": "display",
                "data": {
                    "message": "✅ Registration successful! Welcome to Vimbiso."
                }
            }
        })
        if not success:
            raise StateException(f"Failed to update state: {error}")

        # Log success
        audit.log_flow_event(
            "registration",
            "complete",
            None,
            {
                "channel_id": channel["identifier"],
                "member_id": member_id
            },
            "success"
        )

        # Let dashboard handler show success message
        from ..member.dashboard import handle_dashboard_display
        return handle_dashboard_display(state_manager)

    except StateException as e:
        logger.error(f"Registration failed: {str(e)}")
        raise


def process_registration_step(state_manager: Any, step: str, input_data: Any = None) -> Message:
    """Process registration step enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get required data (StateManager validates)
        flow_data = state_manager.get("flow_data")

        # Handle each step
        if step == "first_name":
            if input_data:
                if not validate_name(input_data):
                    raise StateException("Invalid first name format")
                success, error = state_manager.update_state({
                    "flow_data": {
                        **flow_data,
                        "first_name": input_data.strip(),
                        "current_step": "last_name"
                    }
                })
                if not success:
                    raise StateException(f"Failed to update state: {error}")
                return handle_last_name_prompt(state_manager)
            return handle_first_name_prompt(state_manager)

        elif step == "last_name":
            if input_data:
                if not validate_name(input_data):
                    raise StateException("Invalid last name format")
                success, error = state_manager.update_state({
                    "flow_data": {
                        **flow_data,
                        "last_name": input_data.strip(),
                        "current_step": "confirm"
                    }
                })
                if not success:
                    raise StateException(f"Failed to update state: {error}")
                return handle_confirmation(state_manager)
            return handle_last_name_prompt(state_manager)

        else:
            raise StateException(f"Invalid registration step: {step}")

    except StateException as e:
        logger.error(f"Registration step error: {str(e)}")
        raise
