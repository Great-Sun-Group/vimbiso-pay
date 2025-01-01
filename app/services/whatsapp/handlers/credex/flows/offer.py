"""Offer flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, List, Optional

from core.messaging.types import (Button, ChannelIdentifier, ChannelType, InteractiveContent,
                                  InteractiveType, Message, MessageRecipient, TextContent)
from core.utils.exceptions import StateException
from services.credex.service import get_credex_service

from .steps import process_step

logger = logging.getLogger(__name__)

# Valid denominations for offers
VALID_DENOMINATIONS = {"USD", "ZWG", "XAU", "CAD"}


def create_message(channel_id: str, text: str, buttons: Optional[List[Dict[str, str]]] = None) -> Message:
    """Create core message type with optional buttons"""
    recipient = MessageRecipient(
        channel_id=ChannelIdentifier(
            channel=ChannelType.WHATSAPP,
            value=channel_id
        )
    )

    if buttons:
        # Convert button dicts to Button objects
        button_objects = [
            Button(id=btn["id"], title=btn["text"])
            for btn in buttons
        ]
        return Message(
            recipient=recipient,
            content=InteractiveContent(
                interactive_type=InteractiveType.BUTTON,
                body=text,
                buttons=button_objects
            )
        )

    return Message(
        recipient=recipient,
        content=TextContent(body=text)
    )


def validate_offer_amount(amount: float, denomination: str) -> None:
    """Validate offer amount based on business rules"""
    if denomination not in VALID_DENOMINATIONS:
        raise StateException(f"Invalid denomination. Supported: {', '.join(sorted(VALID_DENOMINATIONS))}")

    if amount <= 0:
        raise StateException("Amount must be greater than 0")


def validate_offer_handle(handle: str, state_manager: Any) -> None:
    """Validate offer handle based on business rules"""
    if 50 < len(handle) < 3:
        raise StateException("Handle must be between 3 and 50 characters")

    try:
        # Check if handle exists
        credex_service = get_credex_service(state_manager)
        success, response = credex_service["validate_account_handle"](handle)
        if not success:
            error_msg = response.get("message") if isinstance(response, dict) else str(response)
            raise StateException(error_msg or "Sorry, no account found with that handle. Please try again.")

        # Get active account
        active_account = state_manager.get_active_account()
        if not active_account:
            raise StateException("No active account found")

        # Cannot send offer to self
        if handle == active_account["accountHandle"]:
            raise StateException("Cannot send offer to originating account")

    except Exception as e:
        logger.error(
            "Error validating offer handle",
            extra={
                "error": str(e),
                "handle": handle,
                "state": state_manager.get("flow_data")
            }
        )
        raise StateException(str(e))


def process_offer_step(state_manager: Any, step: str, input_data: Any = None) -> Message:
    """Process offer step with validation"""
    try:
        # Get channel ID through state manager
        channel_id = state_manager.get("channel")["identifier"]

        # Process step input through generic step processor
        result = process_step(state_manager, step, input_data)

        # Initial prompts or responses based on step
        if step == "amount":
            if not input_data:
                return create_message(
                    channel_id,
                    "💸 **What offer amount and denomination?**\n"
                    "💵 Defaults to USD: `1`, `73932.64` \n"
                    "✨ Valid denom placement: `54 ZWG`, `ZWG 125.54`\n"
                    f"🌐 Valid denoms: {', '.join(f'`{d}`' for d in sorted(VALID_DENOMINATIONS))}"
                )

            # Amount validation and state update handled in process_step
            # Just return next prompt
            return create_message(channel_id, "Enter account 💳 handle:")

        elif step == "handle":
            if not input_data:
                return create_message(channel_id, "Enter account 💳 handle:")

            # Validate handle based on business rules
            validate_offer_handle(result["handle"], state_manager)

            # Show confirmation with amount and handle
            state = state_manager.get_flow_step_data()
            amount = state["amount"]
            handle = result["handle"]
            formatted_amount = f"{amount['amount']} {amount['denomination']}".strip()
            return create_message(
                channel_id,
                f"📝 Review your offer:\n"
                f"💸 Amount: {formatted_amount}\n"
                f"💳 To: {handle}",
                buttons=[
                    {"id": "confirm", "text": "✅ Confirm"},
                    {"id": "cancel", "text": "❌ Cancel"}
                ]
            )

        elif step == "confirm":
            if not input_data:
                # Re-show confirmation with current data
                state = state_manager.get_flow_step_data()
                amount = state["amount"]
                handle = state["handle"]
                formatted_amount = f"{amount['amount']} {amount['denomination']}".strip()
                # Re-show confirmation with buttons
                return create_message(
                    channel_id,
                    f"📝 Review your offer:\n"
                    f"💸 Amount: {formatted_amount}\n"
                    f"💳 To: {handle}",
                    buttons=[
                        {"id": "confirm", "text": "✅ Confirm"},
                        {"id": "cancel", "text": "❌ Cancel"}
                    ]
                )

            # Process confirmation result
            if result["confirmed"]:
                try:
                    # Submit offer
                    credex_service = get_credex_service(state_manager)
                    success, response = credex_service["offer_credex"](
                        state_manager.get_flow_step_data()
                    )
                    if not success:
                        raise StateException(response.get("message", "Failed to create offer"))

                    # Update flow state to mark completion
                    flow_data = state_manager.get("flow_data") or {}
                    current_step = flow_data.get("step", 0)
                    state_manager.update_state({
                        "flow_data": {
                            "flow_type": flow_data.get("flow_type", "offer"),
                            "step": current_step + 1,  # Final step increment
                            "current_step": "complete",
                            "data": {
                                **(flow_data.get("data", {})),
                                "offer_id": response.get("data", {}).get("offer", {}).get("id"),
                                "last_completed": "complete"
                            }
                        }
                    })

                    # Log success
                    logger.info(
                        "Offer created successfully",
                        extra={
                            "channel_id": channel_id,
                            "response": response,
                            "flow_state": state_manager.get("flow_data")
                        }
                    )
                    return create_message(channel_id, "✅ Your request has been processed.")

                except Exception as e:
                    # Ensure flow stays in confirm step on error
                    flow_data = state_manager.get("flow_data") or {}
                    state_manager.update_state({
                        "flow_data": {
                            "flow_type": flow_data.get("flow_type", "offer"),
                            "step": flow_data.get("step", 0),  # Don't increment on error
                            "current_step": "confirm",
                            "data": {
                                **(flow_data.get("data", {})),  # Preserve existing data
                                "error": str(e)
                            }
                        }
                    })
                    raise

            # Not confirmed - show confirmation again
            state = state_manager.get_flow_step_data()
            amount = state["amount"]
            handle = state["handle"]
            formatted_amount = f"{amount['amount']} {amount['denomination']}".strip()
            # Show confirmation with buttons again
            return create_message(
                channel_id,
                f"📝 Review your offer:\n"
                f"💸 Amount: {formatted_amount}\n"
                f"💳 To: {handle}",
                buttons=[
                    {"id": "confirm", "text": "✅ Confirm"},
                    {"id": "cancel", "text": "❌ Cancel"}
                ]
            )

        raise StateException(f"Invalid step: {step}")

    except Exception as e:
        # Add error context and let it propagate up
        logger.error(
            "Error in offer flow",
            extra={
                "error": str(e),
                "step": step,
                "flow_data": state_manager.get("flow_data")
            }
        )
        raise StateException(str(e))
