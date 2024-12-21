"""Dashboard and member operations"""
import logging
from typing import Dict, Any, Tuple, Optional

from .base import BaseAPIClient
from .profile import ProfileManager

logger = logging.getLogger(__name__)


class DashboardManager(BaseAPIClient):
    """Handles dashboard and member operations"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile_manager = ProfileManager(*args, **kwargs)

    def get_dashboard(self) -> Tuple[bool, Dict[str, Any]]:
        """Fetch member's dashboard"""
        logger.info("Fetching member dashboard")
        url = f"{self.base_url}/getMemberDashboardByPhone"
        logger.info(f"Dashboard URL: {url}")

        payload = {"phone": self.bot_service.user.mobile_number}
        headers = self._get_headers()

        try:
            response = self._make_api_request(url, headers, payload, login=False)
            if response.status_code == 200:
                response_data = response.json()
                # Get current state
                current_state = self.profile_manager._get_current_state()

                # Add current state's action data to response to preserve it
                if "data" not in response_data:
                    response_data["data"] = {}
                if "action" not in response_data["data"]:
                    response_data["data"]["action"] = {}

                # Preserve existing action data
                current_action = current_state.get("profile", {}).get("action", {})
                response_data["data"]["action"].update({
                    "message": current_action.get("message", ""),
                    "status": current_action.get("status", ""),
                    "type": current_action.get("type", "dashboard_fetch")
                })

                # Structure profile data from dashboard response
                profile_data = self.profile_manager._structure_profile_data(
                    response_data,
                    "dashboard_fetch"
                )

                logger.info("Dashboard fetched successfully")
                return True, {
                    "data": {
                        "dashboard": profile_data["dashboard"],
                        "action": profile_data["action"]
                    }
                }

            elif response.status_code == 401:
                # Try to refresh token and retry
                from .auth import AuthManager
                auth_manager = AuthManager(self.bot_service)
                success, _ = auth_manager.login()
                if success:
                    response = self._make_api_request(url, headers, payload)
                    if response.status_code == 200:
                        response_data = response.json()
                        # Get current state
                        current_state = self.profile_manager._get_current_state()

                        # Add current state's action data to response to preserve it
                        if "data" not in response_data:
                            response_data["data"] = {}
                        if "action" not in response_data["data"]:
                            response_data["data"]["action"] = {}

                        # Preserve existing action data
                        current_action = current_state.get("profile", {}).get("action", {})
                        response_data["data"]["action"].update({
                            "message": current_action.get("message", ""),
                            "status": current_action.get("status", ""),
                            "type": current_action.get("type", "dashboard_fetch")
                        })

                        # Structure profile data from dashboard response
                        profile_data = self.profile_manager._structure_profile_data(
                            response_data,
                            "dashboard_fetch"
                        )

                        logger.info("Dashboard fetched successfully after reauth")
                        return True, {
                            "data": {
                                "dashboard": profile_data["dashboard"],
                                "action": profile_data["action"]
                            }
                        }

                return self._handle_error_response(
                    "Dashboard fetch",
                    response,
                    "Dashboard fetch failed: Unauthorized"
                )

            else:
                return self._handle_error_response(
                    "Dashboard fetch",
                    response,
                    f"Dashboard fetch failed: Unexpected error (status code: {response.status_code})"
                )

        except Exception as e:
            logger.exception(f"Error during dashboard fetch: {str(e)}")
            return False, {"message": f"Dashboard fetch failed: {str(e)}"}

    def refresh_member_info(
        self,
        reset: bool = True,
        silent: bool = True,
        init: bool = False
    ) -> Optional[str]:
        """Refresh member information"""
        logger.info("Refreshing member info")

        # Get current state
        current_state = self.profile_manager._get_current_state()

        # Handle initialization messages
        self._handle_reset_and_init(reset, silent, init)

        try:
            url = f"{self.base_url}/getMemberDashboardByPhone"
            payload = {"phone": self.bot_service.message["from"]}
            headers = self._get_headers()

            response = self._make_api_request(url, headers, payload)
            response_data = self._process_api_response(response)

            if (
                "Member not found" in response_data.get("message", "")
                or "Could not retrieve member dashboard" in response_data.get("message", "")
                or "Invalid token" in response_data.get("message", "")
            ):
                return "Member not found or invalid token"

            # Handle successful refresh
            return self.profile_manager.handle_successful_refresh(
                response_data,
                current_state
            )

        except Exception as e:
            logger.exception(f"Error during refresh: {str(e)}")
            return str(e)

    def validate_handle(self, handle: str) -> Tuple[bool, Dict[str, Any]]:
        """Validate member handle"""
        logger.info(f"Validating handle: {handle}")
        url = f"{self.base_url}/getAccountByHandle"
        logger.info(f"Handle validation URL: {url}")

        payload = {"accountHandle": handle.lower()}
        headers = self._get_headers()

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
                return self._handle_error_response(
                    "Handle validation",
                    response,
                    f"Handle validation failed: Unexpected error (status code: {response.status_code})"
                )

        except Exception as e:
            logger.exception(f"Error during handle validation: {str(e)}")
            return False, {"error": f"Handle validation failed: {str(e)}"}

    def get_ledger(self, payload: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Get member's transaction ledger"""
        logger.info("Fetching ledger")
        url = f"{self.base_url}/getLedger"
        logger.info(f"Ledger URL: {url}")

        headers = self._get_headers()
        try:
            response = self._make_api_request(url, headers, payload)
            if response.status_code == 200:
                response_data = response.json()
                # Structure profile data from get ledger response
                self.profile_manager.update_profile_from_response(
                    response_data,
                    "ledger_fetch",
                    "ledger_fetch"
                )
                logger.info("Ledger fetched successfully")
                return True, response_data

            else:
                return self._handle_error_response(
                    "Ledger fetch",
                    response,
                    f"Ledger fetch failed: Unexpected error (status code: {response.status_code})"
                )

        except Exception as e:
            logger.exception(f"Error during ledger fetch: {str(e)}")
            return False, {"error": f"Ledger fetch failed: {str(e)}"}
