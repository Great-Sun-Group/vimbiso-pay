"""CredEx member operations with strict state validation"""
import logging
from typing import Any, Dict, Tuple

from core.utils.exceptions import FlowException, SystemException

from .base import make_credex_request

logger = logging.getLogger(__name__)


def get_member_accounts(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Get member accounts from state enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Let StateManager validate through update
        state_manager.update_state({
            "flow_data": {
                "flow_type": "accounts",
                "step": 0,
                "current_step": "fetch"
            }
        })

        # Let StateManager validate accounts through update
        state_manager.update_state({
            "validation": {
                "type": "accounts",
                "required": True
            }
        })

        # Get validated account data
        account_data = state_manager.get_account_data()

        return True, {
            "data": {
                "accounts": account_data["accounts"],
                "active_account_id": account_data["active_id"]
            }
        }

    except FlowException:
        # Let flow errors propagate up
        raise

    except Exception as e:
        # Wrap other errors as system errors
        raise SystemException(
            message=str(e),
            code="ACCOUNT_ERROR",
            service="credex_member",
            action="get_member_accounts"
        )


def validate_account_handle(handle: str, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Validate CredEx handle enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Make API request (StateManager validates jwt_token)
        response_data = make_credex_request(
            'account', 'validate_account_handle',
            payload={"accountHandle": handle},
            state_manager=state_manager
        )

        return True, response_data

    except FlowException:
        # Let flow errors propagate up
        raise

    except Exception as e:
        # Wrap other errors as system errors
        raise SystemException(
            message=str(e),
            code="HANDLE_ERROR",
            service="credex_member",
            action="validate_account_handle",
            details={
                "handle": handle
            }
        )


def refresh_member_info(state_manager: Any) -> None:
    """Refresh member information enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Let StateManager validate through update
        state_manager.update_state({
            "flow_data": {
                "flow_type": "refresh",
                "step": 0,
                "current_step": "start"
            }
        })

        # Make API request (StateManager validates channel)
        response_data = make_credex_request(
            'auth', 'login',
            state_manager=state_manager
        )

        # Let StateManager validate response through update
        state_manager.update_state({
            "flow_data": {
                "flow_type": "refresh",
                "step": 1,
                "current_step": "complete",
                "data": {
                    "refresh": response_data
                }
            }
        })

        return None

    except FlowException:
        # Let flow errors propagate up
        raise

    except Exception as e:
        # Wrap other errors as system errors
        raise SystemException(
            message=str(e),
            code="REFRESH_ERROR",
            service="credex_member",
            action="refresh_member_info"
        )
