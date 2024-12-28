"""Registration handler enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.utils.exceptions import StateException
from services.credex.service import register_member

logger = logging.getLogger(__name__)


def handle_registration(state_manager: Any, input_data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Handle registration enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Initialize registration flow with input data
        success, error = state_manager.update_state({
            "flow_data": {
                "flow_type": "registration",
                "step": 0,
                "current_step": "validate",
                "data": input_data
            }
        })
        if not success:
            raise StateException(f"Failed to initialize registration: {error}")

        # Get channel for registration
        channel = state_manager.get("channel")
        phone = channel["identifier"]

        # Register member
        success, response = register_member(phone, input_data)
        if not success:
            raise StateException("Failed to register member")

        member_data = response["data"]
        member_id = member_data["member_id"]
        account_id = member_data["account_id"]

        # Update state with member data and registration complete
        success, error = state_manager.update_state({
            # Member data at top level
            "member_id": member_id,
            "account_id": account_id,
            "authenticated": True,
            # Flow state
            "flow_data": {
                "flow_type": "registration",
                "step": 1,
                "current_step": "complete",
                "data": {
                    "member": member_data
                }
            }
        })
        if not success:
            raise StateException(f"Failed to update state: {error}")

        return True, None

    except StateException as e:
        logger.error(f"Registration error: {str(e)}")
        # Update state with error
        state_manager.update_state({
            "flow_data": {
                "flow_type": "registration",
                "step": 0,
                "current_step": "error",
                "data": {
                    "error": str(e),
                    "input": input_data
                }
            }
        })
        return False, {
            "error": {
                "type": "REGISTRATION_ERROR",
                "message": str(e)
            }
        }


def validate_registration_input(state_manager: Any, input_data: Dict[str, Any]) -> None:
    """Validate registration input through state update"""
    try:
        # Update state with validation data
        success, error = state_manager.update_state({
            "flow_data": {
                "flow_type": "registration",
                "step": 0,
                "current_step": "validate",
                "data": {
                    "validation": {
                        "first_name": input_data.get("first_name"),
                        "last_name": input_data.get("last_name"),
                        "email": input_data.get("email")
                    }
                }
            }
        })
        if not success:
            raise StateException(f"Failed to update validation state: {error}")

        # Get validation data
        flow_data = state_manager.get("flow_data")
        validation = flow_data["data"]["validation"]

        # First name validation
        first_name = validation["first_name"]
        if not first_name or len(first_name) < 2:
            raise StateException("First name must be at least 2 characters")

        # Last name validation
        last_name = validation["last_name"]
        if not last_name or len(last_name) < 2:
            raise StateException("Last name must be at least 2 characters")

        # Email validation
        email = validation["email"]
        if not email or "@" not in email:
            raise StateException("Invalid email format")

        # Update state with validated data
        success, error = state_manager.update_state({
            "flow_data": {
                "flow_type": "registration",
                "step": 0,
                "current_step": "validated",
                "data": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "validation": {
                        "success": True
                    }
                }
            }
        })
        if not success:
            raise StateException(f"Failed to update validated state: {error}")

    except StateException as e:
        # Update state with validation error
        state_manager.update_state({
            "flow_data": {
                "flow_type": "registration",
                "step": 0,
                "current_step": "error",
                "data": {
                    "error": str(e),
                    "validation": {
                        "success": False,
                        "error": str(e)
                    }
                }
            }
        })
        raise
