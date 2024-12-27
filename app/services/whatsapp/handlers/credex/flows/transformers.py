"""Data transformation logic for credex flows"""
import logging
from typing import Any, Dict, Union

from core.utils import audit
from .validators import AMOUNT_PATTERN, validate_amount, validate_handle

logger = logging.getLogger(__name__)


def transform_amount(amount_str: str, flow_id: str = None) -> Dict[str, Any]:
    """Transform amount string to structured data"""
    # Validate first
    validate_amount(amount_str, flow_id)

    try:
        match = AMOUNT_PATTERN.match(str(amount_str).strip().upper())
        if not match:
            raise ValueError("Invalid amount format")

        # Extract amount and denomination
        if match.group(1):  # Currency first
            denom, amount = match.group(1), match.group(2)
        elif match.group(3):  # Amount first
            amount, denom = match.group(3), match.group(4)
        else:  # Just amount
            amount, denom = match.group(5), None

        # Log transformation at INFO level
        logger.info(f"Transforming amount: {amount} {denom or 'USD'}")

        # Validate amount is a positive number
        amount_float = float(amount)
        if amount_float <= 0:
            raise ValueError("Amount must be greater than 0")

        result = {
            "amount": amount_float,
            "denomination": denom or "USD"
        }

        # Log details at DEBUG level
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Input: {amount_str}")
            logger.debug(f"Parsed: {result}")

        return result

    except Exception as e:
        # Log error with context
        error_context = {
            "input": amount_str,
            "error": str(e),
            "error_type": type(e).__name__
        }
        logger.error("Amount transformation failed", extra=error_context, exc_info=True)

        if flow_id:
            audit.log_validation_event(
                flow_id,
                "amount",
                amount_str,
                False,
                str(e)
            )

        raise ValueError(f"Failed to transform amount: {str(e)}")


def transform_handle(handle: Union[str, Dict[str, Any]], credex_service: Any, flow_id: str = None) -> Dict[str, Any]:
    """Transform and validate handle"""
    # Validate first
    validate_handle(handle, flow_id)

    # Extract handle from interactive or text
    if isinstance(handle, dict):
        interactive = handle.get("interactive", {})
        if interactive.get("type") == "text":
            handle = interactive.get("text", {}).get("body", "")
        else:
            raise ValueError("Invalid handle format")

    handle = handle.strip()

    try:
        # Store validation context
        validation_context = {
            "_validation_state": {
                "step_id": "handle",
                "input": handle,
                "timestamp": audit.get_current_timestamp()
            }
        }

        # Validate handle through API
        success, response = credex_service.services['member'].validate_handle(handle)
        if not success:
            if flow_id:
                audit.log_validation_event(
                    flow_id,
                    "handle",
                    handle,
                    False,
                    response.get("message", "Invalid handle")
                )
            raise ValueError(response.get("message", "Invalid handle"))

        # Get account data
        data = response.get("data", {})
        if not data or not data.get("accountID"):
            raise ValueError("Invalid account data received from API")

        # Create result with validation context
        result = {
            "handle": handle,
            "name": data.get("accountName", handle),
            "account_id": data.get("accountID"),
            **validation_context,
            "_validation_success": True
        }

        # Log successful validation
        if flow_id:
            audit.log_validation_event(
                flow_id,
                "handle",
                handle,
                True,
                "Handle validated successfully"
            )

        return result

    except Exception as e:
        if flow_id:
            audit.log_flow_event(
                flow_id,
                "handle_validation_error",
                "handle",
                {"error": str(e), "handle": handle},
                "failure"
            )
        raise ValueError(f"Handle validation failed: {str(e)}")


def format_amount(amount: float, denomination: str) -> str:
    """Format amount based on denomination"""
    if denomination in {"USD", "ZWG", "CAD"}:
        return f"${amount:.2f} {denomination}"
    elif denomination == "XAU":
        return f"{amount:.4f} {denomination}"
    return f"{amount} {denomination}"


def transform_state_for_dashboard(current_state: Dict[str, Any], response: Dict[str, Any], flow_id: str = None) -> Dict[str, Any]:
    """Transform state for dashboard update"""
    try:
        # Get dashboard data
        dashboard = response.get("data", {}).get("dashboard")
        if not dashboard:
            if flow_id:
                audit.log_flow_event(
                    flow_id,
                    "dashboard_update_error",
                    None,
                    current_state,
                    "failure",
                    "No dashboard data in response"
                )
            raise ValueError("Missing dashboard data")

        # Get channel ID from state
        channel_id = current_state.get("channel", {}).get("identifier")
        if not channel_id:
            raise ValueError("Missing channel identifier")

        # Structure profile data
        action = response.get("data", {}).get("action", {})
        profile_data = {
            "action": {
                "id": action.get("id", ""),
                "type": action.get("type"),
                "timestamp": audit.get_current_timestamp(),
                "details": action.get("details", {}),
                "message": (
                    action.get("message") or
                    action.get("details", {}).get("message") or
                    ("CredEx offer created successfully" if action.get("type") == "CREDEX_CREATED" else "")
                ),
                "status": "success" if action.get("type") == "CREDEX_CREATED" else action.get("status", "")
            },
            "dashboard": dashboard
        }

        # Find personal account
        accounts = dashboard.get("accounts", [])
        personal_account = next(
            (account for account in accounts if account.get("accountType") == "PERSONAL"),
            next(
                (account for account in accounts if account.get("accountHandle") == channel_id),
                current_state.get("current_account")
            )
        )

        # Build new state preserving required fields
        new_state = {
            "member_id": current_state.get("member_id"),  # SINGLE SOURCE OF TRUTH
            "channel": current_state.get("channel"),  # SINGLE SOURCE OF TRUTH
            "authenticated": current_state.get("authenticated", True),
            "jwt_token": current_state.get("jwt_token"),  # SINGLE SOURCE OF TRUTH
            "account_id": current_state.get("account_id"),
            "current_account": personal_account,
            "profile": profile_data,
            "_validation_context": current_state.get("_validation_context", {}),
            "_validation_state": current_state.get("_validation_state", {}),
            "_last_updated": audit.get_current_timestamp()
        }

        # Preserve additional fields
        for key in current_state:
            if key.startswith('_') and key not in new_state:
                new_state[key] = current_state[key]

        # Log state transformation
        if flow_id:
            audit.log_state_transition(
                flow_id,
                current_state,
                new_state,
                "success"
            )

        return new_state

    except Exception as e:
        logger.error(f"State transformation error: {str(e)}")
        if flow_id:
            audit.log_flow_event(
                flow_id,
                "state_transform_error",
                None,
                {"error": str(e)},
                "failure"
            )
        raise
