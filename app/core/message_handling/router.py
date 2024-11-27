import logging
from functools import wraps
from ..config.constants import GREETINGS

logger = logging.getLogger(__name__)


class Router:
    def __init__(self):
        self.routes = {}

    def route(self, pattern):
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                return f(*args, **kwargs)

            self.routes[pattern] = wrapper
            return wrapper

        return decorator

    def handle(self, message, bot_service):
        for pattern, handler in self.routes.items():
            if self._match_pattern(pattern, message):
                logger.info(f"Routing message to handler: {handler.__name__}")
                return handler(bot_service)

        logger.warning(f"No handler found for message: {message}")
        return bot_service.action_handler.handle_default_action()

    def _match_pattern(self, pattern, message):
        if pattern == "greeting":
            return message.lower() in GREETINGS
        elif pattern == "offer_credex":
            return "=>" in message or "->" in message
        elif pattern.startswith("handle_action_"):
            return message.startswith(pattern)
        else:
            return pattern == message


router = Router()


@router.route("greeting")
def handle_greeting(bot_service):
    return bot_service.message_handler.handle_greeting()


@router.route("offer_credex")
def handle_offer_credex(bot_service):
    return bot_service.message_handler.handle_offer_credex()


@router.route("handle_action_")
def handle_action(bot_service):
    return bot_service.message_handler.handle_action()


# Add more route handlers as needed
