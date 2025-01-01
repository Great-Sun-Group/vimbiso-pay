"""Offer flow implementation enforcing SINGLE SOURCE OF TRUTH"""
from typing import Any, Dict, List, Optional

from core.messaging.types import (Button, ChannelIdentifier, ChannelType,
                                  InteractiveContent, InteractiveType, Message,
                                  MessageRecipient, TextContent)
from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ErrorContext
from core.utils.exceptions import StateException
from services.credex.service import get_credex_service

from .constants import VALID_DENOMINATIONS


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
        # Let StateManager validate channel
        state_manager.update_state({
            "validation": {
                "type": "channel",
                "required": True
            }
        })

        # Get validated channel data
        channel_id = state_manager.get_channel_id()

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
            # Let StateManager validate amount input
            state_manager.update_state({
                "validation": {
                    "type": "amount_input",
                    "input": input_data,
                    "denominations": list(VALID_DENOMINATIONS)
                }
            })

            # Get validated amount data
            amount_data = state_manager.get_amount_data()

            # Update step after validation
            state_manager.update_state({
                "validation": {
                    "type": "step_update",
                    "step": 2,
                    "current_step": "handle"
                }
            })

            return create_message(channel_id, "Enter account 💳 handle:")

        elif step == "handle":
            # Let StateManager validate handle input
            state_manager.update_state({
                "validation": {
                    "type": "handle_input",
                    "input": input_data
                }
            })

            # Get validated handle data
            handle_data = state_manager.get_handle_data()

            # Show confirmation with validated data
            amount_data = handle_data["amount"]
            formatted_amount = f"{amount_data['value']} {amount_data['denomination']}".strip()

            # Update step before returning message
            state_manager.update_state({
                "validation": {
                    "type": "step_update",
                    "step": 3,
                    "current_step": "confirm"
                }
            })

            return create_message(
                channel_id,
                f"*📝 Review your offer:*\n"
                f"💸 Amount: {formatted_amount}\n"
                f"💳 To: {handle_data['account_name']} ({handle_data['account_handle']})",
                buttons=[
                    {"id": "confirm", "text": "✅ Confirm"},
                    {"id": "cancel", "text": "❌ Cancel"}
                ]
            )

        elif step == "confirm":
            # Let StateManager validate confirmation input
            state_manager.update_state({
                "validation": {
                    "type": "confirmation_input",
                    "input": input_data
                }
            })

            # Get validated confirmation data
            confirmation_data = state_manager.get_confirmation_data()

            # Submit offer if confirmed
            if confirmation_data["confirmed"]:
                # Let StateManager assemble offer data
                state_manager.update_state({
                    "validation": {
                        "type": "offer_assembly"
                    }
                })

                # Submit through service layer
                credex_service = get_credex_service(state_manager)
                success, response = credex_service["offer_credex"](state_manager)

                if not success:
                    error_msg = response["message"] if isinstance(response, dict) else str(response)
                    raise StateException(f"Failed to create offer: {error_msg}")

                # Let StateManager validate response
                state_manager.update_state({
                    "validation": {
                        "type": "offer_response",
                        "response": response
                    }
                })

                # Get validated offer ID
                offer_id = state_manager.get_offer_id()

                # Update step with completion
                state_manager.update_state({
                    "validation": {
                        "type": "step_complete",
                        "step": 4,
                        "current_step": "complete",
                        "offer_id": offer_id
                    }
                })

                return create_message(channel_id, "✅ Your request has been processed.")

            # Show confirmation again if not confirmed
            handle_data = state_manager.get_handle_data()
            amount_data = handle_data["amount"]
            formatted_amount = f"{amount_data['value']} {amount_data['denomination']}".strip()

            return create_message(
                channel_id,
                f"*📝 Review your offer:*\n"
                f"💸 Amount: {formatted_amount}\n"
                f"💳 To: {handle_data['account_name']} ({handle_data['account_handle']})",
                buttons=[
                    {"id": "confirm", "text": "✅ Confirm"},
                    {"id": "cancel", "text": "❌ Cancel"}
                ]
            )

        raise StateException("invalid_step")

    except Exception as e:
        # Let ErrorHandler create proper message with context
        return ErrorHandler.handle_flow_error(
            state_manager,
            e,
            ErrorContext(
                error_type="flow",
                message=str(e),
                step_id=step,
                details={
                    "input": input_data,
                    "flow_type": "offer"
                }
            ),
            return_message=True
        )
