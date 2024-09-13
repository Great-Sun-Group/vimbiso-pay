import logging
from bot.utils import CredexWhatsappService, wrap_text
from bot.action_handlers import ActionHandler
from bot.offer_credex_handler import OfferCredexHandler
from bot.constants import *
import requests
import json
from decouple import config
from bot.models import Message
from django.core.cache import cache
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CredexBotService:
    def __init__(self, payload, user: object = None) -> None:
        if user is None:
            logger.error("User object is required")
            raise ValueError("User object is required")
        
        self.message = payload
        self.user = user
        self.body = self.message.get('message', '')

        self.state = self.user.state
        self.current_state = self.state.get_state(self.user)
        if not isinstance(self.current_state, dict):
            self.current_state = self.current_state.state

        self.action_handler = ActionHandler(self)
        self.offer_credex_handler = OfferCredexHandler(self)

        try:
            self.response = self.handle()
        except Exception as e:
            logger.exception(f"Error in CredexBotService: {str(e)}")
            self.response = wrap_text(INVALID_ACTION, self.user.mobile_number)

    def handle(self):
        logger.info(f"Initial state: {self.state.stage}")
        if self.body is None:
            logger.warning("Empty message body received")
            return self.action_handler.handle_default_action()

        if "=>" in f"{self.body}" or "->" in f"{self.body}":
            logger.info("Handling offer credex action")
            self.state.update_state(self.current_state, "handle_action_offer_credex", "handle", "handle_action_offer_credex")
            return self.offer_credex_handler.handle_action_offer_credex()
        
        if f"{self.body}".startswith("handle_action_"):
            action_method = getattr(self.action_handler, self.body, None)
            if action_method and callable(action_method):
                logger.info(f"Handling action: {self.body}")
                self.state.update_state(self.current_state, self.body, "handle", self.body)
                return action_method()
            else:
                logger.warning(f"Action method {self.body} not found")
                return self.action_handler.handle_default_action()
        
        # Handle greetings
        if f"{self.body}".lower() in GREETINGS:
            logger.info("Handling greeting")
            self.state.update_state(self.current_state, "handle_action_select_profile", "handle", "handle_greeting")
            return self.action_handler.handle_greeting()
        
        # Add other routing logic here
        
        logger.info("Handling default action")
        response = self.action_handler.handle_default_action()
        logger.info(f"Final state: {self.state.stage}")
        return response

    def refresh(self, reset=True, silent=True, init=False):
        """THIS METHOD REFRESHES MEMBER INFO BY MAKING AN API CALL TO CREDEX CALL"""
        logger.info("Refreshing member info")
        state = self.user.state
        current_state = state.get_state(self.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        url = f"{config('CREDEX')}/getMemberDashboardByPhone"
        logger.info(f"API URL: {url}")

        payload = json.dumps({
            "phone": self.message['from']
        })
        logger.info(f"Payload: {payload}")

        headers = {
            'X-Github-Token': config('X_GITHUB_TOKEN'),
            'Content-Type': 'application/json',
            'WHATSAPP_BOT_API_KEY': config('WHATSAPP_BOT_API_KEY'),
            'Authorization': config('JWT_AUTH')
        }
        logger.info(f"Headers: {headers}")

        try:
            if reset and silent == False or init:
                if state.stage != "handle_action_register" and not cache.get(f"{self.user.mobile_number}_interracted"):
                    CredexWhatsappService(payload={
                        "messaging_product": "whatsapp",
                        "preview_url": False,
                        "recipient_type": "individual",
                        "to": self.user.mobile_number,
                        "type": "text",
                        "text": {
                            "body": DELAY
                        }
                    }).send_message()
                    cache.set(f"{self.user.mobile_number}_interracted", True, 60*15)

                message = Message.objects.all().first()
                if message:
                    CredexWhatsappService(payload={
                        "messaging_product": "whatsapp",
                        "preview_url": False,
                        "recipient_type": "individual",
                        "to": self.user.mobile_number,
                        "type": "text",
                        "text": {
                            "body": message.messsage
                        }
                    }).send_message()
        
            logger.info("Sending API request")
            response = requests.request("GET", url, headers=headers, data=payload)
            logger.info(f"API Response Status Code: {response.status_code}")
            logger.info(f"API Response Headers: {response.headers}")
            logger.info(f"API Response Content: {response.text[:500]}...")  # Log only the first 500 characters

            if response.status_code != 200:
                raise requests.exceptions.RequestException(f"API returned status code {response.status_code}")

            content_type = response.headers.get('Content-Type', '')
            if 'application/json' not in content_type:
                raise ValueError(f"Received unexpected Content-Type: {content_type}")

            response_data = response.json()
            if 'member' not in current_state:
                current_state['member'] = {}
            current_state['member'].update(response_data)
            self._update_current_state(response_data, current_state, reset)
            return self._handle_successful_refresh(current_state, state)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error during API call: {str(e)}")
            return self._handle_failed_refresh(current_state, state, f"Failed to connect to the server: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {str(e)}")
            return self._handle_failed_refresh(current_state, state, "Received invalid data from the server. Please try again later.")
        except ValueError as e:
            logger.error(f"Unexpected response format: {str(e)}")
            return self._handle_failed_refresh(current_state, state, f"Unexpected response from server: {str(e)}")
        except Exception as e:
            logger.exception(f"Unexpected error during refresh: {str(e)}")
            return self._handle_failed_refresh(current_state, state, "An unexpected error occurred. Please try again later.")

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
        return self.action_handler.handle_action_select_profile()

    def _handle_failed_refresh(self, current_state, state, error_message):
        logger.error(f"Refresh failed: {error_message}")
        state.update_state(
            state=current_state,
            stage='handle_action_register',
            update_from="refresh",
            option="handle_action_register"
        )
        return wrap_text(REGISTER.format(message=error_message), self.user.mobile_number, extra_rows=[{"id": '1', "title": "Become a member"}], include_menu=False)

    # Other core methods that don't fit into specific handlers