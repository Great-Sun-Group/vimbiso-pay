"""Message creation and formatting for credex flows"""
from typing import Any, Dict

from services.whatsapp.types import WhatsAppMessage
from core.utils.exceptions import StateException


def create_initial_prompt_with_state(state_manager: Any) -> Dict[str, Any]:
    """Create initial welcome message enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get channel (StateManager validates)
        channel = state_manager.get("channel")
        return WhatsAppMessage.create_text(
            channel["identifier"],
            "Welcome! Please enter amount:"
        )
    except StateException as e:
        raise ValueError(str(e))


def create_handle_prompt_with_state(state_manager: Any) -> Dict[str, Any]:
    """Create handle input prompt enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get channel (StateManager validates)
        channel = state_manager.get("channel")
        return WhatsAppMessage.create_text(
            channel["identifier"],
            "Please enter handle:"
        )
    except StateException as e:
        raise ValueError(str(e))


def create_confirmation_prompt_with_state(state_manager: Any) -> Dict[str, Any]:
    """Create confirmation prompt enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get channel (StateManager validates)
        channel = state_manager.get("channel")
        return WhatsAppMessage.create_text(
            channel["identifier"],
            "Please confirm (yes/no):"
        )
    except StateException as e:
        raise ValueError(str(e))


def create_success_message_with_state(state_manager: Any) -> Dict[str, Any]:
    """Create success message enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get channel (StateManager validates)
        channel = state_manager.get("channel")
        return WhatsAppMessage.create_text(
            channel["identifier"],
            "Thank you! Your request has been processed."
        )
    except StateException as e:
        raise ValueError(str(e))


def create_cancel_message_with_state(state_manager: Any) -> Dict[str, Any]:
    """Create cancellation message enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get channel (StateManager validates)
        channel = state_manager.get("channel")
        return WhatsAppMessage.create_text(
            channel["identifier"],
            "Request cancelled."
        )
    except StateException as e:
        raise ValueError(str(e))


def create_error_message_with_state(state_manager: Any, error: str) -> Dict[str, Any]:
    """Create error message enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get channel (StateManager validates)
        channel = state_manager.get("channel")
        return WhatsAppMessage.create_text(
            channel["identifier"],
            str(error)
        )
    except StateException as e:
        raise ValueError(str(e))


def create_offer_confirmation_with_state(state_manager: Any) -> Dict[str, Any]:
    """Create offer confirmation message enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get required data (StateManager validates)
        channel = state_manager.get("channel")
        flow_data = state_manager.get("flow_data")

        if not flow_data or not flow_data.get("data"):
            raise StateException("Missing flow data")

        # Get offer details from flow data
        data = flow_data["data"]
        amount_denom = data.get("amount_denom")
        handle = data.get("handle")

        if not amount_denom or not handle:
            raise StateException("Missing offer details")

        formatted_amount = f"{amount_denom['amount']} {amount_denom['denomination']}".strip()
        return WhatsAppMessage.create_text(
            channel["identifier"],
            f"Confirm offer:\n"
            f"Amount: {formatted_amount}\n"
            f"To: {handle}\n\n"
            "Please confirm (yes/no):"
        )
    except StateException as e:
        raise ValueError(str(e))


def create_action_confirmation_with_state(
    state_manager: Any,
    action: str
) -> Dict[str, Any]:
    """Create action confirmation message enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get required data (StateManager validates)
        channel = state_manager.get("channel")
        flow_data = state_manager.get("flow_data")

        if not flow_data or not flow_data.get("data"):
            raise StateException("Missing flow data")

        # Get action details from flow data
        data = flow_data["data"]
        amount = data.get("amount")
        counterparty = data.get("counterparty")

        if not amount or not counterparty:
            raise StateException("Missing action details")

        return WhatsAppMessage.create_text(
            channel["identifier"],
            f"Confirm {action}:\n"
            f"Amount: {amount}\n"
            f"With: {counterparty}\n\n"
            "Please confirm (yes/no):"
        )
    except StateException as e:
        raise ValueError(str(e))


def create_cancel_confirmation_with_state(state_manager: Any) -> Dict[str, Any]:
    """Create cancel confirmation message enforcing SINGLE SOURCE OF TRUTH"""
    return create_action_confirmation_with_state(state_manager, "cancel")


def create_accept_confirmation_with_state(state_manager: Any) -> Dict[str, Any]:
    """Create accept confirmation message enforcing SINGLE SOURCE OF TRUTH"""
    return create_action_confirmation_with_state(state_manager, "accept")


def create_decline_confirmation_with_state(state_manager: Any) -> Dict[str, Any]:
    """Create decline confirmation message enforcing SINGLE SOURCE OF TRUTH"""
    return create_action_confirmation_with_state(state_manager, "decline")


def create_list_message_with_state(
    state_manager: Any,
    action: str,
    empty_message: str = None
) -> Dict[str, Any]:
    """Create list selection message enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get required data (StateManager validates)
        channel = state_manager.get("channel")
        flow_data = state_manager.get("flow_data")

        if not flow_data or not flow_data.get("data"):
            raise StateException("Missing flow data")

        # Get items from flow data
        items = flow_data["data"].get("items", [])

        if not items:
            return WhatsAppMessage.create_text(
                channel["identifier"],
                empty_message or f"No {action} offers available"
            )

        message = f"Select offer to {action}:\n\n"
        for i, item in enumerate(items, 1):
            amount = item.get("formattedInitialAmount", "Unknown amount")
            counterparty = item.get("counterpartyAccountName", "Unknown")
            message += f"{i}. {amount} with {counterparty}\n"

        return WhatsAppMessage.create_text(
            channel["identifier"],
            message
        )
    except StateException as e:
        raise ValueError(str(e))
