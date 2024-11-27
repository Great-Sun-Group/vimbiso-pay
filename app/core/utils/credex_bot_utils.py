import logging
from core.utils import wrap_text
from ..config.constants import REGISTER, GREETINGS

logger = logging.getLogger(__name__)


def update_current_state(response_data, current_state, reset):
    if reset:
        current_state["member"] = response_data
    else:
        current_state["member"].update(response_data)
    logger.info("Current state updated")


def handle_successful_refresh(current_state, state, bot_service):
    logger.info("Refresh successful")
    state.update_state(
        state=current_state,
        stage="handle_action_select_profile",
        update_from="refresh",
        option="select_account_to_use",
    )
    return bot_service.action_handler.handle_action_select_profile()


def handle_failed_refresh(current_state, state, error_message, bot_service):
    logger.error(f"Refresh failed: {error_message}")
    state.update_state(
        state=current_state,
        stage="handle_action_register",
        update_from="refresh",
        option="handle_action_register",
    )
    return wrap_text(
        REGISTER.format(message=error_message),
        bot_service.user.mobile_number,
        extra_rows=[{"id": "1", "title": "Become a member"}],
        include_menu=False,
    )


def handle_message(bot_service):
    logger.info("Handling default action")
    response = bot_service.action_handler.handle_default_action()
    logger.info(f"Final state: {bot_service.state.stage}")
    return response


def handle_offer_credex(bot_service):
    logger.info("Handling offer credex action")
    bot_service.state.update_state(
        bot_service.current_state,
        "handle_action_offer_credex",
        "handle",
        "handle_action_offer_credex",
    )
    return bot_service.offer_credex_handler.handle_action_offer_credex()


def handle_action(bot_service):
    action_method = getattr(bot_service.action_handler, bot_service.body, None)
    if action_method and callable(action_method):
        logger.info(f"Handling action: {bot_service.body}")
        bot_service.state.update_state(
            bot_service.current_state, bot_service.body, "handle", bot_service.body
        )
        return action_method()
    else:
        logger.warning(f"Action method {bot_service.body} not found")
        return bot_service.action_handler.handle_default_action()


def handle_greeting(bot_service):
    logger.info("Handling greeting")
    bot_service.state.update_state(
        bot_service.current_state,
        "handle_action_select_profile",
        "handle",
        "handle_greeting",
    )
    return bot_service.action_handler.handle_greeting()
