"""Offer flow implementation enforcing SINGLE SOURCE OF TRUTH

The flow maintains two step tracking fields in its state that serve distinct but complementary purposes:

1. step (integer):
    - Required by framework for validation and progression tracking
    - Starts at 0 and increments with each step (0 -> 1 -> 2)
    - Used by StateManager to validate flow progression
    - Enables audit logging with clear step sequence
    - Example: step: 0 for amount input, 1 for handle input, 2 for confirmation

2. current_step (string):
    - Used for flow-specific routing and logic
    - Provides semantic meaning to each step
    - Maps to specific validation rules and message handlers
    - Makes code more readable and maintainable
    - Example: current_step: "amount" -> "handle" -> "confirm"
"""
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
                body="How much would you like to offer? Your response defaults to USD unless otherwise indicated. Valid examples: `1`, `5`, `3.23`, `53.22 ZWG`, `ZWG 5384.54`, `0.04 XAU`, `CAD 5.18`"
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
    # All denominations from prompt examples are valid
    valid_denominations = {"USD", "ZWG", "XAU", "CAD"}

    # Handle single number as USD
    parts = amount.split()
    if not amount or len(parts) > 2:
        raise StateException("Invalid amount format. Enter amount with optional denomination (e.g. 100 or 100 USD or USD 100)")

    if len(parts) == 1:
        value = parts[0]
        denomination = "USD"  # Default to USD
    else:
        # Try both denomination positions
        first, second = parts
        # Check if first part is a valid denomination
        if first.upper() in valid_denominations:
            denomination = first.upper()
            value = second
        else:
            value = first
            denomination = second.upper()

    try:
        value = float(value)
        if value <= 0:
            raise StateException("Amount must be greater than 0")
    except ValueError:
        raise StateException("Invalid amount value")

    # Validate final denomination
    if denomination not in valid_denominations:
        raise StateException(f"Invalid denomination. Supported: {', '.join(sorted(valid_denominations))}")

    return {"amount": value, "denomination": denomination}


def store_amount(state_manager: Any, amount: str) -> bool:
    """Store validated amount in state

    Args:
        state_manager: State manager instance
        amount: Amount string to validate and store

    Returns:
        bool: True if storage successful

    Raises:
        StateException: If validation or storage fails
    """
    logger.debug(f"Validating amount: {amount}")

    # Validate amount (raises StateException if invalid)
    amount_data = validate_amount(amount)
    logger.debug(f"Amount validated: {amount_data}")

    # Let StateManager validate structure and preserve flow metadata
    success, error = state_manager.update_state({
        "flow_data": {
            "data": {  # Only update data
                "amount_denom": amount_data
            }
        }
    })
    if not success:
        raise StateException(f"Failed to store amount: {error}")

    logger.debug("Amount stored successfully")
    return True  # Indicate successful storage


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


def validate_account_handle(handle: str) -> str:
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


def store_handle(state_manager: Any, handle: str) -> bool:
    """Store validated handle in state

    Args:
        state_manager: State manager instance
        handle: Handle string to validate and store

    Returns:
        bool: True if storage successful

    Raises:
        StateException: If validation or storage fails
    """
    logger.debug(f"Validating handle: {handle}")

    # Validate handle (raises StateException if invalid)
    validated_handle = validate_account_handle(handle)
    logger.debug(f"Handle validated: {validated_handle}")

    # Let StateManager validate structure and preserve flow metadata
    success, error = state_manager.update_state({
        "flow_data": {
            "data": {  # Only update data
                "handle": validated_handle
            }
        }
    })
    if not success:
        raise StateException(f"Failed to store handle: {error}")

    logger.debug("Handle stored successfully")
    return True  # Indicate successful storage


def get_confirmation_message(state_manager: Any) -> Message:
    """Get confirmation message with strict state validation"""
    try:
        # Let StateManager validate and use state directly
        channel = state_manager.get("channel")
        flow_data = state_manager.get("flow_data")["data"]  # StateManager validates

        # Use state directly in template
        confirmation_text = (
            f"Please confirm offer details:\n\n"
            f"Amount: {flow_data['amount_denom']['amount']} {flow_data['amount_denom']['denomination']}\n"
            f"Recipient: {flow_data['handle']}\n\n"
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
    # Let StateManager validate and pass state directly
    flow_data = state_manager.get("flow_data")["data"]  # StateManager validates
    success, response = credex_service['offer_credex'](flow_data)
    if not success:
        error_msg = response.get("message", "Failed to create offer")
        logger.error(f"API call failed: {error_msg}")
        raise StateException(error_msg)

    # Log success with direct state
    audit.log_flow_event(
        "offer_flow",
        "completion_success",
        None,
        {
            "channel_id": state_manager.get("channel")["identifier"],
            **flow_data  # Pass state directly without transformation
        },
        "success"
    )

    return response


def process_offer_step(
    state_manager: Any,
    step: str,
    input_data: Any = None
) -> Message:
    """Process offer step enforcing SINGLE SOURCE OF TRUTH

    The flow progresses through steps using both numeric and named identifiers:
    - step 0 ("amount"): Collect and validate offer amount
    - step 1 ("handle"): Collect and validate recipient handle
    - step 2 ("confirm"): Confirm offer details
    """
    try:
        logger.debug(f"Processing offer step: '{step}' with input: '{input_data}'")

        # Handle each step (StateManager validates state)
        if step == "amount":
            if input_data:
                logger.debug(f"Storing amount: {input_data}")

                # Store amount data
                store_amount(state_manager, input_data)  # Raises StateException if invalid
                logger.debug("Amount stored successfully")

                # Advance to next step using StateManager.update_state
                flow_data = state_manager.get("flow_data")
                success, error = state_manager.update_state({
                    "flow_data": {
                        "flow_type": flow_data["flow_type"],
                        "step": flow_data["step"] + 1,
                        "current_step": "handle"
                    }
                })
                if not success:
                    raise StateException(f"Failed to advance flow: {error}")
                logger.debug("Flow state updated, getting handle prompt")

                return get_handle_prompt(state_manager)
            logger.debug("No input data, getting amount prompt")
            return get_amount_prompt(state_manager)

        elif step == "handle":
            if input_data:
                # Store handle data
                store_handle(state_manager, input_data)  # Raises StateException if invalid
                logger.debug("Handle stored successfully")

                # Advance to next step using StateManager.update_state
                flow_data = state_manager.get("flow_data")
                success, error = state_manager.update_state({
                    "flow_data": {
                        "flow_type": flow_data["flow_type"],
                        "step": flow_data["step"] + 1,
                        "current_step": "confirm"
                    }
                })
                if not success:
                    raise StateException(f"Failed to advance flow: {error}")
                logger.debug("Flow state updated, getting confirmation message")

                return get_confirmation_message(state_manager)
            return get_handle_prompt(state_manager)

        elif step == "confirm":
            if input_data and input_data.lower() == "yes":
                # Get credex service through state validation
                from services.credex.service import get_credex_service
                credex_service = get_credex_service(state_manager)

                # Complete offer through state update
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
