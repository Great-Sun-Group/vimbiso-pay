import logging
import requests
import json
from decouple import config
from ..utils.utils import CredexWhatsappService
from django.core.cache import cache

logger = logging.getLogger(__name__)

class APIInteractions:
    def __init__(self, bot_service):
        self.bot_service = bot_service

    def refresh_member_info(self, reset=True, silent=True, init=False):
        """Refreshes member info by making an API call to CredEx"""
        logger.info("Refreshing member info")
        state = self.bot_service.state
        current_state = state.get_state(self.bot_service.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        url = f"{config('CREDEX')}/getMemberDashboardByPhone"
        payload = json.dumps({"phone": self.bot_service.message['from']})
        headers = {
            'X-Github-Token': config('X_GITHUB_TOKEN'),
            'Content-Type': 'application/json',
            'WHATSAPP_BOT_API_KEY': config('WHATSAPP_BOT_API_KEY'),
            'Authorization': config('JWT_AUTH')
        }

        try:
            self._handle_reset_and_init(reset, silent, init)
            response = self._make_api_request(url, headers, payload)
            response_data = self._process_api_response(response)
            self._update_current_state(response_data, current_state, reset)
            return self._handle_successful_refresh(current_state, state)
        except Exception as e:
            logger.exception(f"Error during refresh: {str(e)}")
            return self._handle_failed_refresh(current_state, state, str(e))

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
        logger.info("Sending API request")
        response = requests.request("GET", url, headers=headers, data=payload)
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