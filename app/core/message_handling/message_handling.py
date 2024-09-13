import logging
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils.html import escape
from ..utils.utils import wrap_text
from ..config.constants import GREETINGS
from .router import router
from ..utils.exceptions import InvalidInputException

logger = logging.getLogger(__name__)

class MessageHandler:
    def __init__(self, bot_service):
        self.bot_service = bot_service

    def handle_message(self):
        if self.bot_service.body is None:
            logger.warning("Empty message body received")
            return self.bot_service.action_handler.handle_default_action()

        try:
            sanitized_body = self.sanitize_input(self.bot_service.body)
            self.validate_input(sanitized_body)
            return router.handle(sanitized_body, self.bot_service)
        except InvalidInputException as e:  # Changed this line
            logger.error(f"Input validation failed: {str(e)}")
            return f"Invalid input: {str(e)}"

    def sanitize_input(self, input_text):
        # Escape HTML entities to prevent XSS attacks
        return escape(input_text)

    def validate_input(self, input_text):
        # Basic length check
        if len(input_text) > 1000:
            raise InvalidInputException("Input is too long. Please limit your message to 1000 characters.")  # Changed this line

        # Check for potential email inputs
        if '@' in input_text:
            try:
                validate_email(input_text)
            except ValidationError:
                raise InvalidInputException("Invalid email format.")  # Changed this line

        # Add more custom validation rules as needed
        # For example, you could check for specific patterns or disallowed characters
        disallowed_chars = ['<', '>', '{', '}', '[', ']']
        if any(char in input_text for char in disallowed_chars):
            raise InvalidInputException("Input contains disallowed characters.")  # Changed this line

    def handle_offer_credex(self):
        logger.info("Handling offer credex action")
        self.bot_service.state.update_state(self.bot_service.current_state, "handle_action_offer_credex", "handle", "handle_action_offer_credex")
        return self.bot_service.offer_credex_handler.handle_action_offer_credex()

    def handle_action(self):
        action_method = getattr(self.bot_service.action_handler, self.bot_service.body, None)
        if action_method and callable(action_method):
            logger.info(f"Handling action: {self.bot_service.body}")
            self.bot_service.state.update_state(self.bot_service.current_state, self.bot_service.body, "handle", self.bot_service.body)
            return action_method()
        else:
            logger.warning(f"Action method {self.bot_service.body} not found")
            return self.handle_default_action()

    def handle_greeting(self):
        logger.info("Handling greeting")
        self.bot_service.state.update_state(self.bot_service.current_state, "handle_action_select_profile", "handle", "handle_greeting")
        return self.bot_service.action_handler.handle_greeting()

    def handle_default_action(self):
        logger.info("Handling default action")
        response = self.bot_service.action_handler.handle_default_action()
        logger.info(f"Final state: {self.bot_service.state.stage}")
        return response