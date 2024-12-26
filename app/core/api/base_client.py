import logging
import base64
from typing import Tuple, Dict, Any, Optional
import requests
from decouple import config

logger = logging.getLogger(__name__)


class BaseAPIClient:
    """Base class for API client operations"""

    def __init__(self):
        self.base_url = f"{config('MYCREDEX_APP_URL')}"
        logger.info(f"Base URL: {self.base_url}")

    def _make_api_request(self, url: str, headers: Dict[str, str], payload: Dict[str, Any],
                          method: str = "POST", login: bool = False) -> requests.Response:
        """Make an API request with proper logging and error handling"""
        logger.info(f"Sending API request to: {url}")
        logger.info(f"Headers: {headers}")
        logger.info(f"Payload: {payload}")

        response = requests.request(method, url, headers=headers, json=payload)
        logger.info(f"API Response Status Code: {response.status_code}")
        logger.info(f"API Response Headers: {response.headers}")
        logger.info(f"API Response Content: {response.text[:500]}...")  # Log first 500 chars
        return response

    def _process_api_response(self, response: requests.Response) -> Dict[str, Any]:
        """Process API response and handle content type validation"""
        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            raise ValueError(f"Received unexpected Content-Type: {content_type}")
        return response.json()

    def _get_headers(self, jwt_token: Optional[str] = None) -> Dict[str, str]:
        """Get headers for API requests"""
        headers = {
            "Content-Type": "application/json",
            "x-client-api-key": config("CLIENT_API_KEY"),
        }
        if jwt_token:
            headers["Authorization"] = f"Bearer {jwt_token}"
        return headers

    @staticmethod
    def _get_basic_auth_header(phone_number: str) -> str:
        """Generate basic auth header from phone number"""
        credentials = f"{phone_number}:{phone_number}"
        encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        return f"Basic {encoded_credentials}"

    def _handle_response(self, response: requests.Response,
                         success_key: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """Generic response handler for API calls"""
        try:
            if response.status_code == 200:
                response_data = response.json()
                if success_key:
                    success = response_data.get("data", {}).get("action", {}).get("type") == success_key
                else:
                    success = True
                return success, response_data
            elif response.status_code == 400:
                return False, {"error": response.json().get("message", "Bad request")}
            elif response.status_code == 401:
                return False, {"error": "Unauthorized"}
            else:
                return False, {"error": f"Unexpected error (status code: {response.status_code})"}
        except Exception as e:
            logger.exception(f"Error processing response: {str(e)}")
            return False, {"error": str(e)}
