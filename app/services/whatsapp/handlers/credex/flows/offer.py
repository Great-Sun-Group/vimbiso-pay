"""Offer flow implementation enforcing SINGLE SOURCE OF TRUTH

The flow maintains two step tracking fields that serve distinct purposes:

1. step (integer):
    - Required by framework for validation and progression tracking
    - Starts at 0 and increments with each step (0 -> 1 -> 2)
    - Used by StateManager to validate flow progression

2. current_step (string):
    - Used for flow-specific routing and logic
    - Maps to specific validation rules and message handlers
    - Example: "amount" -> "handle" -> "confirm"
"""
import logging
from typing import Any, Dict

from core.messaging.types import (ChannelIdentifier, ChannelType, Message,
                                  MessageRecipient, TextContent)
from core.utils.error_handler import ErrorContext, ErrorHandler
from core.utils.exceptions import StateException

logger = logging.getLogger(__name__)

# Valid denominations from prompt examples
VALID_DENOMINATIONS = {"USD", "ZWG", "XAU", "CAD"}


def _create_message(state_manager: Any, body: str) -> Message:
    """Create message through state validation"""
    try:
        channel = state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            raise StateException("Invalid channel state")

        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel["identifier"]
                )
            ),
            content=TextContent(body=body)
        )
    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message="Failed to create message",
            details={"error": str(e)}
        )
        ErrorHandler.handle_error(e, state_manager, error_context)
        raise


def get_amount_prompt(state_manager: Any) -> Message:
    """Get amount prompt through state validation"""
    try:
        return _create_message(
            state_manager,
            "How much would you like to offer? Your response defaults to USD unless otherwise indicated. "
            "Valid examples: `1`, `5`, `3.23`, `53.22 ZWG`, `ZWG 5384.54`, `0.04 XAU`, `CAD 5.18`"
        )
    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message=str(e),
            step_id="amount"
        )
        ErrorHandler.handle_error(e, state_manager, error_context)
        raise


def validate_amount(amount: str) -> Dict[str, Any]:
    """Validate amount through state validation"""
    try:
        parts = amount.split()
        if not amount or len(parts) > 2:
            raise StateException(
                "Invalid amount format. Please enter amount with optional denomination "
                "(e.g. 100 or 100 USD or USD 100)"
            )

        # Parse amount and denomination
        if len(parts) == 1:
            value, denomination = parts[0], "USD"
        else:
            first, second = parts
            if first.upper() in VALID_DENOMINATIONS:
                denomination, value = first.upper(), second
            else:
                value, denomination = first, second.upper()

        # Validate amount value
        try:
            value = float(value)
            if value <= 0:
                raise StateException("Amount must be greater than 0")
        except ValueError:
            raise StateException("Invalid amount value. Please enter a valid number")

        # Validate denomination
        if denomination not in VALID_DENOMINATIONS:
            raise StateException(
                f"Invalid denomination. Supported: {', '.join(sorted(VALID_DENOMINATIONS))}"
            )

        return {"amount": value, "denomination": denomination}

    except StateException:
        raise
    except Exception as e:
        raise StateException(f"Failed to validate amount: {str(e)}")


def store_amount(state_manager: Any, amount: str) -> None:
    """Store amount through state validation"""
    try:
        # Validate amount
        amount_data = validate_amount(amount)

        # Update state through validation
        state_update = {
            "flow_data": {
                "data": {"amount_denom": amount_data},
                "step_validation": {
                    "current_step": "amount",
                    "input": amount
                }
            }
        }

        success, error = state_manager.update_state(state_update)
        if not success:
            raise StateException(f"Failed to store amount: {error}")

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message=str(e),
            step_id="amount",
            details={"input": amount}
        )
        ErrorHandler.handle_error(e, state_manager, error_context)
        raise


def get_handle_prompt(state_manager: Any) -> Message:
    """Get handle prompt through state validation"""
    try:
        return _create_message(state_manager, "Enter recipient handle:")
    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message=str(e),
            step_id="handle"
        )
        ErrorHandler.handle_error(e, state_manager, error_context)
        raise


