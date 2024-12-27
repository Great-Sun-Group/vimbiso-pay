"""Message creation and formatting for credex flows"""
from typing import Any, Dict

from services.whatsapp.types import WhatsAppMessage
from .transformers import format_amount


def create_initial_prompt(channel_identifier: str) -> Dict[str, Any]:
    """Create initial welcome message"""
    return WhatsAppMessage.create_text(
        channel_identifier,
        "Welcome! Please enter amount:"
    )


def create_handle_prompt(channel_identifier: str) -> Dict[str, Any]:
    """Create handle input prompt"""
    return WhatsAppMessage.create_text(
        channel_identifier,
        "Please enter handle:"
    )


def create_confirmation_prompt(channel_identifier: str) -> Dict[str, Any]:
    """Create confirmation prompt"""
    return WhatsAppMessage.create_text(
        channel_identifier,
        "Please confirm (yes/no):"
    )


def create_success_message(channel_identifier: str) -> Dict[str, Any]:
    """Create success message"""
    return WhatsAppMessage.create_text(
        channel_identifier,
        "Thank you! Your request has been processed."
    )


def create_cancel_message(channel_identifier: str) -> Dict[str, Any]:
    """Create cancellation message"""
    return WhatsAppMessage.create_text(
        channel_identifier,
        "Request cancelled."
    )


def create_error_message(channel_identifier: str, error: str) -> Dict[str, Any]:
    """Create error message"""
    return WhatsAppMessage.create_text(
        channel_identifier,
        str(error)
    )


def create_offer_confirmation(
    channel_identifier: str,
    amount: float,
    denomination: str,
    handle: str,
    name: str
) -> Dict[str, Any]:
    """Create offer confirmation message"""
    formatted_amount = format_amount(amount, denomination)
    return WhatsAppMessage.create_text(
        channel_identifier,
        f"Confirm offer:\n"
        f"Amount: {formatted_amount}\n"
        f"To: {name} ({handle})\n\n"
        "Please confirm (yes/no):"
    )


def create_action_confirmation(
    channel_identifier: str,
    amount: str,
    counterparty: str,
    action: str
) -> Dict[str, Any]:
    """Create action confirmation message"""
    return WhatsAppMessage.create_text(
        channel_identifier,
        f"Confirm {action}:\n"
        f"Amount: {amount}\n"
        f"With: {counterparty}\n\n"
        "Please confirm (yes/no):"
    )


def create_cancel_confirmation(
    channel_identifier: str,
    amount: str,
    counterparty: str
) -> Dict[str, Any]:
    """Create cancel confirmation message"""
    return create_action_confirmation(
        channel_identifier,
        amount,
        counterparty,
        "cancel"
    )


def create_accept_confirmation(
    channel_identifier: str,
    amount: str,
    counterparty: str
) -> Dict[str, Any]:
    """Create accept confirmation message"""
    return create_action_confirmation(
        channel_identifier,
        amount,
        counterparty,
        "accept"
    )


def create_decline_confirmation(
    channel_identifier: str,
    amount: str,
    counterparty: str
) -> Dict[str, Any]:
    """Create decline confirmation message"""
    return create_action_confirmation(
        channel_identifier,
        amount,
        counterparty,
        "decline"
    )


def create_list_message(
    channel_identifier: str,
    items: list,
    action: str,
    empty_message: str = None
) -> Dict[str, Any]:
    """Create list selection message"""
    if not items:
        return WhatsAppMessage.create_text(
            channel_identifier,
            empty_message or f"No {action} offers available"
        )

    message = f"Select offer to {action}:\n\n"
    for i, item in enumerate(items, 1):
        amount = item.get("formattedInitialAmount", "Unknown amount")
        counterparty = item.get("counterpartyAccountName", "Unknown")
        message += f"{i}. {amount} with {counterparty}\n"

    return WhatsAppMessage.create_text(
        channel_identifier,
        message
    )
