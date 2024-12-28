"""Offer flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.messaging.types import (ChannelIdentifier, ChannelType, Message,
                                  MessageRecipient, TextContent)
from core.utils.exceptions import StateException
from core.utils.flow_audit import FlowAuditLogger

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


def get_amount_prompt(state_manager: Any) -> Message:
    """Get amount prompt with strict state validation"""
    try:
        # Let StateManager handle validation
        channel = state_manager.get("channel")
        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel["identifier"]
                )
            ),
            content=TextContent(
                body="Enter amount to offer (e.g. 100 USD):"
            )
        )
    except StateException as e:
        logger.error(f"Amount prompt error: {str(e)}")
        raise


def validate_amount(amount: str) -> Dict[str, Any]:
    """Validate amount input

    Args:
        amount: Amount string to validate

    Returns:
        Dict with validated amount and denomination

    Raises:
        StateException: If validation fails
    """
    if not amount or len(amount.split()) != 2:
        raise StateException("Invalid amount format. Please enter amount and currency (e.g. 100 USD)")

    value, denomination = amount.split()
    try:
        value = float(value)
        if value <= 0:
            raise StateException("Amount must be greater than 0")
    except ValueError:
        raise StateException("Invalid amount value")

    if denomination not in {"USD", "EUR", "GBP"}:
        raise StateException("Invalid currency. Supported: USD, EUR, GBP")

    return {"amount": value, "denomination": denomination}


def store_amount(state_manager: Any, amount: str) -> None:
    """Store validated amount in state

    Args:
        state_manager: State manager instance
        amount: Amount string to validate and store

    Raises:
        StateException: If validation or storage fails
    """
    # Validate amount (raises StateException if invalid)
    amount_data = validate_amount(amount)

    # Let StateManager handle validation and update
    state_manager.update_state({
        "flow_data": {
            "data": {
                "amount_denom": {
                    "amount": amount_data["amount"],
                    "denomination": amount_data["denomination"]
                }
            },
            "current_step": "handle"
        }
    })


def get_handle_prompt(state_manager: Any) -> Message:
    """Get handle prompt with strict state validation"""
    try:
        # Let StateManager handle validation
        channel = state_manager.get("channel")
        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel["identifier"]
                )
            ),
            content=TextContent(
                body="Enter recipient handle:"
            )
        )
    except StateException as e:
        logger.error(f"Handle prompt error: {str(e)}")
        raise


def validate_handle(handle: str) -> str:
    """Validate handle input

    Args:
        handle: Handle string to validate

    Returns:
        Validated handle string

    Raises:
        StateException: If validation fails
    """
    if not handle or len(handle) < 3:
        raise StateException("Handle must be at least 3 characters")
    return handle.strip()


def store_handle(state_manager: Any, handle: str) -> None:
    """Store validated handle in state

    Args:
        state_manager: State manager instance
        handle: Handle string to validate and store

    Raises:
        StateException: If validation or storage fails
    """
    # Validate handle (raises StateException if invalid)
    validated_handle = validate_handle(handle)

    # Let StateManager handle validation and update
    state_manager.update_state({
        "flow_data": {
            "data": {
                "handle": validated_handle
            },
            "current_step": "confirm"
        }
    })


def get_confirmation_message(state_manager: Any) -> Message:
    """Get confirmation message with strict state validation"""
    try:
        # Let StateManager validate all state access
        channel = state_manager.get("channel")
        amount_denom = state_manager.get("flow_data")["data"]["amount_denom"]  # StateManager validates
        handle = state_manager.get("flow_data")["data"]["handle"]  # StateManager validates

        confirmation_text = (
            f"Please confirm offer details:\n\n"
            f"Amount: {amount_denom['amount']} {amount_denom['denomination']}\n"
            f"Recipient: {handle}\n\n"
            f"Reply 'yes' to confirm or 'no' to cancel"
        )

        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel["identifier"]
                )
            ),
            content=TextContent(
                body=confirmation_text
            )
        )

    except StateException as e:
        logger.error(f"Confirmation message error: {str(e)}")
        raise


def complete_offer(state_manager: Any, credex_service: Any) -> Dict[str, Any]:
    """Complete offer flow enforcing SINGLE SOURCE OF TRUTH

    Args:
        state_manager: State manager instance
        credex_service: CredEx service instance

    Returns:
        API response data

    Raises:
        StateException: If offer completion fails
    """
    # Let StateManager validate data structure
    amount_denom = state_manager.get("flow_data")["data"]["amount_denom"]  # StateManager validates
    handle = state_manager.get("flow_data")["data"]["handle"]

    # Make API call
    offer_data = {
        "amount": amount_denom["amount"],
        "denomination": amount_denom["denomination"],
        "handle": handle
    }
    success, response = credex_service['offer_credex'](offer_data)
    if not success:
        error_msg = response.get("message", "Failed to create offer")
        logger.error(f"API call failed: {error_msg}")
        raise StateException(error_msg)

    # Log success
    audit.log_flow_event(
        "offer_flow",
        "completion_success",
        None,
        {
            "channel_id": state_manager.get("channel")["identifier"],
            "amount": amount_denom["amount"],
            "denomination": amount_denom["denomination"],
            "handle": handle
        },
        "success"
    )

    return response


def process_offer_step(
    state_manager: Any,
    step: str,
    input_data: Any = None,
    credex_service: Any = None
) -> Message:
    """Process offer step enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Handle each step (StateManager validates state)
        if step == "amount":
            if input_data:
                store_amount(state_manager, input_data)  # Raises StateException if invalid
                return get_handle_prompt(state_manager)
            return get_amount_prompt(state_manager)

        elif step == "handle":
            if input_data:
                store_handle(state_manager, input_data)  # Raises StateException if invalid
                return get_confirmation_message(state_manager)
            return get_handle_prompt(state_manager)

        elif step == "confirm":
            if not credex_service:
                raise StateException("CredEx service required for confirmation")

            if input_data and input_data.lower() == "yes":
                complete_offer(state_manager, credex_service)  # Raises StateException if fails
                return Message(
                    recipient=MessageRecipient(
                        channel_id=ChannelIdentifier(
                            channel=ChannelType.WHATSAPP,
                            value=state_manager.get("channel")["identifier"]
                        )
                    ),
                    content=TextContent(
                        body="✅ Offer created successfully!"
                    )
                )
            return get_confirmation_message(state_manager)

        else:
            raise StateException(f"Invalid offer step: {step}")

    except StateException as e:
        channel = state_manager.get("channel")
        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel["identifier"]
                )
            ),
            content=TextContent(
                body=f"Error: {str(e)}"
            )
        )
