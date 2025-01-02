"""Offer flow implementation enforcing SINGLE SOURCE OF TRUTH"""
from typing import Any, Dict, List, Optional

from core.components.input import AmountInput, HandleInput, ConfirmInput
from core.messaging.types import (Button, ChannelIdentifier, ChannelType,
                                  InteractiveContent, InteractiveType, Message,
                                  MessageRecipient, TextContent)
from core.utils.exceptions import FlowException, SystemException
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
        # Get channel ID through state manager
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

            raise FlowException(
                message="Invalid step for prompt",
                step=step,
                action="prompt",
                data={"step": step}
            )

        # Process step with proper component validation
        if step == "amount":
            # Validate amount through component
            amount_component = AmountInput()
            result = amount_component.validate(input_data)
            if "error" in result:
                return create_message(channel_id, result["error"]["message"])

            # Convert to verified data
            amount_data = amount_component.to_verified_data(input_data)

            # Update state with verified data
            state_manager.update_state({
                "flow_data": {
                    "data": amount_data,
                    "step": "handle"
                }
            })

            return create_message(channel_id, "Enter account 💳 handle:")

        elif step == "handle":
            # Validate handle through component
            handle_component = HandleInput()
            result = handle_component.validate(input_data)
            if "error" in result:
                return create_message(channel_id, result["error"]["message"])

            # Convert to verified data
            handle_data = handle_component.to_verified_data(input_data)

            # Get amount from state
            flow_data = state_manager.get_flow_state()
            amount_data = flow_data.get("data", {}).get("amount")
            if not amount_data:
                raise FlowException(
                    message="Missing amount data",
                    step=step,
                    action="validate",
                    data={"step": step}
                )

            # Update state with verified data
            state_manager.update_state({
                "flow_data": {
                    "data": {
                        "amount": amount_data,
                        "handle": handle_data["handle"]
                    },
                    "step": "confirm"
                }
            })

            # Format confirmation message
            return create_message(
                channel_id,
                f"*📝 Review your offer:*\n"
                f"💸 Amount: {amount_data}\n"
                f"💳 To: {handle_data['handle']}",
                buttons=[
                    {"id": "confirm", "text": "✅ Confirm"},
                    {"id": "cancel", "text": "❌ Cancel"}
                ]
            )

        elif step == "confirm":
            # Validate confirmation through component
            confirm_component = ConfirmInput()
            result = confirm_component.validate(input_data)
            if "error" in result:
                return create_message(channel_id, result["error"]["message"])

            # Convert to verified data
            confirm_data = confirm_component.to_verified_data(input_data)

            if confirm_data["confirmed"]:
                # Get flow data
                flow_data = state_manager.get_flow_state()
                offer_data = flow_data.get("data", {})

                if not offer_data.get("amount") or not offer_data.get("handle"):
                    raise FlowException(
                        message="Missing offer data",
                        step=step,
                        action="validate",
                        data={"step": step}
                    )

                try:
                    # Submit through service layer
                    credex_service = get_credex_service(state_manager)
                    success, response = credex_service["offer_credex"](state_manager)

                    if not success:
                        raise SystemException(
                            message=response.get("message", "Failed to create offer"),
                            code="OFFER_CREATE_FAILED",
                            service="credex",
                            action="create_offer"
                        )

                    # Update state with completion
                    state_manager.update_state({
                        "flow_data": {
                            "data": {
                                **offer_data,
                                "offer_id": response["offer_id"]
                            },
                            "step": "complete"
                        }
                    })

                    return create_message(channel_id, "✅ Your request has been processed.")

                except (FlowException, SystemException):
                    # Let flow and system errors propagate up
                    raise
                except Exception as e:
                    raise SystemException(
                        message=str(e),
                        code="OFFER_ERROR",
                        service="credex",
                        action="create_offer"
                    )

            # Show confirmation again if not confirmed
            flow_data = state_manager.get_flow_state()
            offer_data = flow_data.get("data", {})

            return create_message(
                channel_id,
                f"*📝 Review your offer:*\n"
                f"💸 Amount: {offer_data.get('amount')}\n"
                f"💳 To: {offer_data.get('handle')}",
                buttons=[
                    {"id": "confirm", "text": "✅ Confirm"},
                    {"id": "cancel", "text": "❌ Cancel"}
                ]
            )

        raise FlowException(
            message="Invalid step",
            step=step,
            action="process",
            data={"step": step}
        )

    except (FlowException, SystemException):
        # Let flow and system errors propagate up
        raise
    except Exception as e:
        raise SystemException(
            message=str(e),
            code="FLOW_ERROR",
            service="offer_flow",
            action=step
        )
