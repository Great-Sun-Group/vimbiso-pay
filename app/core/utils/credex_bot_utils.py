"""Utility functions for CredEx bot"""
import logging
from typing import Any, Dict

from core.utils import wrap_text
from core.utils.exceptions import FlowException
from core.utils.state_validator import StateValidator

from ..config.constants import REGISTER

logger = logging.getLogger(__name__)


def handle_successful_refresh(state_manager: Any) -> Dict[str, Any]:
    """Handle successful member refresh with state manager

    Args:
        state_manager: State manager instance

    Returns:
        Response from action handler

    Raises:
        FlowException: If refresh handling fails
    """
    try:
        logger.info("Refresh successful")
        return handle_action_select_profile(state_manager)
    except Exception as e:
        raise FlowException(
            message=f"Failed to handle successful refresh: {str(e)}",
            step="refresh",
            action="handle_success",
            data={"error": str(e)}
        )


def handle_failed_refresh(state_manager: Any, error_message: str) -> Dict[str, Any]:
    """Handle failed member refresh using state manager

    Args:
        state_manager: State manager instance
        error_message: Error message from failed refresh

    Returns:
        Error response message

    Raises:
        FlowException: If state validation fails
    """
    try:
        logger.error(f"Refresh failed: {error_message}")

        # Validate at boundary
        validation = StateValidator.validate_before_access(
            {"channel": state_manager.get("channel")},
            {"channel"}
        )
        if not validation.is_valid:
            logger.error(f"Invalid state: {validation.error_message}")
            raise FlowException(
                message=validation.error_message,
                step="refresh",
                action="validate_state",
                data={"error": error_message}
            )

        channel = state_manager.get("channel")
        if not isinstance(channel, dict) or not channel.get("identifier"):
            logger.error("Invalid channel structure")
            raise FlowException(
                message="Invalid channel structure",
                step="refresh",
                action="validate_channel",
                data={"error": error_message}
            )

        return wrap_text(
            REGISTER.format(message=error_message),
            channel["identifier"],
            extra_rows=[{"id": "1", "title": "Become a member"}],
            include_menu=False,
        )

    except FlowException:
        raise
    except Exception as e:
        raise FlowException(
            message=f"Failed to handle refresh error: {str(e)}",
            step="refresh",
            action="handle_error",
            data={"error": error_message}
        )


def handle_message(state_manager: Any) -> Dict[str, Any]:
    """Handle default message action using state manager

    Args:
        state_manager: State manager instance

    Returns:
        Response from default action handler

    Raises:
        FlowException: If message handling fails
    """
    try:
        logger.info("Handling default action")
        return handle_default_action(state_manager)
    except Exception as e:
        raise FlowException(
            message=f"Failed to handle message: {str(e)}",
            step="message",
            action="handle_default",
            data={"error": str(e)}
        )


def handle_offer_credex(state_manager: Any) -> Dict[str, Any]:
    """Handle credex offer action using state manager

    Args:
        state_manager: State manager instance

    Returns:
        Response from offer credex handler

    Raises:
        FlowException: If state update fails
    """
    logger.info("Handling offer credex action")
    try:
        # Update action in state
        state_manager.update_state({"action": "offer_credex"})
        return handle_action_offer_credex(state_manager)
    except Exception as e:
        raise FlowException(
            message=f"Failed to handle credex offer: {str(e)}",
            step="offer_credex",
            action="update_state",
            data={"error": str(e)}
        )


def handle_action(state_manager: Any, action: str) -> Dict[str, Any]:
    """Handle dynamic action method using state manager

    Args:
        state_manager: State manager instance
        action: Action to handle

    Returns:
        Response from action handler

    Raises:
        FlowException: If state update fails or action not found
    """
    # Map of action names to handler functions
    action_handlers = {
        "handle_action_select_profile": handle_action_select_profile,
        "handle_default_action": handle_default_action,
        "handle_greeting": handle_greeting,
        "handle_action_offer_credex": handle_action_offer_credex
    }

    handler = action_handlers.get(action)
    if not handler:
        logger.warning(f"Action method {action} not found")
        return handle_default_action(state_manager)

    try:
        logger.info(f"Handling action: {action}")
        state_manager.update_state({"action": action})
        return handler(state_manager)
    except Exception as e:
        raise FlowException(
            message=f"Failed to handle action: {str(e)}",
            step="action",
            action=action,
            data={"error": str(e)}
        )


def handle_greeting(state_manager: Any) -> Dict[str, Any]:
    """Handle greeting message using state manager

    Args:
        state_manager: State manager instance

    Returns:
        Response from greeting handler

    Raises:
        FlowException: If state update fails
    """
    logger.info("Handling greeting")
    try:
        state_manager.update_state({"action": "greeting"})
        return handle_action_greeting(state_manager)
    except Exception as e:
        raise FlowException(
            message=f"Failed to handle greeting: {str(e)}",
            step="greeting",
            action="update_state",
            data={"error": str(e)}
        )


# Handler function implementations
def handle_action_select_profile(state_manager: Any) -> Dict[str, Any]:
    """Handle select profile action

    Args:
        state_manager: State manager instance

    Returns:
        Response from profile handler

    Raises:
        FlowException: If profile handling fails
    """
    try:
        # Implementation would go here
        raise NotImplementedError("Profile selection not implemented")
    except Exception as e:
        raise FlowException(
            message=f"Failed to handle profile selection: {str(e)}",
            step="profile",
            action="select",
            data={"error": str(e)}
        )


def handle_default_action(state_manager: Any) -> Dict[str, Any]:
    """Handle default action

    Args:
        state_manager: State manager instance

    Returns:
        Response from default handler

    Raises:
        FlowException: If default handling fails
    """
    try:
        # Implementation would go here
        raise NotImplementedError("Default action not implemented")
    except Exception as e:
        raise FlowException(
            message=f"Failed to handle default action: {str(e)}",
            step="default",
            action="handle",
            data={"error": str(e)}
        )


def handle_action_greeting(state_manager: Any) -> Dict[str, Any]:
    """Handle greeting action

    Args:
        state_manager: State manager instance

    Returns:
        Response from greeting handler

    Raises:
        FlowException: If greeting handling fails
    """
    try:
        # Implementation would go here
        raise NotImplementedError("Greeting action not implemented")
    except Exception as e:
        raise FlowException(
            message=f"Failed to handle greeting action: {str(e)}",
            step="greeting",
            action="handle",
            data={"error": str(e)}
        )


def handle_action_offer_credex(state_manager: Any) -> Dict[str, Any]:
    """Handle offer credex action

    Args:
        state_manager: State manager instance

    Returns:
        Response from credex handler

    Raises:
        FlowException: If credex handling fails
    """
    try:
        # Implementation would go here
        raise NotImplementedError("Credex offer not implemented")
    except Exception as e:
        raise FlowException(
            message=f"Failed to handle credex offer: {str(e)}",
            step="credex",
            action="offer",
            data={"error": str(e)}
        )
