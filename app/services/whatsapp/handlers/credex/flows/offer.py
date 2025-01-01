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

from .constants import VALID_DENOMINATIONS
from .steps import process_step

logger = logging.getLogger(__name__)


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


def process_offer_step(state_manager: Any, step: str, input_data: Any = None) -> Message:
    """Process offer step and return appropriate message"""
    try:
        # Get channel ID for messages
        channel_id = state_manager.get("channel")["identifier"]

        # Handle initial prompts
        if not input_data:
            if step == "amount":
                return create_message(
                    channel_id,
                    "*💸 What offer amount and denomination?*\n"
                    "- Defaults to USD 💵 `1`, `73932.64` \n"
                    "- Valid denom placement ✨ `54 ZWG`, `ZWG 125.54`\n"
                    f"- Valid denoms 🌐 {', '.join(f'`{d}`' for d in sorted(VALID_DENOMINATIONS))}"
                )
            elif step == "handle":
                return create_message(channel_id, "Enter account 💳 handle:")
            elif step == "complete":
                return create_message(channel_id, "✅ Your offer has been sent.")

        # Return step-specific messages
        if step == "amount":
            # Process input through StateManager
            process_step(state_manager, step, input_data)

            # Get validated state
            flow_data = state_manager.get("flow_data")

            # Update step after processing amount
            state_manager.update_state({
                "flow_data": {
                    "step": 2,
                    "current_step": "handle"
                }
            })
            return create_message(channel_id, "Enter account 💳 handle:")

        elif step == "handle":
            # Process input through StateManager
            process_step(state_manager, step, input_data)

            # Get validated state
            flow_data = state_manager.get("flow_data")

            # Get account details from validated state
            accounts = state_manager.get("accounts") or []
            handle = flow_data["data"]["handle"]
            target_account = next(
                (acc for acc in accounts if acc["accountHandle"] == handle),
                None
            )

            if not target_account:
                raise StateException(f"Account not found: {handle}")

            # Show confirmation with validated data
            amount_data = flow_data["data"]["amount"]
            formatted_amount = f"{amount_data['value']} {amount_data['denomination']}".strip()

            # Update step before returning message
            state_manager.update_state({
                "flow_data": {
                    "step": 3,
                    "current_step": "confirm"
                }
            })

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
            # Process input through StateManager
            process_step(state_manager, step, input_data)

            # Get validated state
            flow_data = state_manager.get("flow_data")

            # Submit offer if confirmed
            if flow_data["data"].get("confirmed"):
                # Get active account for issuer ID
                active_account = state_manager.get_active_account()

                # Build offer data
                offer_data = {
                    "amount": flow_data["data"]["amount"],
                    "handle": flow_data["data"]["handle"],
                    "issuerAccountID": active_account["accountID"]
                }

                # Update state with offer data
                state_manager.update_state({
                    "flow_data": {
                        "data": offer_data
                    }
                })

                # Submit through service layer
                credex_service = get_credex_service(state_manager)
                success, response = credex_service["offer_credex"](offer_data)

                if not success:
                    error_msg = response["message"] if isinstance(response, dict) else str(response)
                    raise StateException(f"Failed to create offer: {error_msg}")

                # Parse response
                try:
                    if isinstance(response, dict) and "data" in response and "offer" in response["data"]:
                        offer_id = response["data"]["offer"]["id"]
                    else:
                        raise ValueError("Invalid response format")
                except (KeyError, ValueError) as e:
                    raise StateException(f"Invalid offer response: {str(e)}")

                # Update step and state with result
                state_manager.update_state({
                    "flow_data": {
                        "step": 4,
                        "current_step": "complete",
                        "data": {
                            "offer_id": offer_id
                        }
                    }
                })

                return create_message(channel_id, "✅ Your request has been processed.")

            # Show confirmation again if not confirmed
            amount_data = flow_data["data"]["amount"]
            formatted_amount = f"{amount_data['value']} {amount_data['denomination']}".strip()
            accounts = state_manager.get("accounts") or []
            handle = flow_data["data"]["handle"]
            target_account = next(
                (acc for acc in accounts if acc["accountHandle"] == handle),
                None
            )

            if not target_account:
                raise StateException(f"Account not found: {handle}")

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
        # Let ErrorHandler create proper message
        return ErrorHandler.handle_flow_error(
            state_manager,
            e,
            ErrorContext(
                error_type="flow",
                message=str(e),
                step_id=step,
                details={
                    "input": input_data,
                    "flow_data": state_manager.get("flow_data")
                }
            ),
            return_message=True
        )
