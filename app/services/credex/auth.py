"""CredEx authentication service using pure functions"""
from typing import Any, Dict, Tuple

from core.utils.error_handler import error_decorator

from .base import make_credex_request


@error_decorator
def login(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Authenticate user enforcing SINGLE SOURCE OF TRUTH"""
    # Make API request (channel info passed through state)
    response_data = make_credex_request(
        'auth', 'login',
        state_manager=state_manager
    )

    success = response_data.get("type") == "MEMBER_LOGIN"

    if success:
        # Update flow state with login response
        state_manager.update_state({
            "flow_data": {
                "type": "auth_response",
                "data": response_data,
                "step": "login_response"
            }
        })

    return success, response_data


@error_decorator
def register_member(state_manager: Any, member_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Register new member enforcing SINGLE SOURCE OF TRUTH"""
    # Make API request with member data
    response_data = make_credex_request(
        'auth', 'register',
        payload=member_data,
        state_manager=state_manager
    )

    success = response_data.get("type") == "MEMBER_REGISTER"

    if success:
        # Update flow state with registration response
        state_manager.update_state({
            "flow_data": {
                "type": "auth_response",
                "data": response_data,
                "step": "register_response"
            }
        })

    return success, response_data
