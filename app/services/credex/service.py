"""CredEx service using pure functions with strict state validation"""
import logging
from typing import Any, Dict, Tuple

from core.utils.exceptions import StateException

from .member import validate_account_handle as member_validate_handle
from .offers import get_credex, offer_credex

logger = logging.getLogger(__name__)


def get_credex_service(state_manager: Any) -> Dict[str, Any]:
    """Get CredEx service functions with strict state validation"""
    return {
        'validate_account_handle': lambda handle: validate_member_handle(state_manager, handle),
        'get_credex': lambda credex_id: get_credex(credex_id, state_manager),
        'offer_credex': lambda data: offer_credex(data, state_manager)
    }


def validate_member_handle(state_manager: Any, handle: str) -> Tuple[bool, Dict[str, Any]]:
    """Validate member handle (simple endpoint, no state update needed)"""
    try:
        return member_validate_handle(handle, state_manager)

    except StateException as e:
        error_msg = str(e)
        logger.error(f"Handle validation error: {error_msg}")
        return False, {"message": error_msg}
