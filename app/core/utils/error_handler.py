import logging
from core.exceptions import (
    CredExBotException,
    InvalidInputException,
    APIException,
    StateException,
    ActionHandlerException,
    ConfigurationException
)
from core.utils import wrap_text

logger = logging.getLogger(__name__)

def handle_error(e, bot_service):
    """Centralized error handling function"""
    if isinstance(e, InvalidInputException):
        message = "Sorry, I couldn't understand your input. Please try again."
    elif isinstance(e, APIException):
        message = "We're experiencing some technical difficulties. Please try again later."
    elif isinstance(e, StateException):
        message = "There was an issue with your current session. Please start over."
    elif isinstance(e, ActionHandlerException):
        message = "I encountered an error while processing your request. Please try again."
    elif isinstance(e, ConfigurationException):
        message = "There's a configuration issue on our end. Our team has been notified."
    elif isinstance(e, CredExBotException):
        message = "An unexpected error occurred. Please try again or contact support."
    else:
        message = "I apologize, but something went wrong. Please try again later."

    logger.error(f"Error: {type(e).__name__} - {str(e)}")
    return wrap_text(message, bot_service.user.mobile_number)

def error_decorator(f):
    """Decorator to wrap functions with error handling"""
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            return handle_error(e, args[0])  # Assuming the first argument is always bot_service
    return wrapper