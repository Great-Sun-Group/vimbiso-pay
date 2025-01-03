"""Utility functions for CredEx bot"""
import logging
from typing import Any, Dict

from core.utils import wrap_text
from core.utils.error_handler import ErrorHandler
from core.utils.state_validator import StateValidator

from ..config.constants import REGISTER

logger = logging.getLogger(__name__)


def handle_successful_refresh(state_manager: Any) -> Dict[str, Any]:
    """Handle successful member refresh with state manager

    Args:
        state_manager: State manager instance

    Returns:
        Response from action handler
    """
    logger.info("Refresh successful")
    return handle_action_select_profile(state_manager)


def handle_failed_refresh(state_manager: Any, error_message: str) -> Dict[str, Any]:
    """Handle failed member refresh using state manager

    Args:
        state_manager: State manager instance
        error_message: Error message from failed refresh

    Returns:
        Error response message
    """
    logger.error(f"Refresh failed: {error_message}")

    # Validate at boundary
    validation = StateValidator.validate_before_access(
        {"channel": state_manager.get("channel")},
        {"channel"}
    )
    if not validation.is_valid:
        logger.error(f"Invalid state: {validation.error_message}")
        return wrap_text(
            REGISTER.format(message=error_message),
            "unknown",
            extra_rows=[{"id": "1", "title": "Become a member"}],
            include_menu=False,
        )

    channel = state_manager.get("channel")
    if not isinstance(channel, dict) or not channel.get("identifier"):
        logger.error("Invalid channel structure")
        return wrap_text(
            REGISTER.format(message=error_message),
            "unknown",
            extra_rows=[{"id": "1", "title": "Become a member"}],
            include_menu=False,
        )

    return wrap_text(
        REGISTER.format(message=error_message),
        channel["identifier"],
        extra_rows=[{"id": "1", "title": "Become a member"}],
        include_menu=False,
    )


def handle_message(state_manager: Any) -> Dict[str, Any]:
    """Handle default message action using state manager

    Args:
        state_manager: State manager instance

    Returns:
        Response from default action handler
    """
    logger.info("Handling default action")
    return handle_default_action(state_manager)


def handle_offer_credex(state_manager: Any) -> Dict[str, Any]:
    """Handle credex offer action using state manager

    Args:
        state_manager: State manager instance

    Returns:
        Response from offer credex handler
    """
    logger.info("Handling offer credex action")
    # Update action in state
    success, error = state_manager.update_state({"action": "offer_credex"})
    if not success:
        return ErrorHandler.handle_flow_error(
            step="offer_credex",
            action="update_state",
            data={"error": error},
            message=f"Failed to update action state: {error}",
            flow_state=state_manager.get_flow_state()
        )
    return handle_action_offer_credex(state_manager)


def handle_action(state_manager: Any, action: str) -> Dict[str, Any]:
    """Handle dynamic action method using state manager

    Args:
        state_manager: State manager instance
        action: Action to handle

    Returns:
        Response from action handler
    """
    # Map of action names to handler functions
    action_handlers = {
        "handle_action_select_profile": handle_action_select_profile,
        "handle_default_action": handle_default_action,
        "handle_greeting": handle_greeting,
        "handle_action_offer_credex": handle_action_offer_credex
    }

    handler = action_handlers.get(action)
    if handler:
        logger.info(f"Handling action: {action}")
        success, error = state_manager.update_state({"action": action})
        if not success:
            return ErrorHandler.handle_flow_error(
                step="action",
                action=action,
                data={"error": error},
                message=f"Failed to update action state: {error}",
                flow_state=state_manager.get_flow_state()
            )
        return handler(state_manager)
    else:
        logger.warning(f"Action method {action} not found")
        return handle_default_action(state_manager)


def handle_greeting(state_manager: Any) -> Dict[str, Any]:
    """Handle greeting message using state manager

    Args:
        state_manager: State manager instance

    Returns:
        Response from greeting handler
    """
    logger.info("Handling greeting")
    success, error = state_manager.update_state({"action": "greeting"})
    if not success:
        return ErrorHandler.handle_flow_error(
            step="greeting",
            action="update_state",
            data={"error": error},
            message=f"Failed to update action state: {error}",
            flow_state=state_manager.get_flow_state()
        )
    return handle_action_greeting(state_manager)


# Handler function implementations
def handle_action_select_profile(state_manager: Any) -> Dict[str, Any]:
    """Handle select profile action"""
    # Implementation would go here
    pass


def handle_default_action(state_manager: Any) -> Dict[str, Any]:
    """Handle default action"""
    # Implementation would go here
    pass


def handle_action_greeting(state_manager: Any) -> Dict[str, Any]:
    """Handle greeting action"""
    # Implementation would go here
    pass


def handle_action_offer_credex(state_manager: Any) -> Dict[str, Any]:
    """Handle offer credex action"""
    # Implementation would go here
    pass
