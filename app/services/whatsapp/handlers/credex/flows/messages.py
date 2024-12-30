"""Message creation and formatting for credex flows"""
from typing import Any, Dict, List

from services.whatsapp.types import WhatsAppMessage
from core.utils.error_handler import ErrorHandler


def create_initial_prompt(channel_id: str) -> Dict[str, Any]:
    """Create initial welcome message"""
    return WhatsAppMessage.create_text(
        channel_id,
        "Welcome! Please enter amount:"
    )


def create_handle_prompt(channel_id: str) -> Dict[str, Any]:
    """Create handle input prompt"""
    return WhatsAppMessage.create_text(
        channel_id,
        "Please enter handle:"
    )


def create_confirmation_prompt(channel_id: str) -> Dict[str, Any]:
    """Create confirmation prompt"""
    return WhatsAppMessage.create_text(
        channel_id,
        "Please confirm (yes/no):"
    )


def create_success_message(channel_id: str) -> Dict[str, Any]:
    """Create success message"""
    return WhatsAppMessage.create_text(
        channel_id,
        f"{ErrorHandler.SUCCESS_PREFIX} Your request has been processed."
    )


def create_cancel_message(channel_id: str) -> Dict[str, Any]:
    """Create cancellation message"""
    return WhatsAppMessage.create_text(
        channel_id,
        "Request cancelled."
    )


def create_error_message(channel_id: str, error: str) -> Dict[str, Any]:
    """Create error message"""
    return WhatsAppMessage.create_text(
        channel_id,
        ErrorHandler.format_error_message(str(error))
    )


def create_offer_confirmation(
    channel_id: str,
    amount: float,
    denomination: str,
    handle: str
) -> Dict[str, Any]:
    """Create offer confirmation message"""
    formatted_amount = f"{amount} {denomination}".strip()
    return WhatsAppMessage.create_text(
        channel_id,
        f"Confirm offer:\n"
        f"Amount: {formatted_amount}\n"
        f"To: {handle}\n\n"
        "Please confirm (yes/no):"
    )


def create_action_confirmation(
    channel_id: str,
    action: str,
    amount: str,
    counterparty: str
) -> Dict[str, Any]:
    """Create action confirmation message"""
    return WhatsAppMessage.create_text(
        channel_id,
        f"Confirm {action}:\n"
        f"Amount: {amount}\n"
        f"With: {counterparty}\n\n"
        "Please confirm (yes/no):"
    )


def create_cancel_confirmation(
    channel_id: str,
    amount: str,
    counterparty: str
) -> Dict[str, Any]:
    """Create cancel confirmation message"""
    return create_action_confirmation(channel_id, "cancel", amount, counterparty)


def create_accept_confirmation(
    channel_id: str,
    amount: str,
    counterparty: str
) -> Dict[str, Any]:
    """Create accept confirmation message"""
    return create_action_confirmation(channel_id, "accept", amount, counterparty)


def create_decline_confirmation(
    channel_id: str,
    amount: str,
    counterparty: str
) -> Dict[str, Any]:
    """Create decline confirmation message"""
    return create_action_confirmation(channel_id, "decline", amount, counterparty)


def create_list_message(
    channel_id: str,
    action: str,
    items: List[Dict[str, Any]],
    empty_message: str = None
) -> Dict[str, Any]:
    """Create list selection message"""
    if not items:
        return WhatsAppMessage.create_text(
            channel_id,
            empty_message or f"No {action} offers available"
        )

    message_parts = [f"Select offer to {action}:\n"]
    for i, item in enumerate(items, 1):
        amount = item.get("formattedInitialAmount", "Unknown amount")
        counterparty = item.get("counterpartyAccountName", "Unknown")
        message_parts.append(f"{i}. {amount} with {counterparty}")

    return WhatsAppMessage.create_text(
        channel_id,
        "\n".join(message_parts)
    )
