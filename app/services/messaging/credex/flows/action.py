"""Credex action flow implementation

This module implements the action flow (accept/decline/cancel) with:
- Pure UI validation in components
- Business logic in services
- Flow coordination with proper state management
"""

import logging
from typing import Any, Dict, Optional

from core.components.input import SelectInput, ConfirmInput
from core.messaging.interface import MessagingServiceInterface
from core.messaging.types import Message
from core.utils.exceptions import FlowException
from core.utils.error_handler import ErrorHandler
from services.credex.service import get_credex_service

from .base import CredexFlow

logger = logging.getLogger(__name__)


class ActionFlow(CredexFlow):
    """Credex action flow (accept/decline/cancel) using clean architecture"""

    # Action type configuration
    ACTIONS = {
        "accept": {
            "service_method": "accept_credex",
            "confirm_prompt": "accept",
            "cancel_message": "Acceptance cancelled",
            "complete_message": "✅ Offer accepted successfully.",
            "error_prefix": "accept"
        },
        "decline": {
            "service_method": "decline_credex",
            "confirm_prompt": "decline",
            "cancel_message": "Decline cancelled",
            "complete_message": "✅ Offer declined successfully.",
            "error_prefix": "decline"
        },
        "cancel": {
            "service_method": "cancel_credex",
            "confirm_prompt": "cancel",
            "cancel_message": "Cancellation cancelled",
            "complete_message": "✅ Offer cancelled successfully.",
            "error_prefix": "cancel"
        }
    }

    def __init__(self, messaging_service: MessagingServiceInterface, action_type: str):
        """Initialize with action type"""
        super().__init__(messaging_service)
        if action_type not in self.ACTIONS:
            raise ValueError(f"Invalid action type: {action_type}")
        self.action_type = action_type
        self.config = self.ACTIONS[action_type]

    def get_step_content(self, step: str, data: Optional[Dict] = None) -> str:
        """Get action step content"""
        if step == "select":
            return f"Select a credex offer to {self.action_type}:"
        elif step == "confirm":
            if data:
                return (
                    f"📝 Review offer to {self.config['confirm_prompt']}:\n"
                    f"💸 Amount: {data.get('amount')}\n"
                    f"💳 From: {data.get('handle')}"
                )
            return f"Please confirm {self.config['confirm_prompt']} (yes/no):"
        elif step == "complete":
            return self.config["complete_message"]
        return ""

    def process_step(self, state_manager: Any, step: str, input_value: Any) -> Message:
        """Process action step with proper state management"""
        try:
            # Get flow state for context
            flow_state = state_manager.get_flow_state()
            if not flow_state:
                raise FlowException(
                    message="No active flow",
                    step=step,
                    action="process",
                    data={"flow_type": f"credex_{self.action_type}"}
                )

            # Get common resources
            recipient = self._get_recipient(state_manager)
            credex_service = get_credex_service(state_manager)

            if step == "select":
                # Get pending offers for validation
                flow_data = state_manager.get_flow_data()
                pending_offers = flow_data.get("pending_offers", [])
                valid_ids = [offer.get("id") for offer in pending_offers]

                # Validate selection with proper tracking
                component = self._get_component(SelectInput, options=valid_ids)
                value = self._validate_input(state_manager, step, input_value, component)

                # Get offer details with error handling
                success, result = credex_service["get_credex"](value)
                if not success:
                    error_response = ErrorHandler.handle_flow_error(
                        step=step,
                        action="get_offer",
                        data={"offer_id": value},
                        message=result["message"],
                        flow_state=flow_state
                    )
                    return self.messaging.send_text(
                        recipient=recipient,
                        text=f"❌ {error_response['error']['message']}"
                    )

                # Update flow data
                self._update_flow_data(state_manager, {
                    "offer_id": value,
                    "offer_details": result
                })

                # Show confirmation with progress
                return self.messaging.send_text(
                    recipient=recipient,
                    text=f"{self.get_step_content('confirm', result)}\n\nStep {flow_state['step_index'] + 2} of {flow_state['total_steps']}"
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
                        message=self.config["cancel_message"],
                        flow_state=flow_state
                    )
                    return self.messaging.send_text(
                        recipient=recipient,
                        text=f"❌ {error_response['error']['message']}"
                    )

                # Submit through service with error handling
                flow_data = state_manager.get_flow_data()
                success, result = credex_service[self.config["service_method"]](
                    flow_data.get("offer_id")
                )

                if not success:
                    error_response = ErrorHandler.handle_flow_error(
                        step=step,
                        action="submit",
                        data={"offer_id": flow_data.get("offer_id")},
                        message=result["message"],
                        flow_state=flow_state
                    )
                    return self.messaging.send_text(
                        recipient=recipient,
                        text=f"❌ {error_response['error']['message']}"
                    )

                # Complete flow (no progress needed for completion)
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
                message=f"Unexpected error in {self.action_type} flow",
                error=e
            )
            raise FlowException(
                message=error_response["error"]["message"],
                step=step,
                action="process",
                data=error_response["error"]["details"]
            )
