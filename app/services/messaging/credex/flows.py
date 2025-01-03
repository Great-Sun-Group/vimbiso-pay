"""Credex flows using messaging service interface"""
import logging
from typing import Any, Dict, Optional

from core.messaging.interface import MessagingServiceInterface
from core.messaging.types import Message, MessageRecipient
from core.utils.exceptions import FlowException, SystemException

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
    """Credex offer flow"""

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
        """Process offer step"""
        try:
            recipient = self._get_recipient(state_manager)

            if step == "amount":
                # TODO: Validate amount and denomination
                state_manager.update_state({
                    "flow_data": {
                        "data": {"amount": input_value}
                    }
                })
                return self.messaging.send_text(
                    recipient=recipient,
                    text=self.get_step_content("handle")
                )

            elif step == "handle":
                # TODO: Validate handle
                state_manager.update_state({
                    "flow_data": {
                        "data": {
                            **state_manager.get_flow_data(),
                            "handle": input_value
                        }
                    }
                })
                return self.messaging.send_text(
                    recipient=recipient,
                    text=self.get_step_content("confirm", {
                        "amount": state_manager.get_flow_data().get("amount"),
                        "handle": input_value
                    })
                )

            elif step == "confirm":
                # TODO: Submit offer through API
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

            if step == "select":
                # TODO: Validate selection
                state_manager.update_state({
                    "flow_data": {
                        "data": {"offer_id": input_value}
                    }
                })
                # TODO: Get offer details from API
                return self.messaging.send_text(
                    recipient=recipient,
                    text=self.get_step_content("confirm")
                )

            elif step == "confirm":
                # TODO: Submit acceptance through API
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
