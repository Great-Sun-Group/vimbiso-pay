"""Utility functions for CredEx bot"""
import logging
from core.utils import wrap_text
from ..config.constants import REGISTER

logger = logging.getLogger(__name__)


def update_current_state(response_data, current_state, reset):
    """Update member data in state"""
    if reset:
        current_state["member"] = response_data
    else:
        current_state["member"].update(response_data)
    logger.info("Current state updated")


def handle_successful_refresh(current_state, state, bot_service):
    """Handle successful member refresh"""
    logger.info("Refresh successful")
    state.update_state(current_state, "refresh")
    return bot_service.action_handler.handle_action_select_profile()


def handle_failed_refresh(current_state, state, error_message, bot_service):
    """Handle failed member refresh"""
    logger.error(f"Refresh failed: {error_message}")
    state.update_state(current_state, "refresh_failed")
    channel_identifier = bot_service.user.state.state.get("channel", {}).get("identifier")
    return wrap_text(
        REGISTER.format(message=error_message),
        channel_identifier,
        extra_rows=[{"id": "1", "title": "Become a member"}],
        include_menu=False,
    )


def handle_message(bot_service):
    """Handle default message action"""
    logger.info("Handling default action")
    response = bot_service.action_handler.handle_default_action()
    logger.info("Default action handled")
    return response


def handle_offer_credex(bot_service):
    """Handle credex offer action"""
    logger.info("Handling offer credex action")
    bot_service.state.update({
        "action": "offer_credex"
    })
    return bot_service.offer_credex_handler.handle_action_offer_credex()


def handle_action(bot_service):
    """Handle dynamic action method"""
    action_method = getattr(bot_service.action_handler, bot_service.body, None)
    if action_method and callable(action_method):
        logger.info(f"Handling action: {bot_service.body}")
        bot_service.state.update({
            "action": bot_service.body
        })
        return action_method()
    else:
        logger.warning(f"Action method {bot_service.body} not found")
        return bot_service.action_handler.handle_default_action()


def handle_greeting(bot_service):
    """Handle greeting message"""
    logger.info("Handling greeting")
    bot_service.state.update({
        "action": "greeting"
    })
    return bot_service.action_handler.handle_greeting()
