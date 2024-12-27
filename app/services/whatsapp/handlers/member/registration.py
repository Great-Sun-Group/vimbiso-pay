"""Member registration flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator
from core.messaging.types import Message
from ...types import WhatsAppMessage
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
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {"channel": state_manager.get("channel")},
            {"channel"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # Get channel info
        channel = state_manager.get("channel")
        return MemberTemplates.create_first_name_prompt(channel["identifier"])
    except ValueError as e:
        return WhatsAppMessage.create_text("unknown", f"Error: {str(e)}")


def handle_last_name_prompt(state_manager: Any) -> Message:
    """Get last name prompt enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {"channel": state_manager.get("channel")},
            {"channel"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # Get channel info
        channel = state_manager.get("channel")
        return MemberTemplates.create_last_name_prompt(channel["identifier"])
    except ValueError as e:
        return WhatsAppMessage.create_text("unknown", f"Error: {str(e)}")


def handle_confirmation(state_manager: Any) -> Message:
    """Create registration confirmation message enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {
                "channel": state_manager.get("channel"),
                "flow_data": state_manager.get("flow_data")
            },
            {"channel", "flow_data"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # Get required data
        channel = state_manager.get("channel")
        flow_data = state_manager.get("flow_data", {})

        first_name = flow_data.get("first_name")
        last_name = flow_data.get("last_name")
        if not first_name or not last_name:
            raise ValueError("Name data required for confirmation")

        return MemberTemplates.create_registration_confirmation(
            channel["identifier"],
            first_name,
            last_name
        )
    except ValueError as e:
        return WhatsAppMessage.create_text("unknown", f"Error: {str(e)}")


def handle_registration_completion(state_manager: Any, credex_service: Any) -> Message:
    """Complete registration flow enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {
                "channel": state_manager.get("channel"),
                "flow_data": state_manager.get("flow_data")
            },
            {"channel", "flow_data"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # Get required data
        channel = state_manager.get("channel")
        flow_data = state_manager.get("flow_data", {})

        first_name = flow_data.get("first_name")
        last_name = flow_data.get("last_name")
        if not first_name or not last_name:
            raise ValueError("Name data required for registration")

        # Register member
        member_data = {
            "firstname": first_name,
            "lastname": last_name,
            "defaultDenom": "USD"
        }
        success, response = credex_service['register_member'](
            member_data,
            channel["identifier"]
        )

        if not success:
            raise ValueError(response.get("message", "Registration failed"))

        # Update state with new member info
        token = response.get("data", {}).get("action", {}).get("details", {}).get("token")
        member_id = response.get("data", {}).get("action", {}).get("details", {}).get("memberID")
        if not token or not member_id:
            raise ValueError("Registration response missing required data")

        # Update state
        success, error = state_manager.update_state({
            "member_id": member_id,
            "jwt_token": token,
            "authenticated": True,
            "_last_updated": audit.get_current_timestamp(),
            "flow_data": None  # Clear flow data
        })

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


def process_registration_step(state_manager: Any, step: str, input_data: Any = None) -> Message:
    """Process registration step enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {
                "channel": state_manager.get("channel"),
                "flow_data": state_manager.get("flow_data")
            },
            {"channel", "flow_data"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # Handle each step
        if step == "first_name":
            if input_data:
                if not validate_name(input_data):
                    raise ValueError("Invalid first name format")
                success, error = state_manager.update_state({
                    "flow_data": {
                        **state_manager.get("flow_data", {}),
                        "first_name": input_data.strip(),
                        "current_step": "last_name"
                    }
                })
                return handle_last_name_prompt(state_manager)
            return handle_first_name_prompt(state_manager)

        elif step == "last_name":
            if input_data:
                if not validate_name(input_data):
                    raise ValueError("Invalid last name format")
                success, error = state_manager.update_state({
                    "flow_data": {
                        **state_manager.get("flow_data", {}),
                        "last_name": input_data.strip(),
                        "current_step": "confirm"
                    }
                })
                return handle_confirmation(state_manager)
            return handle_last_name_prompt(state_manager)

        else:
            raise ValueError(f"Invalid registration step: {step}")

    except ValueError as e:
        return WhatsAppMessage.create_text(
            state_manager.get("channel", {}).get("identifier", "unknown"),
            f"Error: {str(e)}"
        )
