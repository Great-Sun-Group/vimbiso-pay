"""Dashboard-related API operations using pure functions"""
import logging
from typing import Any, Dict, Tuple

from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ErrorContext
from core.utils.exceptions import StateException
from decouple import config

from .base import BASE_URL, handle_error_response, make_api_request

logger = logging.getLogger(__name__)


def get_dashboard(phone_number: str, jwt_token: str) -> Tuple[bool, Dict[str, Any]]:
    """Fetches the member's dashboard from the CredEx API"""
    logger.info("Fetching member dashboard")
    url = f"{BASE_URL}/getMemberDashboardByPhone"
    logger.info(f"Dashboard URL: {url}")

    payload = {"phone": phone_number}
    headers = {
        "Content-Type": "application/json",
        "x-client-api-key": config("CLIENT_API_KEY"),
        "Authorization": f"Bearer {jwt_token}"
    }

    try:
        response = make_api_request(url, headers, payload)
        if response.status_code == 200:
            return True, response.json()
        return handle_error_response(
            "Dashboard fetch",
            response,
            f"Dashboard fetch failed: Unexpected error (status code: {response.status_code})"
        )
    except Exception as e:
        logger.exception(f"Error during dashboard fetch: {str(e)}")
        return False, {"message": f"Dashboard fetch failed: {str(e)}"}


def validate_account_handle(handle: str, jwt_token: str) -> Tuple[bool, Dict[str, Any]]:
    """Validates a handle by making an API call to CredEx"""
    logger.info(f"Validating handle: {handle}")
    url = f"{BASE_URL}/getAccountByHandle"
    logger.info(f"Handle validation URL: {url}")

    payload = {"accountHandle": handle.lower()}
    headers = {
        "Content-Type": "application/json",
        "x-client-api-key": config("CLIENT_API_KEY"),
        "Authorization": f"Bearer {jwt_token}"
    }

    try:
        response = make_api_request(url, headers, payload, method="POST")
        if response.status_code == 200:
            response_data = response.json()
            if not response_data.get("Error"):
                logger.info("Handle validation successful")
                return True, response_data
            else:
                logger.error("Handle validation failed")
                return False, response_data
        else:
            return handle_error_response(
                "Handle validation",
                response,
                f"Handle validation failed: Unexpected error (status code: {response.status_code})"
            )
    except Exception as e:
        logger.exception(f"Error during handle validation: {str(e)}")
        return False, {"error": str(e)}


def get_ledger(payload: Dict[str, Any], jwt_token: str) -> Tuple[bool, Dict[str, Any]]:
    """Fetches ledger information"""
    logger.info("Fetching ledger")
    url = f"{BASE_URL}/getLedger"
    logger.info(f"Ledger URL: {url}")

    headers = {
        "Content-Type": "application/json",
        "x-client-api-key": config("CLIENT_API_KEY"),
        "Authorization": f"Bearer {jwt_token}"
    }

    try:
        response = make_api_request(url, headers, payload)
        if response.status_code == 200:
            return True, response.json()
        return handle_error_response(
            "Ledger fetch",
            response,
            f"Ledger fetch failed: Unexpected error (status code: {response.status_code})"
        )
    except Exception as e:
        logger.exception(f"Error during ledger fetch: {str(e)}")
        return False, {"error": f"Ledger fetch failed: {str(e)}"}


def setup_default_account(state_manager: Any, dashboard_data: Dict[str, Any]) -> bool:
    """Setup default account through state manager validation

    Args:
        state_manager: StateManager instance for validation
        dashboard_data: Dashboard response data

    Returns:
        bool: True if setup succeeded, False otherwise

    Raises:
        StateException: If state validation fails
    """
    try:
        # Extract account data
        member_tier = (
            dashboard_data.get("memberTier", {}).get("low", 1)
            if isinstance(dashboard_data.get("memberTier"), dict)
            else 1
        )

        accounts = dashboard_data.get("accounts", [])
        if not isinstance(accounts, list) or not accounts:
            raise ValueError("No accounts found in dashboard data")

        # Find eligible account
        if member_tier >= 2:
            raise ValueError("Member tier too high for default account")

        first_account = accounts[0]
        if not (
            isinstance(first_account, dict)
            and first_account.get("success")
            and isinstance(first_account.get("data"), dict)
        ):
            raise ValueError("Invalid account data structure")

        # Update state through StateManager validation
        account_update = {
            "accounts": accounts,  # Store all accounts at top level
            "active_account_id": first_account["data"]["accountID"]  # Reference account by ID
        }

        # Let StateManager validate and update
        success, error = state_manager.update_state(account_update)
        if not success:
            raise StateException(f"Failed to update account state: {error}")

        logger.info("Successfully set up default account")
        return True

    except Exception as e:
        error_context = ErrorContext(
            error_type="state",
            message=str(e),
            details={
                "operation": "setup_default_account",
                "error_message": str(e)
            }
        )
        ErrorHandler.handle_error(e, state_manager, error_context)
        return False


def process_dashboard_response(
    state_manager: Any,
    member_info: Dict[str, Any]
) -> bool:
    """Process dashboard response through state manager validation

    Args:
        state_manager: StateManager instance for validation
        member_info: Dashboard response data

    Returns:
        bool: True if processing succeeded, False otherwise

    Raises:
        StateException: If state validation fails
    """
    logger.info("Processing dashboard response")

    try:
        # Validate response format
        if not isinstance(member_info, dict):
            raise ValueError("Invalid member_info format")

        dashboard_data = member_info.get("data", {}).get("dashboard")
        member_details = member_info.get("data", {}).get("action", {}).get("details", {})

        if not dashboard_data or not member_details:
            raise ValueError("Missing required dashboard data")

        member_id = member_details.get("memberId")
        if not member_id:
            raise ValueError("Missing member ID in dashboard response")

        # Update state through StateManager validation
        state_update = {
            "member_id": member_id,  # SINGLE SOURCE OF TRUTH
            "flow_data": {
                "data": {
                    "dashboard": dashboard_data,
                    "member": member_details
                }
            }
        }

        # Let StateManager validate and update
        success, error = state_manager.update_state(state_update)
        if not success:
            raise StateException(f"Failed to update state: {error}")

        # Setup default account if needed
        if not state_manager.get("active_account_id"):
            setup_default_account(state_manager, dashboard_data)

        logger.info("Successfully processed dashboard response")
        return True

    except Exception as e:
        error_context = ErrorContext(
            error_type="state",
            message=str(e),
            details={
                "operation": "process_dashboard",
                "error_message": str(e)
            }
        )
        ErrorHandler.handle_error(e, state_manager, error_context)
        return False
