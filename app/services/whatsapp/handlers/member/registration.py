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

        # Get channel ID for registration
        phone = state_manager.get_channel_id()

        # Register member
        success, response = register_member(phone, input_data)
        if not success:
            raise StateException("Failed to register member")

        # Get data from onboarding response
        dashboard = response["data"]["dashboard"]
        action = response["data"]["action"]

        # Get member data from dashboard.member
        member = dashboard["member"]  # Member data is under member
        member_data = {
            "memberTier": member["memberTier"],  # Always 1 for new members
            "remainingAvailableUSD": member.get("remainingAvailableUSD"),
            "firstname": member["firstname"],
            "lastname": member["lastname"],
            "memberHandle": member["memberHandle"],  # Initially phone number
            "defaultDenom": member["defaultDenom"]
        }

        # Update state with member data and registration complete
        success, error = state_manager.update_state({
            # Core identity - SINGLE SOURCE OF TRUTH
            "jwt_token": action["details"]["token"],
            "authenticated": True,
            "member_id": action["details"]["memberID"],

            # Member data at top level
            "member_data": member_data,

            # Account data at top level (single personal account)
            "accounts": dashboard["accounts"],
            "active_account_id": action["details"]["defaultAccountID"],

            # Flow state only for routing
            "flow_data": {
                "flow_type": "registration",
                "step": 1,
                "current_step": "complete"
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
                        "firstname": input_data.get("firstname"),
                        "lastname": input_data.get("lastname"),
                        "defaultDenom": input_data.get("defaultDenom")
                    }
                }
            }
        })
        if not success:
            raise StateException(f"Failed to update validation state: {error}")

        # Get validation data
        flow_data = state_manager.get_flow_step_data()
        validation = flow_data.get("validation", {})

        # Validate required fields from API spec
        firstname = validation["firstname"]
        if not firstname or len(firstname) < 3 or len(firstname) > 50:
            raise StateException("First name must be between 3 and 50 characters")

        lastname = validation["lastname"]
        if not lastname or len(lastname) < 3 or len(lastname) > 50:
            raise StateException("Last name must be between 3 and 50 characters")

        defaultDenom = validation["defaultDenom"]
        valid_denoms = {"CXX", "CAD", "USD", "XAU", "ZWG"}
        if not defaultDenom or defaultDenom not in valid_denoms:
            raise StateException(f"Invalid defaultDenom. Must be one of: {', '.join(valid_denoms)}")

        # Phone validation handled by channel (phone number format: ^[1-9]\d{1,14}$)

        # Update state with validated data
        success, error = state_manager.update_state({
            "flow_data": {
                "flow_type": "registration",
                "step": 0,
                "current_step": "validated",
                "data": {
                    "firstname": firstname,
                    "lastname": lastname,
                    "defaultDenom": defaultDenom,
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
