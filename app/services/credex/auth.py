"""CredEx authentication service using pure functions"""
from typing import Any, Dict, Tuple

from core.utils.error_handler import error_decorator

from .base import make_credex_request


@error_decorator
def login(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Authenticate user enforcing SINGLE SOURCE OF TRUTH"""
    # Get channel info from state
    channel = state_manager.get("channel")

    # Make API request with channel identifier
    response_data = make_credex_request(
        'auth', 'login',
        payload={"phone": channel["identifier"]},
        state_manager=state_manager
    )

    # Check response type
    action = response_data.get("data", {}).get("action", {})
    success = action.get("type") == "MEMBER_LOGIN"

    if success:
        # Let StateManager handle complete login response
        state_manager.update_state({
            "flow_data": {
                "response": response_data
            }
        })

    return success, response_data


@error_decorator
def register_member(state_manager: Any, member_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Register new member enforcing SINGLE SOURCE OF TRUTH"""
    # Make API request with provided member data
    response_data = make_credex_request(
        'auth', 'register',
        payload=member_data,
        state_manager=state_manager
    )

    # Check response type
    action = response_data.get("data", {}).get("action", {})
    success = action.get("type") == "MEMBER_REGISTER"

    if success:
        # Let StateManager handle complete registration response
        state_manager.update_state({
            "flow_data": {
                "response": response_data
            }
        })

    return success, response_data
