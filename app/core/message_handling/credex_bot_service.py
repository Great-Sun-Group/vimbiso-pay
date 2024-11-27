import logging
from ..utils.utils import wrap_text
from .action_handlers import ActionHandler
from .offer_credex_handler import OfferCredexHandler
from ..config.constants import INVALID_ACTION
from ..api.api_interactions import APIInteractions
from ..state.state_management import StateManager
from ..utils.exceptions import InvalidInputException
from ..utils.error_handler import error_decorator

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CredexBotService:
    def __init__(self, payload, user: object = None) -> None:
        print(user)
        if user is None:
            logger.error("User object is required")
            raise InvalidInputException("User object is required")

        self.message = payload
        self.user = user
        self.body = self.message.get("message", "")

        self.state = self.user.state
        self.current_state = self.state.get_state(self.user)
        if not isinstance(self.current_state, dict):
            self.current_state = self.current_state.state

        self.action_handler = ActionHandler(self)
        self.offer_credex_handler = OfferCredexHandler(self)

        # Initialize new modules
        from .message_handling import MessageHandler

        self.message_handler = MessageHandler(self)
        self.api_interactions = APIInteractions(self)
        self.state_manager = StateManager(self)
        self.response = self.handle()

    @error_decorator
    def handle(self):
        logger.info(f"Entry point: {self.state.stage}")
        return self.message_handler.handle_action()

    @error_decorator
    def refresh(self, reset=True, silent=True, init=False):
        return self.api_interactions.refresh_member_info(reset, silent, init)
