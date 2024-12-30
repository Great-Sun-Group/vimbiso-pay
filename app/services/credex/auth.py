"""CredEx authentication service using pure functions"""
from typing import Any, Dict, Tuple

from core.utils.error_handler import error_decorator

from .base import make_credex_request


@error_decorator
def login(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Authenticate user enforcing SINGLE SOURCE OF TRUTH"""
    # Let StateManager validate through flow state update
    state_manager.update_state({
        "flow_data": {
            "flow_type": "auth",  # Not an authenticated flow
            "step": 1,
            "current_step": "login",
            "data": {
                "channel": state_manager.get("channel")  # StateManager validates
            }
        }
    })

    # Get validated channel info
    flow_data = state_manager.get_flow_step_data()
    channel = flow_data.get("channel")

    # Make API request (ErrorHandler handles any errors)
    response = make_credex_request(
        'auth', 'login',
        payload={"phone": channel["identifier"]},
        state_manager=state_manager
    )

    # Let StateManager validate through flow advance
    state_manager.update_state({
        "flow_data": {
            "next_step": "complete",
            "data": {
                "response": response.json()
            }
        }
    })

    # Get validated response
    flow_data = state_manager.get_flow_step_data()
    return True, flow_data.get("response")


@error_decorator
def register_member(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Register new member enforcing SINGLE SOURCE OF TRUTH"""
    # Let StateManager validate through flow state update
    state_manager.update_state({
        "flow_data": {
            "flow_type": "auth",  # Not an authenticated flow
            "step": 1,
            "current_step": "register",
            "data": {
                "validation": {
                    "valid_denoms": {"CXX", "CAD", "USD", "XAU", "ZWG"},
                    "name_min_length": 3,
                    "name_max_length": 50
                }
            }
        }
    })

    # Let StateManager validate member data
    state_manager.update_state({
        "flow_data": {
            "next_step": "validate",
            "data": {
                "member_data": {
                    "defaultDenom": "USD",  # Default value
                    "firstname": "",  # StateManager validates
                    "lastname": ""  # StateManager validates
                }
            }
        }
    })

    # Get validated member data
    flow_data = state_manager.get_flow_step_data()
    member_data = flow_data.get("member_data")

    # Make API request (ErrorHandler handles any errors)
    response = make_credex_request(
        'auth', 'register',
        payload=member_data,
        state_manager=state_manager
    )

    # Let StateManager validate through flow advance
    state_manager.update_state({
        "flow_data": {
            "next_step": "complete",
            "data": {
                "response": response.json()
            }
        }
    })

    # Get validated response
    flow_data = state_manager.get_flow_step_data()
    return True, flow_data.get("response")


@error_decorator
def refresh_token(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Refresh authentication token enforcing SINGLE SOURCE OF TRUTH"""
    # Let StateManager validate through flow state update
    state_manager.update_state({
        "flow_data": {
            "flow_type": "auth",  # Not an authenticated flow
            "step": 1,
            "current_step": "refresh",
            "data": {
                "channel": state_manager.get("channel")  # StateManager validates
            }
        }
    })

    # Get validated channel info
    flow_data = state_manager.get_flow_step_data()
    channel = flow_data.get("channel")

    # Make API request (ErrorHandler handles any errors)
    response = make_credex_request(
        'auth', 'login',
        payload={"phone": channel["identifier"]},
        state_manager=state_manager
    )

    # Let StateManager validate through flow advance
    state_manager.update_state({
        "flow_data": {
            "next_step": "complete",
            "data": {
                "response": response.json()
            }
        }
    })

    # Get validated response
    flow_data = state_manager.get_flow_step_data()
    return True, flow_data.get("response")


@error_decorator
def get_dashboard(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Get dashboard data from login response enforcing SINGLE SOURCE OF TRUTH"""
    # Let StateManager validate through flow state update
    state_manager.update_state({
        "flow_data": {
            "flow_type": "dashboard",  # Requires authentication
            "step": 1,
            "current_step": "get",
            "data": {
                "channel": state_manager.get("channel")  # StateManager validates
            }
        }
    })

    # Get validated channel info
    flow_data = state_manager.get_flow_step_data()
    channel = flow_data.get("channel")

    # Make API request (ErrorHandler handles any errors)
    response = make_credex_request(
        'auth', 'login',
        payload={"phone": channel["identifier"]},
        state_manager=state_manager
    )

    # Let StateManager validate through flow advance
    state_manager.update_state({
        "flow_data": {
            "next_step": "complete",
            "data": {
                "response": response.json()
            }
        }
    })

    # Get validated response
    flow_data = state_manager.get_flow_step_data()
    return True, flow_data.get("response")
