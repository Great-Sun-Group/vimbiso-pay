"""CredEx operations"""
import logging
from typing import Any, Dict, Tuple

from .base import BaseAPIClient
from .profile import ProfileManager

logger = logging.getLogger(__name__)


class CredExManager(BaseAPIClient):
    """Handles CredEx operations"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile_manager = ProfileManager(*args, **kwargs)

    def offer_credex(self, offer_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Create a new CredEx offer"""
        logger.info("Attempting to offer CredEx")
        url = f"{self.base_url}/createCredex"
        logger.info(f"Offer URL: {url}")

        # Remove any extra fields
        offer_data.pop("full_name", None)

        headers = self._get_headers()
        try:
            response = self._make_api_request(url, headers, offer_data)
            if response.status_code == 200:
                response_data = response.json()

                if (
                    response_data.get("data", {}).get("action", {}).get("type")
                    == "CREDEX_CREATED"
                ):
                    # Add success message and status to response
                    if "data" not in response_data:
                        response_data["data"] = {}
                    if "action" not in response_data["data"]:
                        response_data["data"]["action"] = {}
                    response_data["data"]["action"].update({
                        "message": "CredEx offer created successfully",
                        "status": "success"
                    })

                    # Update profile and state
                    self.profile_manager.update_profile_from_response(
                        response_data,
                        "credex_offer",
                        "credex_offer"
                    )

                    # Return success response with message
                    return True, response_data
                else:
                    logger.error("Offer failed")
                    return False, {"error": response_data.get("error")}

            else:
                return self._handle_error_response(
                    "Offer",
                    response,
                    f"Offer failed: Unexpected error (status code: {response.status_code})"
                )

        except Exception as e:
            logger.exception(f"Error during offer: {str(e)}")
            return False, {"error": f"Offer failed: {str(e)}"}

    def accept_credex(self, credex_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Accept a CredEx offer"""
        logger.info("Attempting to accept CredEx")
        url = f"{self.base_url}/acceptCredex"
        logger.info(f"Accept URL: {url}")

        payload = {"credexID": credex_id}
        headers = self._get_headers()

        try:
            response = self._make_api_request(url, headers, payload)
            if response.status_code == 200:
                response_data = response.json()
                if (
                    response_data.get("data", {}).get("action", {}).get("type")
                    == "CREDEX_ACCEPTED"
                ):
                    # Update profile and state
                    self.profile_manager.update_profile_from_response(
                        response_data,
                        "credex_accept",
                        "credex_accept"
                    )
                    logger.info("Accept successful")
                    return True, response_data
                else:
                    logger.error("Accept failed")
                    return False, {"error": response_data.get("error")}

            else:
                return self._handle_error_response(
                    "Accept",
                    response,
                    f"Accept failed: Unexpected error (status code: {response.status_code})"
                )

        except Exception as e:
            logger.exception(f"Error during accept: {str(e)}")
            return False, {"error": f"Accept failed: {str(e)}"}

    def decline_credex(self, credex_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Decline a CredEx offer"""
        logger.info("Attempting to decline CredEx")
        url = f"{self.base_url}/declineCredex"
        logger.info(f"Decline URL: {url}")

        payload = {"credexID": credex_id}
        headers = self._get_headers()

        try:
            response = self._make_api_request(url, headers, payload)
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("status") == "success":
                    # Update profile and state
                    self.profile_manager.update_profile_from_response(
                        response_data,
                        "credex_decline",
                        "credex_decline"
                    )
                    logger.info("Decline successful")
                    return True, {"message": "Decline successful"}
                else:
                    logger.error("Decline failed")
                    return False, {"error": response_data.get("error")}

            else:
                return self._handle_error_response(
                    "Decline",
                    response,
                    f"Decline failed: Unexpected error (status code: {response.status_code})"
                )

        except Exception as e:
            logger.exception(f"Error during decline: {str(e)}")
            return False, {"error": f"Decline failed: {str(e)}"}

    def cancel_credex(self, credex_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Cancel a CredEx offer"""
        logger.info("Attempting to cancel CredEx")
        url = f"{self.base_url}/cancelCredex"
        logger.info(f"Cancel URL: {url}")

        payload = {"credexID": credex_id}
        headers = self._get_headers()

        try:
            response = self._make_api_request(url, headers, payload)
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("message") == "Credex cancelled successfully":
                    # Update profile and state
                    self.profile_manager.update_profile_from_response(
                        response_data,
                        "credex_cancel",
                        "credex_cancel"
                    )
                    logger.info("Cancel successful")
                    return True, {"message": "Credex cancelled successfully"}
                else:
                    logger.error("Cancel failed")
                    return False, {"error": response_data.get("error")}

            else:
                return self._handle_error_response(
                    "Cancel",
                    response,
                    f"Cancel failed: Unexpected error (status code: {response.status_code})"
                )

        except Exception as e:
            logger.exception(f"Error during cancel: {str(e)}")
            return False, {"error": f"Cancel failed: {str(e)}"}

    def get_credex(self, credex_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Get details of a specific CredEx"""
        logger.info("Fetching credex details")
        url = f"{self.base_url}/getCredex"
        logger.info(f"Credex URL: {url}")

        payload = {"credexID": credex_id}
        headers = self._get_headers()

        try:
            response = self._make_api_request(url, headers, payload)
            if response.status_code == 200:
                response_data = response.json()
                # Update profile and state
                self.profile_manager.update_profile_from_response(
                    response_data,
                    "credex_fetch",
                    "credex_fetch"
                )
                logger.info("Credex fetched successfully")
                return True, response_data

            else:
                return self._handle_error_response(
                    "Credex fetch",
                    response,
                    f"Credex fetch failed: Unexpected error (status code: {response.status_code})"
                )

        except Exception as e:
            logger.exception(f"Error during credex fetch: {str(e)}")
            return False, {"error": f"Credex fetch failed: {str(e)}"}

    def accept_bulk_credex(self, credex_ids: list) -> Tuple[bool, Dict[str, Any]]:
        """Accept multiple CredEx offers"""
        logger.info("Attempting to accept multiple CredEx offers")
        url = f"{self.base_url}/acceptCredexBulk"
        logger.info(f"Accept URL: {url}")

        payload = {"credexIDs": credex_ids}
        headers = self._get_headers()

        try:
            response = self._make_api_request(url, headers, payload)
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("summary", {}).get("accepted"):
                    # Update profile and state
                    self.profile_manager.update_profile_from_response(
                        response_data,
                        "credex_bulk_accept",
                        "credex_bulk_accept"
                    )
                    logger.info("Bulk accept successful")
                    return True, response_data
                else:
                    logger.error("Bulk accept failed")
                    return False, {"error": response_data.get("error")}

            else:
                return self._handle_error_response(
                    "Bulk accept",
                    response,
                    f"Bulk accept failed: Unexpected error (status code: {response.status_code})"
                )

        except Exception as e:
            logger.exception(f"Error during bulk accept: {str(e)}")
            return False, {"error": f"Bulk accept failed: {str(e)}"}
