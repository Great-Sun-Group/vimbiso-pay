import logging
from typing import Tuple, Dict, Any
from .base_client import BaseAPIClient

logger = logging.getLogger(__name__)


class CredexClient(BaseAPIClient):
    """Handles CredEx-specific API operations"""

    def offer_credex(self, payload: Dict[str, Any], jwt_token: str) -> Tuple[bool, Dict[str, Any]]:
        """Sends an offer to the CredEx API"""
        logger.info("Attempting to offer CredEx")
        payload = payload.copy()
        payload.pop("full_name", None)

        url = f"{self.base_url}/createCredex"
        logger.info(f"Offer URL: {url}")

        headers = self._get_headers(jwt_token)
        try:
            response = self._make_api_request(url, headers, payload)
            return self._handle_response(response, "CREDEX_CREATED")
        except Exception as e:
            logger.exception(f"Error during offer: {str(e)}")
            return False, {"error": str(e)}

    def accept_bulk_credex(self, payload: Dict[str, Any], jwt_token: str) -> Tuple[bool, Dict[str, Any]]:
        """Accepts multiple CredEx offers"""
        logger.info("Attempting to accept multiple CredEx offers")
        url = f"{self.base_url}/acceptCredexBulk"
        logger.info(f"Accept URL: {url}")

        headers = self._get_headers(jwt_token)
        try:
            response = self._make_api_request(url, headers, payload)
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("summary", {}).get("accepted"):
                    logger.info("Accept successful")
                    return True, response_data
                else:
                    logger.error("Accept failed")
                    return False, {"error": response_data.get("error")}
            return self._handle_response(response)
        except Exception as e:
            logger.exception(f"Error during bulk accept: {str(e)}")
            return False, {"error": str(e)}

    def accept_credex(self, payload: Dict[str, Any], jwt_token: str) -> Tuple[bool, Dict[str, Any]]:
        """Accepts a CredEx offer"""
        logger.info("Attempting to accept CredEx")
        url = f"{self.base_url}/acceptCredex"
        logger.info(f"Accept URL: {url}")

        headers = self._get_headers(jwt_token)
        try:
            response = self._make_api_request(url, headers, payload)
            return self._handle_response(response, "CREDEX_ACCEPTED")
        except Exception as e:
            logger.exception(f"Error during accept: {str(e)}")
            return False, {"error": str(e)}

    def decline_credex(self, payload: Dict[str, Any], jwt_token: str) -> Tuple[bool, str]:
        """Declines a CredEx offer"""
        logger.info("Attempting to decline CredEx")
        url = f"{self.base_url}/declineCredex"
        logger.info(f"Decline URL: {url}")

        headers = self._get_headers(jwt_token)
        try:
            response = self._make_api_request(url, headers, payload)
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("status") == "success":
                    logger.info("Decline successful")
                    return True, "Decline successful"
                else:
                    logger.error("Decline failed")
                    return False, response_data.get("error", "Unknown error")
            return self._handle_response(response)
        except Exception as e:
            logger.exception(f"Error during decline: {str(e)}")
            return False, str(e)

    def cancel_credex(self, payload: Dict[str, Any], jwt_token: str) -> Tuple[bool, str]:
        """Cancels a CredEx offer"""
        logger.info("Attempting to cancel CredEx")
        url = f"{self.base_url}/cancelCredex"
        logger.info(f"Cancel URL: {url}")

        headers = self._get_headers(jwt_token)
        try:
            response = self._make_api_request(url, headers, payload)
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("message") == "Credex cancelled successfully":
                    logger.info("Cancel successful")
                    return True, "Credex cancelled successfully"
                else:
                    logger.error("Cancel failed")
                    return False, response_data.get("error", "Unknown error")
            return self._handle_response(response)
        except Exception as e:
            logger.exception(f"Error during cancel: {str(e)}")
            return False, str(e)

    def get_credex(self, payload: Dict[str, Any], jwt_token: str) -> Tuple[bool, Dict[str, Any]]:
        """Fetches a specific CredEx offer"""
        logger.info("Fetching credex")
        url = f"{self.base_url}/getCredex"
        logger.info(f"Credex URL: {url}")

        headers = self._get_headers(jwt_token)
        try:
            response = self._make_api_request(url, headers, payload)
            return self._handle_response(response)
        except Exception as e:
            logger.exception(f"Error during credex fetch: {str(e)}")
            return False, {"error": str(e)}
