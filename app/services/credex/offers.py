"""CredEx service layer using pure functions"""
from typing import Any, Dict, Tuple

from core.api.credex import accept_bulk_credex as api_accept_bulk
from core.api.credex import accept_credex as api_accept
from core.api.credex import cancel_credex as api_cancel
from core.api.credex import decline_credex as api_decline
from core.api.credex import get_credex as api_get
from core.api.credex import get_ledger as api_get_ledger
from core.api.credex import offer_credex as api_offer
from core.utils.error_handler import error_decorator


@error_decorator
def offer_credex(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Create new CredEx offer"""
    return api_offer(state_manager)


@error_decorator
def accept_credex(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Accept CredEx offer"""
    return api_accept(state_manager)


@error_decorator
def decline_credex(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Decline CredEx offer"""
    return api_decline(state_manager)


@error_decorator
def cancel_credex(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Cancel CredEx offer"""
    return api_cancel(state_manager)


@error_decorator
def get_credex(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Get CredEx offer details"""
    return api_get(state_manager)


@error_decorator
def accept_bulk_credex(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Accept multiple CredEx offers"""
    return api_accept_bulk(state_manager)


@error_decorator
def get_ledger(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Get member ledger"""
    return api_get_ledger(state_manager)
