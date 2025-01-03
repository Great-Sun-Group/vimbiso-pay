"""Credex flows using clean architecture patterns

Components handle UI validation
Services handle business logic
Flows coordinate the process
"""

import logging
from typing import Any, Dict, Optional

from core.messaging.interface import MessagingServiceInterface
from core.messaging.types import Message, MessageRecipient
from core.utils.exceptions import FlowException, SystemException
from core.components.input import (
    AmountInput,
    HandleInput,
    ConfirmInput,
    SelectInput
)
from services.credex.service import get_credex_service

logger = logging.getLogger(__name__)


class CredexFlow:
    """Base class for credex-related flows"""

    def __init__(self, messaging_service: MessagingServiceInterface):
        self.messaging = messaging_service

    def get_step_content(self, step: str, data: Optional[Dict] = None) -> str:
        """Get step content without channel formatting"""
        raise NotImplementedError("Flow must implement get_step_content")

    def process_step(self, state_manager: Any, step: str, input_value: Any) -> Message:
        """Process flow step using messaging service"""
        raise NotImplementedError("Flow must implement process_step")

    def _get_recipient(self, state_manager: Any) -> MessageRecipient:
        """Get message recipient from state"""
        return MessageRecipient(
            channel_id=state_manager.get_channel_id(),
            member_id=state_manager.get("member_id")
        )


class OfferFlow(CredexFlow):
    """Credex offer flow using clean architecture"""

    def get_step_content(self, step: str, data: Optional[Dict] = None) -> str:
        """Get offer step content"""
        if step == "amount":
            return (
                "💸 What offer amount and denomination?\n"
                "- Defaults to USD 💵 (1, 73932.64)\n"
                "- Valid denom placement ✨ (54 ZWG, ZWG 125.54)"
            )
        elif step == "handle":
            return "Enter account 💳 handle:"
        elif step == "confirm":
            if data:
                return (
                    "📝 Review your offer:\n"
                    f"💸 Amount: {data.get('amount')}\n"
                    f"💳 To: {data.get('handle')}"
                )
            return "Please confirm your offer (yes/no):"
        elif step == "complete":
            return "✅ Your offer has been sent."
        return ""

    def process_step(self, state_manager: Any, step: str, input_value: Any) -> Message:
        """Process offer step using clean architecture patterns"""
        try:
            recipient = self._get_recipient(state_manager)
            credex_service = get_credex_service(state_manager)

            if step == "amount":
                # UI validation
                component = AmountInput()
                validation = component.validate(input_value)
                if not validation.valid:
                    return self.messaging.send_text(
                        recipient=recipient,
                        text=f"❌ {validation.error['message']}"
                    )

                # Update component state
                state_manager.update_state({
                    "flow_data": {
                        "active_component": component.get_ui_state(),
                        "data": {"amount": validation.value}
                    }
                })

                # Move to next step
                return self.messaging.send_text(
                    recipient=recipient,
                    text=self.get_step_content("handle")
                )

            elif step == "handle":
                # UI validation
                component = HandleInput()
                validation = component.validate(input_value)
                if not validation.valid:
                    return self.messaging.send_text(
                        recipient=recipient,
                        text=f"❌ {validation.error['message']}"
                    )

                # Business validation
                success, result = credex_service["validate_account_handle"](validation.value)
                if not success:
                    return self.messaging.send_text(
                        recipient=recipient,
                        text=f"❌ {result['message']}"
                    )

                # Update component and flow state
                state_manager.update_state({
                    "flow_data": {
                        "active_component": component.get_ui_state(),
                        "data": {
                            **state_manager.get_flow_data(),
                            "handle": validation.value
                        }
                    }
                })

                # Show confirmation
                flow_data = state_manager.get_flow_data()
                return self.messaging.send_text(
                    recipient=recipient,
                    text=self.get_step_content("confirm", {
                        "amount": flow_data.get("amount"),
                        "handle": validation.value
                    })
                )

            elif step == "confirm":
                # UI validation
                component = ConfirmInput()
                validation = component.validate(input_value)
                if not validation.valid:
                    return self.messaging.send_text(
                        recipient=recipient,
                        text=f"❌ {validation.error['message']}"
                    )

                # Only proceed if confirmed
                if not validation.value:
                    return self.messaging.send_text(
                        recipient=recipient,
                        text="❌ Offer cancelled."
                    )

                # Submit through service
                flow_data = state_manager.get_flow_data()
                success, result = credex_service["offer_credex"]({
                    "amount": flow_data.get("amount"),
                    "handle": flow_data.get("handle")
                })

                if not success:
                    return self.messaging.send_text(
                        recipient=recipient,
                        text=f"❌ {result['message']}"
                    )

                # Complete flow
                return self.messaging.send_text(
                    recipient=recipient,
                    text=self.get_step_content("complete")
                )

            else:
                raise FlowException(
                    message=f"Invalid step: {step}",
                    step=step,
                    action="validate",
                    data={"value": input_value}
                )

        except FlowException:
            # Let flow errors propagate up
            raise

        except Exception as e:
            # Wrap other errors
            raise SystemException(
                message=str(e),
                code="FLOW_ERROR",
                service="credex_flow",
                action=f"process_{step}"
            )


