"""Credex flows using clean architecture patterns

This module implements credex flows with:
- Pure UI validation in components
- Business logic in services
- Flow coordination with proper state management
- Clear validation boundaries
"""

import logging
from typing import Any, Dict, Optional

from core.components.base import Component
from core.components.input import (AmountInput, ConfirmInput, HandleInput,
                                   SelectInput)
from core.messaging.interface import MessagingServiceInterface
from core.messaging.registry import FlowRegistry
from core.messaging.types import Message
from core.utils.error_handler import ErrorHandler
from core.utils.exceptions import FlowException, SystemException
from services.credex.service import get_credex_service

from ..utils import get_recipient

logger = logging.getLogger(__name__)


def validate_input(
    state_manager: Any,
    step: str,
    input_value: Any,
    component: Component
) -> Dict:
    """Validate input with proper state tracking

    Args:
        state_manager: State manager instance
        step: Current step
        input_value: Input to validate
        component: Component to use for validation

    Returns:
        Dict with validation result

    Raises:
        FlowException: If validation fails
    """
    try:
        # UI validation
        validation = component.validate(input_value)
        if not validation.valid:
            error_response = ErrorHandler.handle_component_error(
                component=component.type,
                field=validation.error.get("field", "value"),
                value=input_value,
                message=validation.error.get("message", "Invalid input"),
                validation_state=component.validation_state
            )
            raise FlowException(
                message=error_response["error"]["message"],
                step=step,
                action="validate",
                data=error_response["error"]["details"]
            )

        # Update component state
        state_manager.update_state({
            "flow_data": {
                "active_component": component.get_ui_state()
            }
        })

        return validation.value

    except FlowException:
        raise

    except Exception as e:
        error_response = ErrorHandler.handle_system_error(
            code="VALIDATION_ERROR",
            service="credex_flow",
            action=f"validate_{step}",
            message=str(e),
            error=e
        )
        raise FlowException(
            message=error_response["error"]["message"],
            step=step,
            action="validate",
            data=error_response["error"]["details"]
        )


class OfferFlow:
    """Credex offer flow using clean architecture"""

    @staticmethod
    def get_step_content(step: str, data: Optional[Dict] = None) -> str:
        """Get offer step content"""
        # Validate step through registry
        FlowRegistry.validate_flow_step("credex_offer", step)

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

    @staticmethod
    def process_step(messaging_service: MessagingServiceInterface, state_manager: Any, step: str, input_value: Any) -> Message:
        """Process offer step using clean architecture patterns"""
        try:
            # Validate step through registry
            FlowRegistry.validate_flow_step("credex_offer", step)
            recipient = get_recipient(state_manager)
            credex_service = get_credex_service(state_manager)

            if step == "amount":
                # UI validation
                validation = validate_input(state_manager, step, input_value, AmountInput())

                # Update flow state
                state_manager.update_state({
                    "flow_data": {
                        "data": {"amount": validation}
                    }
                })

                # Move to next step
                return messaging_service.send_text(
                    recipient=recipient,
                    text=OfferFlow.get_step_content("handle")
                )

            elif step == "handle":
                # UI validation
                validation = validate_input(state_manager, step, input_value, HandleInput())

                # Business validation
                success, result = credex_service["validate_account_handle"](validation)
                if not success:
                    return messaging_service.send_text(
                        recipient=recipient,
                        text=f"❌ {result['message']}"
                    )

                # Update flow state
                state_manager.update_state({
                    "flow_data": {
                        "data": {
                            **state_manager.get_flow_data(),
                            "handle": validation
                        }
                    }
                })

                # Show confirmation
                flow_data = state_manager.get_flow_data()
                return messaging_service.send_text(
                    recipient=recipient,
                    text=OfferFlow.get_step_content("confirm", {
                        "amount": flow_data.get("amount"),
                        "handle": validation
                    })
                )

            elif step == "confirm":
                # UI validation
                validation = validate_input(state_manager, step, input_value, ConfirmInput())

                # Only proceed if confirmed
                if not validation:
                    return messaging_service.send_text(
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
                    return messaging_service.send_text(
                        recipient=recipient,
                        text=f"❌ {result['message']}"
                    )

                # Complete flow
                return messaging_service.send_text(
                    recipient=recipient,
                    text=OfferFlow.get_step_content("complete")
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


class ActionFlow:
    """Base class for credex action flows (accept/decline/cancel)"""

    @staticmethod
    def get_step_content(flow_type: str, step: str, data: Optional[Dict] = None) -> str:
        """Get action step content"""
        # Validate step through registry
        FlowRegistry.validate_flow_step(flow_type, step)

        if step == "select":
            action = flow_type.split("_")[1]  # e.g. "credex_accept" -> "accept"
            return f"Select a credex offer to {action}:"
        elif step == "confirm":
            if data:
                return (
                    "📝 Review offer:\n"
                    f"💸 Amount: {data.get('amount')}\n"
                    f"💳 From: {data.get('handle')}"
                )
            return "Please confirm (yes/no):"
        elif step == "complete":
            action = flow_type.split("_")[1]
            return f"✅ Offer {action}ed successfully."
        return ""

    @staticmethod
    def process_step(messaging_service: MessagingServiceInterface, state_manager: Any, step: str, input_value: Any, flow_type: str) -> Message:
        """Process action step"""
        try:
            # Validate step through registry
            FlowRegistry.validate_flow_step(flow_type, step)
            recipient = get_recipient(state_manager)
            credex_service = get_credex_service(state_manager)
            action = flow_type.split("_")[1]  # e.g. "credex_accept" -> "accept"

            if step == "select":
                # UI validation
                validation = validate_input(state_manager, step, input_value, SelectInput([]))  # TODO: Get options from service

                # Get offer details
                success, result = credex_service["get_credex"](validation)
                if not success:
                    return messaging_service.send_text(
                        recipient=recipient,
                        text=f"❌ {result['message']}"
                    )

                # Update state
                state_manager.update_state({
                    "flow_data": {
                        "data": {
                            "offer_id": validation,
                            "offer_details": result
                        }
                    }
                })

                # Show confirmation
                return messaging_service.send_text(
                    recipient=recipient,
                    text=ActionFlow.get_step_content(flow_type, "confirm", result)
                )

            elif step == "confirm":
                # UI validation
                validation = validate_input(state_manager, step, input_value, ConfirmInput())

                # Only proceed if confirmed
                if not validation:
                    return messaging_service.send_text(
                        recipient=recipient,
                        text=f"❌ {action.title()} cancelled."
                    )

                # Submit through service
                flow_data = state_manager.get_flow_data()
                success, result = credex_service[f"{action}_credex"](
                    flow_data.get("offer_id")
                )

                if not success:
                    return messaging_service.send_text(
                        recipient=recipient,
                        text=f"❌ {result['message']}"
                    )

                # Complete flow
                return messaging_service.send_text(
                    recipient=recipient,
                    text=ActionFlow.get_step_content(flow_type, "complete")
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
