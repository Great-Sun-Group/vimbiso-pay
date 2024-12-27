"""Step definitions for credex flows"""
from typing import List

from core.messaging.flow import Step, StepType
from .messages import create_confirmation_prompt, create_handle_prompt, create_initial_prompt
from .validators import validate_amount, validate_handle
from .transformers import transform_amount, transform_handle


def create_flow_steps() -> List[Step]:
    """Create steps for credex flow"""
    return [
        Step(
            id="amount",
            type=StepType.TEXT,
            message=create_initial_prompt,
            validator=validate_amount,
            transformer=transform_amount
        ),
        Step(
            id="handle",
            type=StepType.TEXT,
            message=create_handle_prompt,
            validator=validate_handle,
            transformer=transform_handle
        ),
        Step(
            id="confirm",
            type=StepType.TEXT,
            message=create_confirmation_prompt,
            validator=lambda x: x.lower() in ["yes", "no"],
            transformer=lambda x: {"confirmed": x.lower() == "yes"}
        )
    ]
