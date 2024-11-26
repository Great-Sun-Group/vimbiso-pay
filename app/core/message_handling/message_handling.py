import logging
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils.html import escape
from ..utils.utils import wrap_text
from ..config.constants import GREETINGS, REGISTER, INVALID_ACTION
from .router import router
from ..utils.exceptions import InvalidInputException
from .whatsapp_forms import registration_form

logger = logging.getLogger(__name__)


def validate_input(input_text):
    if len(input_text) > 1000:
        raise InvalidInputException("Input is too long. Please limit your message to 1000 characters.")

    if '@' in input_text:
        try:
            validate_email(input_text)
        except ValidationError:
            raise InvalidInputException("Invalid email format.")

    disallowed_chars = ['<', '>', '{', '}', '[', ']']
    if any(char in input_text for char in disallowed_chars):
        raise InvalidInputException("Input contains disallowed characters.")


def sanitize_input(input_text):
    return escape(input_text)


class MessageHandler:
    def __init__(self, bot_service):
        self.bot_service = bot_service

    def handle_message(self):
        if self.bot_service.body is None:
            logger.warning("Empty message body received")
            return self.bot_service.action_handler.handle_default_action()

        try:
            sanitized_body = sanitize_input(self.bot_service.body)
            validate_input(sanitized_body)

            if self.is_greeting(sanitized_body):
                return self.handle_greeting()

            return router.handle(sanitized_body, self.bot_service)
        except InvalidInputException as e:
            logger.error(f"Input validation failed: {str(e)}")
            return wrap_text(f"Invalid input: {str(e)}", self.bot_service.user.mobile_number)

    @staticmethod
    def is_greeting(message):
        return message.lower().strip() in GREETINGS

    def handle_action_register(self):
        logger.info("Handling offer credex action")
        print(self.bot_service.state.get_state())

    def handle_greeting(self):
        logger.info("Handling greeting")
        success, message = self.bot_service.api_interactions.login()

        if success:
            self.bot_service.state.update_state(self.bot_service.current_state, "handle_action_select_profile",
                                                "handle", "handle_greeting")
            return wrap_text(f"Welcome back! {message}\nHow can I assist you today?",
                             self.bot_service.user.mobile_number)
        else:
            if "new user" in message.lower() or "invalid phone" in message.lower():
                self.bot_service.state.update_state(self.bot_service.current_state, "handle_action_register", "handle",
                                                    "handle_greeting")
                return wrap_text(REGISTER.format(message=message), self.bot_service.user.mobile_number,
                                 extra_rows=[{"id": '1', "title": "Become a member"}])
            else:
                self.bot_service.state.update_state(self.bot_service.current_state, "handle_action_register", "handle",
                                                    "handle_greeting")
                return registration_form(self.bot_service.user.mobile_number, message=message)
            # wrap_text(f"Login failed: {message}\nPlease try again later or contact support.", )

    def handle_offer_credex(self):
        logger.info("Handling offer credex action")
        self.bot_service.state.update_state(
            self.bot_service.current_state,
            "handle_action_offer_credex",
            "handle",
            "handle_action_offer_credex"
        )
        return self.bot_service.offer_credex_handler.handle_action_offer_credex()

    def handle_action(self):
        if f"{self.bot_service.body}".lower() in GREETINGS:
            self.bot_service.body = "handle_action_menu"
            self.bot_service.state.reset_state()

        if f"{self.bot_service.body}".startswith("handle_"):
            action = self.bot_service.body
        elif f"{self.bot_service.body}" == 'AcceptAllIncomingOffers':
            action = "handle_action_accept_all_incoming_offers"
        elif f"{self.bot_service.body}".startswith("accept_"):
            action = "handle_action_accept_offer"
        elif f"{self.bot_service.body}".startswith("reject_"):
            action = "handle_action_reject_offer"
        elif f"{self.bot_service.body}".startswith("cancel_"):
            action = "handle_action_cancel_offer"
        else:
            action = f"{self.bot_service.user.state.stage}"

        action_method = getattr(self.bot_service.action_handler, action, None)
        if action_method and callable(action_method):
            logger.info(f"Handling action: {action}")
            return action_method()
        else:
            logger.warning(f"Action method {self.bot_service.body} not found")
            return self.handle_default_action()

    def handle_default_action(self):
        logger.info("Handling default action")
        response = wrap_text(INVALID_ACTION, self.bot_service.user.mobile_number)
        logger.info(f"Final state: {self.bot_service.state.stage}")
        return response
