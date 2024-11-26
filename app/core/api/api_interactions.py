import logging
import requests
import json
from decouple import config

from core.api.services import CredexBotService
from ..utils.utils import CredexWhatsappService, wrap_text
from django.core.cache import cache
import os
import base64
from typing import Tuple
from ..config.constants import *

logger = logging.getLogger(__name__)


class APIInteractions:
    def __init__(self, bot_service: CredexBotService):
        self.bot_service = bot_service
        self.env = config('ENV', 'dev')  # Default to 'dev' if not set
        self.base_url = f"{config('MYCREDEX_APP_URL_2')}"
        logger.info(f"Base URL: {self.base_url}")

    def refresh_dashboard(self):
        """Refreshes the member's dashboard"""
        logger.info("Refreshing dashboard")
        success, data = self.get_dashboard()
        if success:
            user = CachedUser(self.bot_service.user.mobile_number)
            current_state = user.state.get_state(user)

            if not isinstance(current_state, dict):
                current_state = current_state.state
            return self._handle_successful_refresh(current_state,data)


    def refresh_member_info(self, reset=True, silent=True, init=False):
        """Refreshes member info by making an API call to CredEx"""
        logger.info("Refreshing member info")

        user = CachedUser(self.bot_service.user.mobile_number)
        current_state = user.state.get_state(user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        # print("")
        url = f"{self.base_url}/getMemberDashboardByPhone"
        payload = {"phone": self.bot_service.message['from']}
        headers = self._get_headers()
        print("\n\n>>>>>>>>>>>>>>>>>>>\n\nHEADERS  >>>> ", headers, self.bot_service.user.state.jwt_token)

        self._handle_reset_and_init(reset, silent, init)
        try:
            response = self._make_api_request(url, headers, payload)
            print("####### RESPONSE ", response)
            response_data = self._process_api_response(response)
            print("####### RESPONSE DATA ", response_data)
            if "Member not found" in response_data.get('message', '') or "Could not retrieve member dashboard" in response_data.get('message', '') or "Invalid token" in response_data.get('message', ''):
                return self.bot_service.action_handler.handle_action_register(register=True)
            else:
                return self._handle_successful_refresh(current_state, member_info=response_data)


        except Exception as e:
            logger.exception(f"Error during refresh: {str(e)}")
            return self._handle_failed_refresh(current_state, str(e))

    def login(self):
        """Sends a login request to the CredEx API"""
        logger.info("Attempting to login")
        url = f"{self.base_url}/login"
        logger.info(f"Login URL: {url}")
        payload = {"phone": self.bot_service.user.mobile_number}
        headers = {
            'Content-Type': 'application/json',
            'x-client-api-key': config('WHATSAPP_BOT_API_KEY')
        }

        try:
            response = self._make_api_request(url, headers, payload)
            if response.status_code == 200:
                response_data = response.json()
                token = response_data.get('data', {}).get('action', {}).get('details', {}).get('token')
                if token:
                    self.bot_service.user.state.set_jwt_token(token)
                    logger.info(f"Login successful {token}")
                    return True, "Login successful"
                else:
                    logger.error("Login response didn't contain a token")
                    return False, "Login failed: No token received"
            elif response.status_code == 400:
                logger.info("Login failed: New user or invalid phone")
                return False, "*Welcome!* \n\nIt looks like you're new here. Let's get you \nset up."
            elif response.status_code == 401:
                logger.error(f"Login failed: Unauthorized. Response content: {response.text}")
                return False, "Login failed: Unauthorized. Please check your credentials."
            elif response.status_code == 404:
                logger.error(f"Login failed: Not found. Response content: {response.text}")
                print("RESPONSE TEXT ", response.json())
                return False, response.json()
            else:
                logger.error(f"Unexpected status code: {response.status_code}. Response content: {response.text}")
                return False, f"Login failed: Unexpected error (status code: {response.status_code})"
        except Exception as e:
            logger.exception(f"Error during login: {str(e)}")
            return False, f"Login failed: {str(e)}"

    def register_member(self, payload):
        """Sends a registration request to the CredEx API"""
        logger.info("Attempting to register member")

        url = f"{self.base_url}/onboardMember"
        logger.info(f"Register URL: {url}")

        headers = self._get_headers()
        try:
            response = self._make_api_request(url, headers, payload)
            if response.status_code == 201:
                response_data = response.json()
                print("REGISTRATION RESPONSE DATA ", response_data)
                if response_data.get("data", {}).get("action", {}).get("details", {}).get('token'):
                    self.bot_service.user.state.set_jwt_token(response_data.get('token'))
                    logger.info("Registration successful")
                    return True, "Registration successful"
                else:
                    logger.error("Registration response didn't contain a token")
                    return False, "Registration failed: No token received"
            elif response.status_code == 400:
                logger.error(f"Registration failed: Bad request. Response content: {response.json().get('message')}")
                return False, f"*Registration failed (400)*:\n\n{response.json().get('message')}"
            elif response.status_code == 401:
                logger.error(f"Registration failed: Unauthorized. Response content: {response.text}")
                return False, f"Registration failed: Unauthorized. {response.text}"
            else:
                logger.error(f"Unexpected status code: {response.status_code}. Response content: {response.text}")
                return False, f"Registration failed: Unexpected error (status code: {response.status_code})"
        except Exception as e:
            logger.exception(f"Error during registration: {str(e)}")
            return False, f"Registration failed: {str(e)}"

    def get_dashboard(self) -> Tuple[bool, dict]:
        """Fetches the member's dashboard from the CredEx API"""
        self.refresh_member_info(reset=True, silent=True, init=False)

        logger.info("Fetching member dashboard")
        url = f"{self.base_url}/getMemberDashboardByPhone"
        logger.info(f"Dashboard URL: {url}")

        payload = {"phone": self.bot_service.user.mobile_number}
        headers = self._get_headers()

        try:
            response = self._make_api_request(url, headers, payload, login=False)
            if response.status_code == 200:
                response_data = response.json()
                logger.info("Dashboard fetched successfully")
                return True, response_data
            elif response.status_code == 401:
                self.login()
                response = self._make_api_request(url, headers, payload)
                if response.status_code == 200:
                    response_data = response.json()
                    logger.info("Dashboard fetched successfully")
                    return True, response_data
                logger.error(f"Dashboard fetch failed: Unauthorized. Response content: {response.text}")
                return False, {"message": "Dashboard fetch failed: Unauthorized"}
            else:
                logger.error(f"Unexpected status code: {response.status_code}. Response content: {response.text}")
                return False, {"message": f"Dashboard fetch failed: Unexpected error (status code: {response.status_code})"}
        except Exception as e:
            logger.exception(f"Error during dashboard fetch: {str(e)}")
            return False, {"message": f"Dashboard fetch failed: {str(e)}"}

    def validate_handle(self, handle):
        """Validates a handle by making an API call to CredEx"""
        logger.info(f"Validating handle: {handle}")

        url = f"{self.base_url}/getAccountByHandle"
        logger.info(f"Handle validation URL: {url}")

        payload = {"accountHandle": handle.lower()}
        headers = self._get_headers()
        # print("HEADERS  >>>> ", headers, self.bot_service.user.state.jwt_token)

        try:
            response = self._make_api_request(url, headers, payload, method="POST")
            if response.status_code == 200:
                response_data = response.json()
                if not response_data.get('Error'):
                    logger.info("Handle validation successful")
                    return True, response_data
                else:
                    logger.error("Handle validation failed")
                    return False, response_data
            else:
                logger.error(f"Unexpected status code: {response.status_code}. Response content: {response.text}")
                return False, f"Handle validation failed: Unexpected error (status code: {response.status_code})"
        except Exception as e:
            logger.exception(f"Error during handle validation: {str(e)}")
            return False, f"Handle validation failed: {str(e)}"

    def offer_credex(self, payload):
        """Sends an offer to the CredEx API"""
        logger.info("Attempting to offer CredEx")
        payload.pop('full_name', None)

        url = f"{self.base_url}/createCredex"
        logger.info(f"Offer URL: {url}")

        headers = self._get_headers()
        try:
            response = self._make_api_request(url, headers, payload)
            if response.status_code == 200:
                response_data = response.json()

                if response_data.get('data', {}).get('action', {}).get('type') == "CREDEX_CREATED":
                    logger.info("Offer successful")
                    return True, response_data
                else:
                    logger.error("Offer failed")
                    return False, response_data.get('error')
            elif response.status_code == 400:
                logger.error(f"Offer failed: Bad request. Response content: {response.json().get('message')}")
                return False, response.json().get('error')
            elif response.status_code == 401:
                logger.error(f"Offer failed: Unauthorized. Response content: {response.text}")
                return False, f"Offer failed: Unauthorized. {response.text}"
            else:
                logger.error(f"Unexpected status code: {response.status_code}. Response content: {response.text}")
                return False, f"Offer failed: Unexpected error (status code: {response.status_code})"
        except Exception as e:
            logger.exception(f"Error during offer: {str(e)}")
            return False, f"Offer failed: {str(e)}"

    def accept_bulk_credex(self, payload):
        """Accepts multiple CredEx offers"""
        logger.info("Attempting to accept multiple CredEx offers")

        url = f"{self.base_url}/acceptCredexBulk"
        logger.info(f"Accept URL: {url}")

        headers = self._get_headers()
        try:
            response = self._make_api_request(url, headers, payload)
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('summary', {}).get("accepted"):
                    logger.info("Accept successful")
                    return True, response_data
                else:
                    logger.error("Accept failed")
                    return False, response_data.get('error')
            elif response.status_code == 400:
                logger.error(f"Accept failed: Bad request. Response content: {response.json().get('message')}")
                return False, f"Accept failed: {response.json().get('message')}"
            elif response.status_code == 401:
                logger.error(f"Accept failed: Unauthorized. Response content: {response.text}")
                return False, f"Accept failed: Unauthorized. {response.text}"
            else:
                logger.error(f"Unexpected status code: {response.status_code}. Response content: {response.text}")
                return False, f"Accept failed: Unexpected error (status code: {response.status_code})"
        except Exception as e:
            logger.exception(f"Error during accept: {str(e)}")
            return False, f"Accept failed: {str(e)}"


    def accept_credex(self, payload):
        """Accepts a CredEx offer"""
        logger.info("Attempting to accept CredEx")

        url = f"{self.base_url}/acceptCredex"
        logger.info(f"Accept URL: {url}")

        headers = self._get_headers()
        try:
            response = self._make_api_request(url, headers, payload)
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('data', {}).get('action', {}).get('type') == "CREDEX_ACCEPTED":
                    logger.info("Accept successful")
                    return True, response_data
                else:
                    logger.error("Accept failed")
                    return False, response_data.get('error')
            elif response.status_code == 400:
                logger.error(f"Accept failed: Bad request. Response content: {response.json().get('message')}")
                return False, f"Accept failed: {response.json().get('error', 'Failed to accept')}"
            elif response.status_code == 401:
                logger.error(f"Accept failed: Unauthorized. Response content: {response.text}")
                return False, f"Accept failed: Unauthorized. {response.text}"
            else:
                logger.error(f"Unexpected status code: {response.status_code}. Response content: {response.text}")
                return False, f"Accept failed: Unexpected error (status code: {response.status_code})"
        except Exception as e:
            logger.exception(f"Error during accept: {str(e)}")
            return False, f"Accept failed: {str(e)}"

    def decline_credex(self, payload):
        """Declines a CredEx offer"""
        logger.info("Attempting to decline CredEx")

        url = f"{self.base_url}/declineCredex"
        logger.info(f"Decline URL: {url}")

        headers = self._get_headers()
        try:
            response = self._make_api_request(url, headers, payload)
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('status') == 'success':
                    logger.info("Decline successful")
                    return True, "Decline successful"
                else:
                    logger.error("Decline failed")
                    return False, response_data.get('error')
            elif response.status_code == 400:
                logger.error(f"Decline failed: Bad request. Response content: {response.json().get('message')}")
                return False, f"Decline failed: {response.json().get('message')}"
            elif response.status_code == 401:
                logger.error(f"Decline failed: Unauthorized. Response content: {response.text}")
                return False, f"Decline failed: Unauthorized. {response.text}"
            else:
                logger.error(f"Unexpected status code: {response.status_code}. Response content: {response.text}")
                return False, f"Decline failed: Unexpected error (status code: {response.status_code})"
        except Exception as e:
            logger.exception(f"Error during decline: {str(e)}")
            return False, f"Decline failed: {str(e)}"


    def cancel_credex(self, payload):
        """Cancels a CredEx offer"""
        logger.info("Attempting to cancel CredEx")

        url = f"{self.base_url}/cancelCredex"
        logger.info(f"Cancel URL: {url}")

        headers = self._get_headers()
        try:
            response = self._make_api_request(url, headers, payload)
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('message') == 'Credex cancelled successfully':
                    logger.info("Cancel successful")
                    return True, "Credex cancelled successfully"
                else:
                    logger.error("Cancel failed")
                    return False, response_data.get('error')
            elif response.status_code == 400:
                logger.error(f"Cancel failed: Bad request. Response content: {response.json().get('message')}")
                return False, f"Cancel failed: {response.json().get('message')}"
            elif response.status_code == 401:
                logger.error(f"Cancel failed: Unauthorized. Response content: {response.text}")
                return False, f"Cancel failed: Unauthorized. {response.text}"
            else:
                logger.error(f"Unexpected status code: {response.status_code}. Response content: {response.text}")
                return False, f"Cancel failed: Unexpected error (status code: {response.status_code})"
        except Exception as e:
            logger.exception(f"Error during cancel: {str(e)}")
            return False, f"Cancel failed: {str(e)}"


    def get_credex(self, payload):
        """
        :param payload:
        :return:
        """
        logger.info("Fetching credex")
        url = f"{self.base_url}/getCredex"
        logger.info(f"Credex URL: {url}")

        headers = self._get_headers()
        try:
            response = self._make_api_request(url, headers, payload)
            if response.status_code == 200:
                response_data = response.json()
                logger.info("Credex fetched successfully")
                return True, response_data
            elif response.status_code == 400:
                logger.error(f"Credex fetch failed: Bad request. Response content: {response.json().get('message')}")
                return False, f"Credex fetch failed: {response.json().get('message')}"
            elif response.status_code == 401:
                logger.error(f"Credex fetch failed: Unauthorized. Response content: {response.text}")
                return False, f"Credex fetch failed: Unauthorized. {response.text}"
            else:
                logger.error(f"Unexpected status code: {response.status_code}. Response content: {response.text}")
                return False, f"Credex fetch failed: Unexpected error (status code: {response.status_code})"
        except Exception as e:
            logger.exception(f"Error during credex fetch: {str(e)}")
            return False, f"Credex fetch failed: {str(e)}"

    def get_ledger(self, payload):
        """
        :param payload:
        :return:
        """
        logger.info("Fetching ledger")
        url = f"{self.base_url}/getLedger"
        logger.info(f"Ledger URL: {url}")

        headers = self._get_headers()
        try:
            response = self._make_api_request(url, headers, payload)
            if response.status_code == 200:
                response_data = response.json()
                logger.info("Ledger fetched successfully")
                return True, response_data
            elif response.status_code == 400:
                logger.error(f"Ledger fetch failed: Bad request. Response content: {response.json().get('message')}")
                return False, f"Ledger fetch failed: {response.json().get('message')}"
            elif response.status_code == 401:
                logger.error(f"Ledger fetch failed: Unauthorized. Response content: {response.text}")
                return False, f"Ledger fetch failed: Unauthorized. {response.text}"
            else:
                logger.error(f"Unexpected status code: {response.status_code}. Response content: {response.text}")
                return False, f"Ledger fetch failed: Unexpected error (status code: {response.status_code})"
        except Exception as e:
            logger.exception(f"Error during ledger fetch: {str(e)}")
            return False, f"Ledger fetch failed: {str(e)}"


    @staticmethod
    def _get_basic_auth_header(phone_number):
        credentials = f"{phone_number}:{phone_number}"
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        return f"Basic {encoded_credentials}"

    def _get_headers(self):
        user = CachedUser(self.bot_service.user.mobile_number)
        headers = {
            'Content-Type': 'application/json',
            'x-client-api-key': config('WHATSAPP_BOT_API_KEY'),
        }

        # Add JWT token if available
        if user.jwt_token:
            headers['Authorization'] = f"Bearer {user.jwt_token}"
        else:
            self.login()


        return headers

    def _handle_reset_and_init(self, reset, silent, init):
        if reset and not silent or init:
            self._send_delay_message()
            self._send_first_message()

    def _send_delay_message(self):
        if self.bot_service.state.stage != "handle_action_register" and not cache.get(
                f"{self.bot_service.user.mobile_number}_interracted"):
            CredexWhatsappService(payload={
                "messaging_product": "whatsapp",
                "preview_url": False,
                "recipient_type": "individual",
                "to": self.bot_service.user.mobile_number,
                "type": "text",
                "text": {"body": "Please wait while we process your request..."}
            }).send_message()
            cache.set(f"{self.bot_service.user.mobile_number}_interracted", True, 60 * 15)

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

    def _make_api_request(self, url, headers, payload, method="POST", login=False):
        logger.info(f"Sending API request to: {url}")
        logger.info(f"Headers: {headers}")
        logger.info(f"Payload: {payload}")
        user = CachedUser(self.bot_service.user.mobile_number)
        if not user.jwt_token and login:
            logger.info("Refreshing token")
            success, message = self.login()
            if not success:
                return message

        headers['Authorization'] = f"Bearer {user.jwt_token}"
        response = requests.request(method, url, headers=headers, json=payload)
        logger.info(f"API Response Status Code: {response.status_code}")
        logger.info(f"API Response Headers: {response.headers}")
        logger.info(f"API Response Content: {response.text[:500]}...")  # Log only the first 500 characters
        return response

    @staticmethod
    def _process_api_response(response):
        # if response.status_code != 200:
        #     raise requests.exceptions.RequestException(f"API returned status code {response.status_code}")

        content_type = response.headers.get('Content-Type', '')
        if 'application/json' not in content_type:
            raise ValueError(f"Received unexpected Content-Type: {content_type}")

        return response.json()

    @staticmethod
    def _update_current_state(response_data, current_state, reset):
        if reset:
            current_state['profile'] = response_data
        else:
            current_state['profile'].update(response_data)
        logger.info("Current state updated")

    def _handle_successful_refresh(self, current_state, member_info=dict):

        logger.info("Refresh successful")
        # {
        #     'member': {
        #         'memberID': '93af87ee-4f1d-4341-a224-826598407793',
        #         'firstname': 'Takudzwa',
        #         'lastname': 'Sharara',
        #         'memberHandle': '263719624032',
        #         'defaultDenom': 'USD',
        #         'memberTier': {
        #             'low': 1,
        #             'high': 0
        #         },
        #         'remainingAvailableUSD': None
        #     },
        #     'memberDashboard': {
        #         'memberTier': {
        #             'low': 1,
        #             'high': 0
        #         },
        #         'remainingAvailableUSD': None,
        #         'accounts': [
        #             {
        #                 'success': True,
        #                 'data': {
        #                     'accountID': 'd3a68139-81de-4bdb-875a-494f747863fb',
        #                     'accountName': 'Takudzwa Sharara Personal',
        #                     'accountHandle': '263719624032',
        #                     'defaultDenom': 'USD',
        #                     'isOwnedAccount': True,
        #                     'authFor': [
        #                         {
        #                             'lastname': 'Sharara',
        #                             'firstname': 'Takudzwa',
        #                             'memberID': '93af87ee-4f1d-4341-a224-826598407793'
        #                         }
        #                     ],
        #                     'balanceData': {
        #                         'success': True,
        #                         'data': {
        #                             'securedNetBalancesByDenom': ['99.76 USD'],
        #                             'unsecuredBalancesInDefaultDenom': {
        #                                 'totalPayables': '0.00 USD',
        #                                 'totalReceivables': '0.00 USD',
        #                                 'netPayRec': '0.00 USD'
        #                             },
        #                             'netCredexAssetsInDefaultDenom': '99.76 USD'
        #                         },
        #                         'message': 'Account balances retrieved successfully'
        #                     },
        #                     'pendingInData': {
        #                         'success': True,
        #                         'data': [],
        #                         'message': 'No pending offers found'
        #                     },
        #                     'pendingOutData': {
        #                         'success': True, 'data': [],
        #                         'message': 'No pending outgoing offers found'
        #                     },
        #                     'sendOffersTo': {
        #                         'memberID': '93af87ee-4f1d-4341-a224-826598407793',
        #                         'firstname': 'Takudzwa',
        #                         'lastname': 'Sharara'
        #                     }
        #                 },
        #                 'message': 'Dashboard retrieved successfully'
        #             }
        #         ]
        #     }
        # }

        member_info = {
            'member': member_info.get('data', {}).get('action', {}).get('details', {}),
            'memberDashboard': member_info.get('data', {}).get('dashboard')
        }


        user = CachedUser(self.bot_service.user.mobile_number)
        if member_info:
            current_state['profile'] = member_info
            if not current_state.get('current_account', {}):
                if current_state.get('profile', {}).get('memberDashboard', {}).get('memberTier', {}).get('low', 1) < 2:
                    try:
                        current_state.update({'current_account': member_info['memberDashboard']['accounts'][0]})
                    except Exception as e:
                        print("ERROR SETTING DEFAULT PROFILE ", e)
                        current_state['current_account'] = {}
                else:
                    current_state['current_account'] = {}
                

        user.state.update_state(
            state=current_state,
            stage='handle_action_menu',
            update_from="refresh",
            option="handle_action_menu"
        )

        self.bot_service.state_manager.update_state(
            new_state=current_state,
            update_from="handle_action_menu",
            stage='handle_action_register',
            option="handle_action_register"
        )
        return None

    def _handle_failed_refresh(self, current_state, error_message):
        logger.error(f"Refresh failed: {error_message}")
        user = CachedUser(self.bot_service.user.mobile_number)
        user.state.update_state(
            state=current_state,
            stage='handle_action_register',
            update_from="refresh",
            option="handle_action_register"
        )
        return wrap_text(f"An error occurred: {error_message}. Please try again.",
                         self.bot_service.user.mobile_number,
                         extra_rows=[{"id": '1', "title": "Become a member"}],
                         include_menu=False)
