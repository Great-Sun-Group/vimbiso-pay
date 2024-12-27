"""Step definitions for credex flows"""
from typing import Any, Dict, List

from core.messaging.flow import Step, StepType
from core.utils.state_validator import StateValidator
from services.whatsapp.types import WhatsAppMessage

from .transformers import transform_amount, transform_handle
from .validators import validate_amount, validate_handle


def _create_message(state: Dict[str, Any], message: str) -> Dict[str, Any]:
    """Create message with state validation at boundary"""
    # Validate at boundary before any state access
    validation_result = StateValidator.validate_state(state)
    if not validation_result.is_valid:
        raise ValueError(f"Invalid state: {validation_result.error_message}")

    # Get channel info from top level state only
    channel = state.get("channel")
    if not channel or not channel.get("identifier"):
        raise ValueError("Channel identifier not found")

    return WhatsAppMessage.create_text(
        channel["identifier"],
        message
    )


def create_initial_message(state: Dict[str, Any]) -> Dict[str, Any]:
    """Create initial message with state validation"""
    return _create_message(
        state,
        "Enter amount:\n\n"
        "Examples:\n"
        "100     (USD)\n"
        "USD 100\n"
        "ZWG 100\n"
        "XAU 1"
    )


def create_handle_message(state: Dict[str, Any]) -> Dict[str, Any]:
    """Create handle message with state validation"""
    return _create_message(state, "Enter recipient handle:")


def create_confirm_message(state: Dict[str, Any]) -> Dict[str, Any]:
    """Create confirmation message with state validation"""
    return _create_message(state, "Please confirm (yes/no):")


def create_flow_steps() -> List[Step]:
    """Create steps for credex flow"""
    return [
        Step(
            id="amount",
            type=StepType.TEXT,
            message=create_initial_message,
            validator=validate_amount,
            transformer=transform_amount
        ),
        Step(
            id="handle",
            type=StepType.TEXT,
            message=create_handle_message,
            validator=validate_handle,
            transformer=transform_handle
        ),
        Step(
            id="confirm",
            type=StepType.TEXT,
            message=create_confirm_message,
            validator=lambda x: x.lower() in ["yes", "no"],
            transformer=lambda x: {"confirmed": x.lower() == "yes"}
        )
    ]