def store_handle(state_manager: Any, handle: str) -> None:
    """Store handle through state validation"""
    try:
        # Validate handle
        if not handle or len(handle.strip()) < 3:
            raise StateException("Handle must be at least 3 characters")

        # Update state through validation
        state_update = {
            "flow_data": {
                "data": {"handle": handle.strip()},
                "step_validation": {
                    "current_step": "handle",
                    "input": handle
                }
            }
        }

        success, error = state_manager.update_state(state_update)
        if not success:
            raise StateException(f"Failed to store handle: {error}")

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message=str(e),
            step_id="handle",
            details={"input": handle}
        )
        ErrorHandler.handle_error(e, state_manager, error_context)
        raise


def get_confirmation_message(state_manager: Any) -> Message:
    """Get confirmation through state validation"""
    try:
        # Get validated flow data
        flow_data = state_manager.get("flow_data")
        if not flow_data or not flow_data.get("data"):
            raise StateException("Missing flow data")

        data = flow_data["data"]
        amount_data = data.get("amount_denom", {})
        handle = data.get("handle")

        if not amount_data or not handle:
            raise StateException("Missing offer details")

        # Create confirmation message
        confirmation_text = (
            f"Please confirm offer details:\n\n"
            f"Amount: {amount_data['amount']} {amount_data['denomination']}\n"
            f"Recipient: {handle}\n\n"
            f"Reply 'yes' to confirm or 'no' to cancel"
        )

        return _create_message(state_manager, confirmation_text)

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message=str(e),
            step_id="confirm"
        )
        ErrorHandler.handle_error(e, state_manager, error_context)
        raise


def complete_offer(state_manager: Any, credex_service: Any) -> Dict[str, Any]:
    """Complete offer through state validation"""
    try:
        # Get validated flow data
        flow_data = state_manager.get("flow_data")
        if not flow_data or not flow_data.get("data"):
            raise StateException("Missing flow data")

        # Submit offer
        success, response = credex_service["offer_credex"](flow_data["data"])
        if not success:
            raise StateException(response.get("message", "Failed to create offer"))

        # Log success
        logger.info(
            "Offer created successfully",
            extra={
                "channel_id": state_manager.get("channel", {}).get("identifier"),
                "response": response
            }
        )

        return response

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message=str(e),
            step_id="confirm",
            details={"operation": "complete_offer"}
        )
        ErrorHandler.handle_error(e, state_manager, error_context)
        raise


def process_offer_step(
    state_manager: Any,
    step: str,
    input_data: Any = None
) -> Message:
    """Process offer step through state validation"""
    try:
        # Validate step transition
        state_update = {
            "flow_data": {
                "step_validation": {
                    "current_step": step,
                    "has_input": bool(input_data)
                }
            }
        }

        success, error = state_manager.update_state(state_update)
        if not success:
            raise StateException(f"Invalid step transition: {error}")

        # Process step
        if step == "amount":
            if input_data:
                store_amount(state_manager, input_data)
                return get_handle_prompt(state_manager)
            return get_amount_prompt(state_manager)

        elif step == "handle":
            if input_data:
                store_handle(state_manager, input_data)
                return get_confirmation_message(state_manager)
            return get_handle_prompt(state_manager)

        elif step == "confirm":
            if input_data and input_data.lower() == "yes":
                # Get credex service
                from services.credex.service import get_credex_service
                credex_service = get_credex_service(state_manager)

                # Complete offer
                complete_offer(state_manager, credex_service)
                return _create_message(state_manager, "✅ Offer created successfully!")

            return get_confirmation_message(state_manager)

        raise StateException(f"Invalid step: {step}")

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message=str(e),
            step_id=step,
            details={
                "input": input_data,
                "operation": "process_step"
            }
        )
        ErrorHandler.handle_error(e, state_manager, error_context)

        # Return error message
        return _create_message(
            state_manager,
            f"❌ {str(e)}"
        )