class AcceptFlow(CredexFlow):
    """Credex accept flow"""

    def get_step_content(self, step: str, data: Optional[Dict] = None) -> str:
        """Get accept step content"""
        if step == "select":
            return "Select a credex offer to accept:"
        elif step == "confirm":
            if data:
                return (
                    "📝 Review offer to accept:\n"
                    f"💸 Amount: {data.get('amount')}\n"
                    f"💳 From: {data.get('handle')}"
                )
            return "Please confirm acceptance (yes/no):"
        elif step == "complete":
            return "✅ Offer accepted successfully."
        return ""

    def process_step(self, state_manager: Any, step: str, input_value: Any) -> Message:
        """Process accept step"""
        try:
            recipient = self._get_recipient(state_manager)
            credex_service = get_credex_service(state_manager)

            if step == "select":
                # UI validation
                component = SelectInput([])  # TODO: Get options from service
                validation = component.validate(input_value)
                if not validation.valid:
                    return self.messaging.send_text(
                        recipient=recipient,
                        text=f"❌ {validation.error['message']}"
                    )

                # Get offer details
                success, result = credex_service["get_credex"](validation.value)
                if not success:
                    return self.messaging.send_text(
                        recipient=recipient,
                        text=f"❌ {result['message']}"
                    )

                # Update state
                state_manager.update_state({
                    "flow_data": {
                        "active_component": component.get_ui_state(),
                        "data": {
                            "offer_id": validation.value,
                            "offer_details": result
                        }
                    }
                })

                # Show confirmation
                return self.messaging.send_text(
                    recipient=recipient,
                    text=self.get_step_content("confirm", result)
                )

            elif step == "confirm":
                # UI validation
                component = ConfirmInput()
                validation = component.validate(input_value)
                if not validation.valid:
                    return self.messaging.send_text(
                        recipient=recipient,
                        text=f"❌ {validation.error['message']}"
                    )

                # Only proceed if confirmed
                if not validation.value:
                    return self.messaging.send_text(
                        recipient=recipient,
                        text="❌ Acceptance cancelled."
                    )

                # Submit through service
                flow_data = state_manager.get_flow_data()
                success, result = credex_service["accept_credex"](
                    flow_data.get("offer_id")
                )

                if not success:
                    return self.messaging.send_text(
                        recipient=recipient,
                        text=f"❌ {result['message']}"
                    )

                # Complete flow
                return self.messaging.send_text(
                    recipient=recipient,
                    text=self.get_step_content("complete")
                )

            else:
                raise FlowException(
                    message=f"Invalid step: {step}",
                    step=step,
                    action="validate",
                    data={"value": input_value}
                )

        except FlowException:
            # Let flow errors propagate up
            raise

        except Exception as e:
            # Wrap other errors
            raise SystemException(
                message=str(e),
                code="FLOW_ERROR",
                service="credex_flow",
                action=f"process_{step}"
            )
