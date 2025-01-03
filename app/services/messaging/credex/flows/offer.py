"""Credex offer flow implementation

This module implements the offer flow with:
- Pure UI validation in components
- Business logic in services
- Flow coordination with proper state management
"""

import logging
from typing import Any, Dict, Optional

from core.components.input import AmountInput, HandleInput, ConfirmInput
from core.messaging.types import Message
from core.utils.exceptions import FlowException
from core.utils.error_handler import ErrorHandler
from services.credex.service import get_credex_service

from .base import CredexFlow

logger = logging.getLogger(__name__)


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
        """Process offer step with proper state management"""
        try:
            # Get flow state for context
            flow_state = state_manager.get_flow_state()
            if not flow_state:
                raise FlowException(
                    message="No active flow",
                    step=step,
                    action="process",
                    data={"flow_type": "credex_offer"}
                )

            # Get common resources
            recipient = self._get_recipient(state_manager)
            credex_service = get_credex_service(state_manager)

            if step == "amount":
                # Validate amount with proper tracking
                component = self._get_component(AmountInput)
                value = self._validate_input(state_manager, step, input_value, component)

                # Update flow data
                self._update_flow_data(state_manager, {"amount": value})

                # Move to next step with progress
                return self.messaging.send_text(
                    recipient=recipient,
                    text=f"{self.get_step_content('handle')}\n\nStep {flow_state['step_index'] + 2} of {flow_state['total_steps']}"
                )

            elif step == "handle":
                # Validate handle with proper tracking
                component = self._get_component(HandleInput)
                value = self._validate_input(state_manager, step, input_value, component)

                # Business validation with error handling
                success, result = credex_service["validate_account_handle"](value)
                if not success:
                    error_response = ErrorHandler.handle_flow_error(
                        step=step,
                        action="validate_handle",
                        data={"handle": value},
                        message=result["message"],
                        flow_state=flow_state
                    )
                    return self.messaging.send_text(
                        recipient=recipient,
                        text=f"❌ {error_response['error']['message']}"
                    )

                # Update flow data
                self._update_flow_data(state_manager, {"handle": value})

                # Show confirmation with progress
                flow_data = state_manager.get_flow_data()
                return self.messaging.send_text(
                    recipient=recipient,
                    text=f"{self.get_step_content('confirm', flow_data)}\n\nStep {flow_state['step_index'] + 2} of {flow_state['total_steps']}"
                )

            elif step == "confirm":
                # Validate confirmation with proper tracking
                component = self._get_component(ConfirmInput)
                value = self._validate_input(state_manager, step, input_value, component)

                # Handle cancellation
                if not value:
                    error_response = ErrorHandler.handle_flow_error(
                        step=step,
                        action="cancel",
                        data={},
                        message="Offer cancelled by user",
                        flow_state=flow_state
                    )
                    return self.messaging.send_text(
                        recipient=recipient,
                        text=f"❌ {error_response['error']['message']}"
                    )

                # Submit through service with error handling
                flow_data = state_manager.get_flow_data()
                success, result = credex_service["offer_credex"]({
                    "amount": flow_data.get("amount"),
                    "handle": flow_data.get("handle")
                })

                if not success:
                    error_response = ErrorHandler.handle_flow_error(
                        step=step,
                        action="submit",
                        data=flow_data,
                        message=result["message"],
                        flow_state=flow_state
                    )
                    return self.messaging.send_text(
                        recipient=recipient,
                        text=f"❌ {error_response['error']['message']}"
                    )

                # Complete flow with final step (no progress needed for completion)
                return self.messaging.send_text(
                    recipient=recipient,
                    text=self.get_step_content('complete')
                )

            else:
                raise FlowException(
                    message=f"Invalid step: {step}",
                    step=step,
                    action="validate",
                    data={"value": input_value}
                )

        except FlowException:
            # Let flow errors propagate up for handler to process
            raise

        except Exception as e:
            # Enhanced error handling
            error_response = ErrorHandler.handle_system_error(
                code="FLOW_ERROR",
                service="credex_flow",
                action=f"process_{step}",
                message="Unexpected error in offer flow",
                error=e
            )
            raise FlowException(
                message=error_response["error"]["message"],
                step=step,
                action="process",
                data=error_response["error"]["details"]
            )
