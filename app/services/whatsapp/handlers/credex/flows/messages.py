"""Message creation and formatting for credex flows"""
from typing import Any, Dict

from services.whatsapp.types import WhatsAppMessage
from ...message.state_handler import StateHandler


def create_initial_prompt_with_state(state_manager: Any) -> Dict[str, Any]:
    """Create initial welcome message without state duplication"""
    StateHandler.validate_state(state_manager)
    return WhatsAppMessage.create_text_with_state(
        state_manager,
        "Welcome! Please enter amount:"
    )


def create_handle_prompt_with_state(state_manager: Any) -> Dict[str, Any]:
    """Create handle input prompt without state duplication"""
    StateHandler.validate_state(state_manager)
    return WhatsAppMessage.create_text_with_state(
        state_manager,
        "Please enter handle:"
    )


def create_confirmation_prompt_with_state(state_manager: Any) -> Dict[str, Any]:
    """Create confirmation prompt without state duplication"""
    StateHandler.validate_state(state_manager)
    return WhatsAppMessage.create_text_with_state(
        state_manager,
        "Please confirm (yes/no):"
    )


def create_success_message_with_state(state_manager: Any) -> Dict[str, Any]:
    """Create success message without state duplication"""
    StateHandler.validate_state(state_manager)
    return WhatsAppMessage.create_text_with_state(
        state_manager,
        "Thank you! Your request has been processed."
    )


def create_cancel_message_with_state(state_manager: Any) -> Dict[str, Any]:
    """Create cancellation message without state duplication"""
    StateHandler.validate_state(state_manager)
    return WhatsAppMessage.create_text_with_state(
        state_manager,
        "Request cancelled."
    )


def create_error_message_with_state(state_manager: Any, error: str) -> Dict[str, Any]:
    """Create error message without state duplication"""
    StateHandler.validate_state(state_manager)
    return WhatsAppMessage.create_text_with_state(
        state_manager,
        str(error)
    )


def create_offer_confirmation_with_state(state_manager: Any) -> Dict[str, Any]:
    """Create offer confirmation message without state duplication"""
    StateHandler.validate_state(state_manager)

    # Get offer details directly from state
    amount = state_manager.get("offer_amount")
    handle = state_manager.get("offer_handle")
    name = state_manager.get("offer_name")

    return WhatsAppMessage.create_text_with_state(
        state_manager,
        f"Confirm offer:\n"
        f"Amount: {amount}\n"
        f"To: {name} ({handle})\n\n"
        "Please confirm (yes/no):"
    )


def create_action_confirmation_with_state(
    state_manager: Any,
    action: str
) -> Dict[str, Any]:
    """Create action confirmation message without state duplication"""
    StateHandler.validate_state(state_manager)

    # Get action details directly from state
    amount = state_manager.get("action_amount")
    counterparty = state_manager.get("action_counterparty")

    return WhatsAppMessage.create_text_with_state(
        state_manager,
        f"Confirm {action}:\n"
        f"Amount: {amount}\n"
        f"With: {counterparty}\n\n"
        "Please confirm (yes/no):"
    )


def create_cancel_confirmation_with_state(state_manager: Any) -> Dict[str, Any]:
    """Create cancel confirmation message without state duplication"""
    return create_action_confirmation_with_state(state_manager, "cancel")


def create_accept_confirmation_with_state(state_manager: Any) -> Dict[str, Any]:
    """Create accept confirmation message without state duplication"""
    return create_action_confirmation_with_state(state_manager, "accept")


def create_decline_confirmation_with_state(state_manager: Any) -> Dict[str, Any]:
    """Create decline confirmation message without state duplication"""
    return create_action_confirmation_with_state(state_manager, "decline")


def create_list_message_with_state(
    state_manager: Any,
    action: str,
    empty_message: str = None
) -> Dict[str, Any]:
    """Create list selection message without state duplication"""
    StateHandler.validate_state(state_manager)

    # Get items directly from state
    items = state_manager.get("list_items", [])

    if not items:
        return WhatsAppMessage.create_text_with_state(
            state_manager,
            empty_message or f"No {action} offers available"
        )

    message = f"Select offer to {action}:\n\n"
    for i, item in enumerate(items, 1):
        amount = item.get("formattedInitialAmount", "Unknown amount")
        counterparty = item.get("counterpartyAccountName", "Unknown")
        message += f"{i}. {amount} with {counterparty}\n"

    return WhatsAppMessage.create_text_with_state(
        state_manager,
        message
    )
