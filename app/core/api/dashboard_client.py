import logging
from typing import Tuple, Dict, Any, Optional
from .base_client import BaseAPIClient

logger = logging.getLogger(__name__)


class DashboardClient(BaseAPIClient):
    """Handles dashboard-related API operations"""

    def get_dashboard(self, phone_number: str, jwt_token: str) -> Tuple[bool, Dict[str, Any]]:
        """Fetches the member's dashboard from the CredEx API"""
        logger.info("Fetching member dashboard")
        url = f"{self.base_url}/getMemberDashboardByPhone"
        logger.info(f"Dashboard URL: {url}")

        payload = {"phone": phone_number}
        headers = self._get_headers(jwt_token)

        try:
            response = self._make_api_request(url, headers, payload, login=False)
            return self._handle_response(response)
        except Exception as e:
            logger.exception(f"Error during dashboard fetch: {str(e)}")
            return False, {"message": f"Dashboard fetch failed: {str(e)}"}

    def validate_handle(self, handle: str, jwt_token: str) -> Tuple[bool, Dict[str, Any]]:
        """Validates a handle by making an API call to CredEx"""
        logger.info(f"Validating handle: {handle}")
        url = f"{self.base_url}/getAccountByHandle"
        logger.info(f"Handle validation URL: {url}")

        payload = {"accountHandle": handle.lower()}
        headers = self._get_headers(jwt_token)

        try:
            response = self._make_api_request(url, headers, payload, method="POST")
            if response.status_code == 200:
                response_data = response.json()
                if not response_data.get("Error"):
                    logger.info("Handle validation successful")
                    return True, response_data
                else:
                    logger.error("Handle validation failed")
                    return False, response_data
            else:
                logger.error(f"Handle validation failed with status: {response.status_code}")
                return False, {"error": f"Unexpected error (status code: {response.status_code})"}
        except Exception as e:
            logger.exception(f"Error during handle validation: {str(e)}")
            return False, {"error": str(e)}

    def get_ledger(self, payload: Dict[str, Any], jwt_token: str) -> Tuple[bool, Dict[str, Any]]:
        """Fetches ledger information"""
        logger.info("Fetching ledger")
        url = f"{self.base_url}/getLedger"
        logger.info(f"Ledger URL: {url}")

        headers = self._get_headers(jwt_token)
        try:
            response = self._make_api_request(url, headers, payload)
            return self._handle_response(response)
        except Exception as e:
            logger.exception(f"Error during ledger fetch: {str(e)}")
            return False, {"error": f"Ledger fetch failed: {str(e)}"}

    def process_dashboard_response(
            self, current_state: Dict[str, Any],
            member_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process and update dashboard response data"""
        logger.info("Processing dashboard response")

        if not isinstance(member_info, dict):
            logger.error("Invalid member_info format")
            return None

        dashboard_data = member_info.get("data", {}).get("dashboard")
        member_details = member_info.get("data", {}).get("action", {}).get("details", {})

        if not dashboard_data or not member_details:
            logger.error("Missing required dashboard data")
            return None

        member_id = member_details.get("memberId")
        if not member_id:
            logger.error("Missing member ID in dashboard response")
            return None

        member_info = {
            "member": member_details,
            "memberDashboard": dashboard_data,
        }

        jwt_token = current_state.get("jwt_token")
        if jwt_token:
            member_info["jwt_token"] = jwt_token

        current_state["profile"] = member_info
        current_state["member_id"] = member_id

        if not current_state.get("current_account", {}):
            self._setup_default_account(current_state, dashboard_data)

        return current_state

    def _setup_default_account(
            self, current_state: Dict[str, Any],
            dashboard_data: Dict[str, Any]) -> None:
        """Setup default account for the user if eligible"""
        member_tier = (
            dashboard_data.get("memberTier", {}).get("low", 1)
            if isinstance(dashboard_data.get("memberTier"), dict)
            else 1
        )

        accounts = dashboard_data.get("accounts", [])
        if member_tier < 2 and accounts and isinstance(accounts, list) and accounts:
            try:
                first_account = accounts[0]
                if (
                    isinstance(first_account, dict)
                    and first_account.get("success")
                    and isinstance(first_account.get("data"), dict)
                ):
                    current_state["current_account"] = first_account["data"]
                    logger.info("Successfully set default account")
                else:
                    logger.error("Invalid account data structure")
                    current_state["current_account"] = {}
            except Exception as e:
                logger.error(f"Error setting default account: {str(e)}")
                current_state["current_account"] = {}
        else:
            current_state["current_account"] = {}
            logger.info("No eligible account found or member tier too high")
