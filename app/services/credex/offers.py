"""CredEx offer operations using pure functions"""
from typing import Any, Dict, Tuple

from core.utils.error_handler import error_decorator

from .base import make_credex_request


@error_decorator
def offer_credex(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Create new CredEx offer"""
    # Update state to trigger validation
    state_manager.update_state({
        "flow_data": {
            "current_step": "create_offer",
            "step": 1,
            "data": {
                "credexType": "PURCHASE",
                "OFFERSorREQUESTS": "OFFERS",
                "securedCredex": True
            }
        }
    })

    # Get validated data from state
    flow_data = state_manager.get_flow_step_data()
    offer_data = flow_data.get("offer_data", {})

    # Let StateManager validate through update
    state_manager.update_state({
        "flow_data": {
            "data": {
                "api_payload": {
                    "Denomination": offer_data.get("denomination"),
                    "InitialAmount": offer_data.get("amount"),
                    "credexType": "PURCHASE",
                    "OFFERSorREQUESTS": "OFFERS",
                    "securedCredex": offer_data.get("securedCredex", True)
                }
            }
        }
    })

    # Get validated payload
    flow_data = state_manager.get_flow_step_data()
    payload = flow_data.get("api_payload", {})

    # Make API request (ErrorHandler handles any errors)
    response = make_credex_request(
        'credex', 'create',
        payload=payload,
        state_manager=state_manager
    )

    # Let StateManager validate response through update
    state_manager.update_state({
        "flow_data": {
            "current_step": "check_success",
            "step": 2,
            "data": {
                "response": response.json()
            }
        }
    })

    # Get validated response
    flow_data = state_manager.get_flow_step_data()
    return True, flow_data.get("response")


@error_decorator
def confirm_credex(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Confirm CredEx offer"""
    # Update state to trigger validation
    state_manager.update_state({
        "flow_data": {
            "current_step": "confirm_offer",
            "step": 1
        }
    })

    # Get validated data from state
    flow_data = state_manager.get_flow_step_data()
    credex_id = flow_data.get("credex_id")
    issuer_account_id = flow_data.get("issuer_account_id")

    # Make API request (ErrorHandler handles any errors)
    response = make_credex_request(
        'credex', 'confirm',
        payload={"credexID": credex_id, "issuerAccountID": issuer_account_id},
        state_manager=state_manager
    )

    # Let StateManager validate response through update
    state_manager.update_state({
        "flow_data": {
            "current_step": "check_success",
            "step": 2,
            "data": {
                "response": response.json()
            }
        }
    })

    # Get validated response
    flow_data = state_manager.get_flow_step_data()
    return True, flow_data.get("response")


@error_decorator
def accept_credex(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Accept CredEx offer"""
    # Update state to trigger validation
    state_manager.update_state({
        "flow_data": {
            "current_step": "accept_offer",
            "step": 1
        }
    })

    # Get validated data from state
    flow_data = state_manager.get_flow_step_data()
    credex_id = flow_data.get("credex_id")

    # Make API request (ErrorHandler handles any errors)
    response = make_credex_request(
        'credex', 'accept',
        payload={"credexID": credex_id},
        state_manager=state_manager
    )

    # Let StateManager validate response through update
    state_manager.update_state({
        "flow_data": {
            "current_step": "check_success",
            "step": 2,
            "data": {
                "response": response.json()
            }
        }
    })

    # Get validated response
    flow_data = state_manager.get_flow_step_data()
    return True, flow_data.get("response")


@error_decorator
def decline_credex(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Decline CredEx offer"""
    # Update state to trigger validation
    state_manager.update_state({
        "flow_data": {
            "current_step": "decline_offer",
            "step": 1
        }
    })

    # Get validated data from state
    flow_data = state_manager.get_flow_step_data()
    credex_id = flow_data.get("credex_id")

    # Make API request (ErrorHandler handles any errors)
    response = make_credex_request(
        'credex', 'decline',
        payload={"credexID": credex_id},
        state_manager=state_manager
    )

    # Let StateManager validate response through update
    state_manager.update_state({
        "flow_data": {
            "current_step": "check_success",
            "step": 2,
            "data": {
                "response": response.json()
            }
        }
    })

    # Get validated response
    flow_data = state_manager.get_flow_step_data()
    return True, flow_data.get("response")


@error_decorator
def cancel_credex(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Cancel CredEx offer"""
    # Update state to trigger validation
    state_manager.update_state({
        "flow_data": {
            "current_step": "cancel_offer",
            "step": 1
        }
    })

    # Get validated data from state
    flow_data = state_manager.get_flow_step_data()
    credex_id = flow_data.get("credex_id")

    # Make API request (ErrorHandler handles any errors)
    response = make_credex_request(
        'credex', 'cancel',
        payload={"credexID": credex_id},
        state_manager=state_manager
    )

    # Let StateManager validate response through update
    state_manager.update_state({
        "flow_data": {
            "current_step": "check_success",
            "step": 2,
            "data": {
                "response": response.json()
            }
        }
    })

    # Get validated response
    flow_data = state_manager.get_flow_step_data()
    return True, flow_data.get("response")


@error_decorator
def get_credex(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Get CredEx offer details"""
    # Update state to trigger validation
    state_manager.update_state({
        "flow_data": {
            "current_step": "get_offer",
            "step": 1
        }
    })

    # Get validated data from state
    flow_data = state_manager.get_flow_step_data()
    credex_id = flow_data.get("credex_id")

    # Make API request (ErrorHandler handles any errors)
    response = make_credex_request(
        'credex', 'get',
        payload={"credexID": credex_id},
        state_manager=state_manager
    )

    # Let StateManager validate response through update
    state_manager.update_state({
        "flow_data": {
            "current_step": "check_success",
            "step": 2,
            "data": {
                "response": response.json()
            }
        }
    })

    # Get validated response
    flow_data = state_manager.get_flow_step_data()
    return True, flow_data.get("response")


@error_decorator
def get_ledger(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Get member ledger"""
    # Update state to trigger validation
    state_manager.update_state({
        "flow_data": {
            "current_step": "get_ledger",
            "step": 1
        }
    })

    # Get validated data from state
    member_id = state_manager.get_member_id()

    # Make API request (ErrorHandler handles any errors)
    response = make_credex_request(
        'credex', 'get_ledger',
        payload={"memberId": member_id},
        state_manager=state_manager
    )

    # Let StateManager validate response through update
    state_manager.update_state({
        "flow_data": {
            "current_step": "check_success",
            "step": 2,
            "data": {
                "response": response.json()
            }
        }
    })

    # Get validated response
    flow_data = state_manager.get_flow_step_data()
    return True, flow_data.get("response")
