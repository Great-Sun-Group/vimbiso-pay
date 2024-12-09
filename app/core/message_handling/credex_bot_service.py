import logging
from .action_handlers import ActionHandler
from .offer_credex_handler import OfferCredexHandler
from ..api.api_interactions import APIInteractions
from ..state.state_management import StateManager
from ..utils.exceptions import InvalidInputException
from ..utils.error_handler import error_decorator

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more detail
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CredexBotService:
    def __init__(self, payload, user: object = None) -> None:
        logger.debug(f"Initializing CredexBotService with payload: {payload}")
        if user is None:
            logger.error("User object is required")
            raise InvalidInputException("User object is required")

        self.message = payload
        self.user = user
        self.body = self.message.get("message", "")
        logger.debug(f"Message body: {self.body}")

        self.state = self.user.state
        self.current_state = self.state.get_state(self.user)
        if not isinstance(self.current_state, dict):
            self.current_state = self.current_state.state
        logger.debug(f"Current state: {self.current_state}")

        self.action_handler = ActionHandler(self)
        self.offer_credex_handler = OfferCredexHandler(self)

        # Initialize new modules
        from .message_handling import MessageHandler

        self.message_handler = MessageHandler(self)
        self.api_interactions = APIInteractions(self)
        self.state_manager = StateManager(self)
        self.response = self.handle()
        logger.debug(f"Final response: {self.response}")

    @error_decorator
    def handle(self):
        logger.info(f"Entry point: {self.state.stage}")
        response = self.message_handler.handle_message()
        logger.debug(f"handle() got response: {response}")
        return response

    @error_decorator
    def refresh(self, reset=True, silent=True, init=False):
        return self.api_interactions.refresh_member_info(reset, silent, init)
