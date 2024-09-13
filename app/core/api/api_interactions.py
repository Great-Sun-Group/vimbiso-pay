import logging
import requests
import json
from decouple import config
from ..utils.utils import CredexWhatsappService
from django.core.cache import cache
import os
import base64

logger = logging.getLogger(__name__)

class APIInteractions:
    def __init__(self, bot_service):
        self.bot_service = bot_service
        self.env = os.getenv('ENV', 'dev')  # Default to 'dev' if not set
        self.base_url = f"{config('MYCREDEX_APP_URL')}api/v1"
        logger.info(f"Base URL: {self.base_url}")

    def refresh_member_info(self, reset=True, silent=True, init=False):
        """Refreshes member info by making an API call to CredEx"""
        logger.info("Refreshing member info")
        state = self.bot_service.state
        current_state = state.get_state(self.bot_service.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        url = f"{self.base_url}/getMemberDashboardByPhone"
        payload = json.dumps({"phone": self.bot_service.message['from']})
        headers = self._get_headers()

        try:
            self._handle_reset_and_init(reset, silent, init)
            response = self._make_api_request(url, headers, payload)
            response_data = self._process_api_response(response)
            self._update_current_state(response_data, current_state, reset)
            return self._handle_successful_refresh(current_state, state)
        except Exception as e:
            logger.exception(f"Error during refresh: {str(e)}")
            return self._handle_failed_refresh(current_state, state, str(e))

    def login(self):
        """Sends a login request to the CredEx API"""
        logger.info("Attempting to login")
        url = f"{self.base_url}/member/login"
        logger.info(f"Login URL: {url}")
        payload = json.dumps({"phone": self.bot_service.user.mobile_number})
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self._get_basic_auth_header(self.bot_service.user.mobile_number)
        }

        try:
            response = self._make_api_request(url, headers, payload)
            if response.status_code == 200:
                response_data = response.json()
                token = response_data.get('token')
                if token:
                    self.bot_service.user.jwt_token = token
                    self.bot_service.user.save()
                    logger.info("Login successful")
                    return True, "Login successful"
                else:
                    logger.error("Login response didn't contain a token")
                    return False, "Login failed: No token received"
            elif response.status_code == 400:
                logger.info("Login failed: New user or invalid phone")
                return False, "Welcome! It looks like you're new here. Let's get you set up."
            elif response.status_code == 401:
                logger.error(f"Login failed: Unauthorized. Response content: {response.text}")
                return False, "Login failed: Unauthorized. Please check your credentials."
            else:
                logger.error(f"Unexpected status code: {response.status_code}. Response content: {response.text}")
                return False, f"Login failed: Unexpected error (status code: {response.status_code})"
        except Exception as e:
            logger.exception(f"Error during login: {str(e)}")
            return False, f"Login failed: {str(e)}"

    def _get_basic_auth_header(self, phone_number):
        credentials = f"{phone_number}:{phone_number}"
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        return f"Basic {encoded_credentials}"

    def _get_headers(self):
        headers = {
            'Content-Type': 'application/json',
            'WHATSAPP_BOT_API_KEY': config('WHATSAPP_BOT_API_KEY'),
        }
        
        # Add JWT token if available
        if hasattr(self.bot_service.user, 'jwt_token') and self.bot_service.user.jwt_token:
            headers['Authorization'] = f"Bearer {self.bot_service.user.jwt_token}"

        # Add X-Github-Token only for dev environment and if it's set
        if self.env == 'dev' and config('X_GITHUB_TOKEN', default=None):
            headers['X-Github-Token'] = config('X_GITHUB_TOKEN')

        return headers

    def _handle_reset_and_init(self, reset, silent, init):
        if reset and not silent or init:
            self._send_delay_message()
            self._send_first_message()

    def _send_delay_message(self):
        if self.bot_service.state.stage != "handle_action_register" and not cache.get(f"{self.bot_service.user.mobile_number}_interracted"):
            CredexWhatsappService(payload={
                "messaging_product": "whatsapp",
                "preview_url": False,
                "recipient_type": "individual",
                "to": self.bot_service.user.mobile_number,
                "type": "text",
                "text": {"body": "Please wait while we process your request..."}
            }).send_message()
            cache.set(f"{self.bot_service.user.mobile_number}_interracted", True, 60*15)

    def _send_first_message(self):
        # Instead of fetching from the database, we'll use a hardcoded message
        first_message = "Welcome to CredEx! How can I assist you today?"
        CredexWhatsappService(payload={
            "messaging_product": "whatsapp",
            "preview_url": False,
            "recipient_type": "individual",
            "to": self.bot_service.user.mobile_number,
            "type": "text",
            "text": {"body": first_message}
        }).send_message()

    def _make_api_request(self, url, headers, payload):
        logger.info(f"Sending API request to: {url}")
        logger.info(f"Headers: {headers}")
        logger.info(f"Payload: {payload}")
        response = requests.request("POST", url, headers=headers, data=payload)
        logger.info(f"API Response Status Code: {response.status_code}")
        logger.info(f"API Response Headers: {response.headers}")
        logger.info(f"API Response Content: {response.text[:500]}...")  # Log only the first 500 characters
        return response

    def _process_api_response(self, response):
        if response.status_code != 200:
            raise requests.exceptions.RequestException(f"API returned status code {response.status_code}")

        content_type = response.headers.get('Content-Type', '')
        if 'application/json' not in content_type:
            raise ValueError(f"Received unexpected Content-Type: {content_type}")

        return response.json()

    def _update_current_state(self, response_data, current_state, reset):
        if reset:
            current_state['member'] = response_data
        else:
            current_state['member'].update(response_data)
        logger.info("Current state updated")

    def _handle_successful_refresh(self, current_state, state):
        logger.info("Refresh successful")
        state.update_state(
            state=current_state,
            stage='handle_action_select_profile',
            update_from="refresh",
            option="select_account_to_use"
        )
        return self.bot_service.action_handler.handle_action_select_profile()

    def _handle_failed_refresh(self, current_state, state, error_message):
        logger.error(f"Refresh failed: {error_message}")
        state.update_state(
            state=current_state,
            stage='handle_action_register',
            update_from="refresh",
            option="handle_action_register"
        )
        return self.bot_service.utils.wrap_text(f"An error occurred: {error_message}. Please try again.", 
                                                self.bot_service.user.mobile_number, 
                                                extra_rows=[{"id": '1', "title": "Become a member"}], 
                                                include_menu=False)