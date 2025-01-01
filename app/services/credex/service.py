"""CredEx service using pure functions with strict state validation"""
import logging
from typing import Any, Dict, Tuple

from core.utils.exceptions import StateException

from .member import validate_account_handle as member_validate_handle
from .offers import (accept_credex, cancel_credex, decline_credex, get_credex,
                     offer_credex)

logger = logging.getLogger(__name__)


def get_credex_service(state_manager: Any) -> Dict[str, Any]:
    """Get CredEx service functions with strict state validation"""
    return {
        'validate_account_handle': lambda handle: validate_member_handle(handle, state_manager),
        'get_credex': lambda credex_id: prepare_get_credex(credex_id, state_manager),
        'offer_credex': lambda data: prepare_offer_credex(data, state_manager),
        'accept_credex': lambda credex_id: prepare_accept_credex(credex_id, state_manager),
        'decline_credex': lambda credex_id: prepare_decline_credex(credex_id, state_manager),
        'cancel_credex': lambda credex_id: prepare_cancel_credex(credex_id, state_manager)
    }


def prepare_offer_credex(data: Dict[str, Any], state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Prepare state for offer creation through validation"""
    # Let StateManager validate through update
    state_manager.update_state({
        "flow_data": {
            "api": {
                "type": "offer_credex",
                "data": data
            }
        }
    })
    return offer_credex(state_manager)


def prepare_get_credex(credex_id: str, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Prepare state for get credex through validation"""
    # Let StateManager validate through update
    state_manager.update_state({
        "flow_data": {
            "api": {
                "type": "get_credex",
                "credex_id": credex_id
            }
        }
    })
    return get_credex(state_manager)


def prepare_accept_credex(credex_id: str, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Prepare state for accept credex through validation"""
    # Let StateManager validate through update
    state_manager.update_state({
        "flow_data": {
            "api": {
                "type": "accept_credex",
                "credex_id": credex_id
            }
        }
    })
    return accept_credex(state_manager)


def prepare_decline_credex(credex_id: str, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Prepare state for decline credex through validation"""
    # Let StateManager validate through update
    state_manager.update_state({
        "flow_data": {
            "api": {
                "type": "decline_credex",
                "credex_id": credex_id
            }
        }
    })
    return decline_credex(state_manager)


def prepare_cancel_credex(credex_id: str, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Prepare state for cancel credex through validation"""
    # Let StateManager validate through update
    state_manager.update_state({
        "flow_data": {
            "api": {
                "type": "cancel_credex",
                "credex_id": credex_id
            }
        }
    })
    return cancel_credex(state_manager)


def validate_member_handle(handle: str, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Validate member handle (simple endpoint, no state update needed)"""
    try:
        return member_validate_handle(handle, state_manager)

    except StateException as e:
        error_msg = str(e)
        logger.error(f"Handle validation error: {error_msg}")
        return False, {"message": error_msg}
