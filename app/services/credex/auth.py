"""CredEx authentication service using pure functions"""
from typing import Any, Dict, Tuple

from core.utils.error_handler import error_decorator

from .base import make_credex_request


@error_decorator
def login(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Authenticate user enforcing SINGLE SOURCE OF TRUTH"""
    # Let StateManager validate channel through update
    state_manager.update_state({
        "validation": {
            "type": "channel",
            "required": True
        }
    })

    # Get validated channel data
    channel_data = state_manager.get_channel_data()

    # Make API request with validated channel data
    response_data = make_credex_request(
        'auth', 'login',
        payload={"phone": channel_data["identifier"]},
        state_manager=state_manager
    )

    # Let StateManager validate response through update
    state_manager.update_state({
        "validation": {
            "type": "auth_response",
            "data": response_data
        }
    })

    # Get validated response data
    validated_response = state_manager.get_auth_response()
    success = validated_response.get("type") == "MEMBER_LOGIN"

    if success:
        # Let StateManager handle complete login response
        state_manager.update_state({
            "flow_data": {
                "response": validated_response
            }
        })

    return success, validated_response


@error_decorator
def register_member(state_manager: Any, member_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Register new member enforcing SINGLE SOURCE OF TRUTH"""
    # Let StateManager validate member data through update
    state_manager.update_state({
        "validation": {
            "type": "member_data",
            "data": member_data
        }
    })

    # Get validated member data
    validated_data = state_manager.get_member_data()

    # Make API request with validated member data
    response_data = make_credex_request(
        'auth', 'register',
        payload=validated_data,
        state_manager=state_manager
    )

    # Let StateManager validate response through update
    state_manager.update_state({
        "validation": {
            "type": "auth_response",
            "data": response_data
        }
    })

    # Get validated response data
    validated_response = state_manager.get_auth_response()
    success = validated_response.get("type") == "MEMBER_REGISTER"

    if success:
        # Let StateManager handle complete registration response
        state_manager.update_state({
            "flow_data": {
                "response": validated_response
            }
        })

    return success, validated_response
