"""Offer flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, List, Optional

from core.messaging.types import (Button, ChannelIdentifier, ChannelType,
                                  InteractiveContent, InteractiveType, Message,
                                  MessageRecipient, TextContent)
from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ErrorContext
from core.utils.exceptions import StateException
from services.credex.service import get_credex_service

from .steps import cleanup_step_data, process_step

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


def validate_offer_amount(amount: float, denomination: str, state_manager: Any = None) -> None:
    """Validate offer amount based on business rules"""
    if denomination not in VALID_DENOMINATIONS:
        raise StateException("invalid_denomination")

    if amount <= 0:
        raise StateException("invalid_amount")


def validate_offer_handle(handle: str, state_manager: Any) -> None:
    """Validate offer handle based on business rules"""
    if 50 < len(handle) < 3:
        raise StateException("invalid_handle_length")

    # Get flow step data which contains the amount using standard structure
    flow_data = state_manager.get_flow_step_data()
    if not flow_data or not flow_data.get("amount", {}).get("value"):
        raise StateException("missing_amount")

    # Check if handle exists using member service directly
    from services.credex.member import validate_account_handle
    success, response = validate_account_handle(handle, state_manager)
    if not success:
        raise StateException("invalid_handle")

    # Get active account
    active_account = state_manager.get_active_account()
    if not active_account:
        raise StateException("missing_account")

    # Cannot send offer to self
    if handle == active_account["accountHandle"]:
        raise StateException("invalid_handle_self")


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
                    "*💸 What offer amount and denomination?*\n"
                    "- Defaults to USD 💵 `1`, `73932.64` \n"
                    "- Valid denom placement ✨ `54 ZWG`, `ZWG 125.54`\n"
                    f"- Valid denoms 🌐 {', '.join(f'`{d}`' for d in sorted(VALID_DENOMINATIONS))}"
                )

            # Amount validation and state update handled in process_step
            # Just return next prompt
            return create_message(channel_id, "Enter account 💳 handle:")

        elif step == "handle":
            if not input_data:
                return create_message(channel_id, "Enter account 💳 handle:")

            # Handle error message result
            if isinstance(result, Message):
                return result

            # Validate handle based on business rules
            validate_offer_handle(result["handle"], state_manager)

            # Show confirmation with amount and account details
            state = state_manager.get_flow_step_data()
            accounts = state_manager.get("accounts") or []
            target_account = next(
                (acc for acc in accounts if acc["accountHandle"] == result["handle"]),
                None
            )
            if not target_account:
                raise StateException("account_not_found")
            amount_data = state.get("amount", {})
            formatted_amount = f"{amount_data.get('value')} {amount_data.get('denomination')}".strip()
            return create_message(
                channel_id,
                f"*📝 Review your offer:*\n"
                f"💸 Amount: {formatted_amount}\n"
                f"💳 To: {target_account['accountName']} ({target_account['accountHandle']})",
                buttons=[
                    {"id": "confirm", "text": "✅ Confirm"},
                    {"id": "cancel", "text": "❌ Cancel"}
                ]
            )

        elif step == "confirm":
            if not input_data:
                # Re-show confirmation with current data
                state = state_manager.get_flow_step_data()
                accounts = state_manager.get("accounts") or []
                handle = state.get("handle")
                target_account = next(
                    (acc for acc in accounts if acc["accountHandle"] == handle),
                    None
                )
                if not target_account:
                    raise StateException("account_not_found")
                amount_data = state.get("amount", {})
                formatted_amount = f"{amount_data.get('value')} {amount_data.get('denomination')}".strip()
                return create_message(
                    channel_id,
                    f"*📝 Review your offer:*\n"
                    f"💸 Amount: {formatted_amount}\n"
                    f"💳 To: {target_account['accountName']} ({target_account['accountHandle']})",
                    buttons=[
                        {"id": "confirm", "text": "✅ Confirm"},
                        {"id": "cancel", "text": "❌ Cancel"}
                    ]
                )

            # Handle error message result
            if isinstance(result, Message):
                return result

            # Process confirmation result
            if result and result.get("confirmed"):
                # Submit offer through credex service
                credex_service = get_credex_service(state_manager)
                success, response = credex_service["offer_credex"](state_manager)
                if not success:
                    raise StateException("offer_creation_failed")

                # Let state_manager handle completion state with clean data
                clean_data = cleanup_step_data(state_manager, "complete", {
                    "offer_id": response.get("data", {}).get("offer", {}).get("id"),
                    "last_completed": "complete"
                })
                success, error = state_manager.update_state({
                    "flow_data": {
                        "flow_type": "offer",  # Ensure flow type stays as offer
                        "step": 3,  # Move to complete step
                        "current_step": "complete",
                        "data": clean_data
                    }
                })
                if not success:
                    logger.error(
                        "Failed to update completion state",
                        extra={
                            "error": error,
                            "step": "complete"
                        }
                    )
                    raise StateException(f"Failed to update completion state: {error}")

                return create_message(channel_id, "✅ Your request has been processed.")

            # Not confirmed - show confirmation again
            state = state_manager.get_flow_step_data()
            accounts = state_manager.get("accounts") or []
            handle = state.get("handle")
            target_account = next(
                (acc for acc in accounts if acc["accountHandle"] == handle),
                None
            )
            if not target_account:
                raise StateException("account_not_found")
            amount_data = state.get("amount", {})
            formatted_amount = f"{amount_data.get('value')} {amount_data.get('denomination')}".strip()
            return create_message(
                channel_id,
                f"*📝 Review your offer:*\n"
                f"💸 Amount: {formatted_amount}\n"
                f"💳 To: {target_account['accountName']} ({target_account['accountHandle']})",
                buttons=[
                    {"id": "confirm", "text": "✅ Confirm"},
                    {"id": "cancel", "text": "❌ Cancel"}
                ]
            )

        raise StateException("invalid_step")

    except Exception as e:
        # Create proper error context
        error_context = ErrorContext(
            error_type="flow",
            message=str(e),
            step_id=step,
            details={
                "input": input_data,
                "flow_data": state_manager.get("flow_data")
            }
        )
        # Let error handler create proper message
        return ErrorHandler.handle_flow_error(
            state_manager,
            e,
            error_context,
            return_message=True
        )
