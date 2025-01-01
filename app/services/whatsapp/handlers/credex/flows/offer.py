"""Offer flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ErrorContext
from core.utils.exceptions import StateException
from services.credex.service import get_credex_service

from .messages import (create_handle_prompt, create_initial_prompt,
                       create_offer_confirmation, create_success_message)

logger = logging.getLogger(__name__)

# Valid denominations
VALID_DENOMINATIONS = {"USD", "ZWG", "XAU", "CAD"}


def validate_offer_input(input_type: str, value: str) -> Dict[str, Any]:
    """Validate offer input based on type"""
    if input_type == "amount":
        parts = value.split()
        if not value or len(parts) > 2:
            raise StateException("Enter amount with optional denomination (e.g. 100 USD)")

        # Parse amount and denomination
        if len(parts) == 1:
            amount, denom = parts[0], "USD"
        else:
            first, second = parts
            if first.upper() in VALID_DENOMINATIONS:
                denom, amount = first.upper(), second
            else:
                amount, denom = first, second.upper()

        # Validate amount
        try:
            amount = float(amount)
            if amount <= 0:
                raise StateException("Amount must be greater than 0")
        except ValueError:
            raise StateException("Invalid amount value")

        # Validate denomination
        if denom not in VALID_DENOMINATIONS:
            raise StateException(f"Invalid denomination. Supported: {', '.join(sorted(VALID_DENOMINATIONS))}")

        return {"amount": amount, "denomination": denom}

    elif input_type == "handle":
        handle = value.strip()
        if not handle or len(handle) < 3:
            raise StateException("Handle must be at least 3 characters")
        return {"handle": handle}

    elif input_type == "confirm":
        if value.lower() not in ["yes", "no"]:
            raise StateException("Please reply with 'yes' or 'no'")
        return {"confirmed": value.lower() == "yes"}

    raise StateException(f"Invalid input type: {input_type}")


def update_offer_state(state_manager: Any, step: str, data: Dict[str, Any]) -> None:
    """Update offer state with validation"""
    state_manager.update_state({
        "flow_data": {
            "step": {"amount": 1, "handle": 2, "confirm": 3}[step],
            "current_step": step,
            "data": data
        }
    })


def process_offer_step(state_manager: Any, step: str, input_data: Any = None) -> Dict[str, Any]:
    """Process offer step with validation"""
    try:
        # Get channel ID through state manager
        state = state_manager.get("channel")
        channel_id = state["identifier"]

        # Initial prompt
        if not input_data:
            return create_initial_prompt(channel_id)

        # Validate input and update state
        try:
            validated = validate_offer_input(step, input_data)
            update_offer_state(state_manager, step, validated)
        except StateException as e:
            error_context = ErrorContext(
                error_type="input",
                message=str(e),
                step_id=step,
                details={"input": input_data}
            )
            raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))

        # Handle step progression
        if step == "amount":
            return create_handle_prompt(channel_id)

        elif step == "handle":
            state = state_manager.get_flow_step_data()
            amount = state["amount"]
            handle = validated["handle"]
            return create_offer_confirmation(
                channel_id,
                amount["amount"],
                amount["denomination"],
                handle
            )

        elif step == "confirm" and validated["confirmed"]:
            # Submit offer
            credex_service = get_credex_service(state_manager)
            success, response = credex_service["offer_credex"](
                state_manager.get_flow_step_data()
            )
            if not success:
                raise StateException(response.get("message", "Failed to create offer"))

            # Log success
            logger.info(
                "Offer created successfully",
                extra={
                    "channel_id": channel_id,
                    "response": response
                }
            )
            return create_success_message(channel_id)

        # Re-confirm if not confirmed
        state = state_manager.get_flow_step_data()
        amount = state["amount"]
        handle = state["handle"]
        return create_offer_confirmation(
            channel_id,
            amount["amount"],
            amount["denomination"],
            handle
        )

    except Exception as e:
        error_context = ErrorContext(
            error_type="flow",
            message=str(e),
            step_id=step,
            details={
                "input": input_data,
                "operation": "process_step"
            }
        )
        raise StateException(ErrorHandler.handle_error(e, state_manager, error_context))
