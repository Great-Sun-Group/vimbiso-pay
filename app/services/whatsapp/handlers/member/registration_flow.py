"""Registration flow for member signup"""
import logging
from typing import Any, Dict, Tuple

from core.messaging.flow import Flow, Step, StepType
from services.state.service import StateStage
from ...types import WhatsAppMessage

logger = logging.getLogger(__name__)


class RegistrationFlow(Flow):
    """Progressive flow for member registration"""

    FLOW_ID = "registration"  # Flow identifier

    def __init__(self, flow_id: str, steps: list[Step]):
        """Initialize flow with ID"""
        super().__init__(flow_id, steps)
        self.steps = self._create_steps()

    def _create_steps(self) -> list[Step]:
        return [
            # Step 1: First Name Input
            Step(
                id="first_name",
                type=StepType.TEXT_INPUT,
                stage=StateStage.REGISTRATION.value,
                message=lambda state: self._create_text_prompt(
                    "What's your first name?",
                    state.get("phone", "")
                ),
                validation=lambda value: self._validate_name(value, "First name")[0],
                transform=lambda value: {"first_name": value.strip()}
            ),
            # Step 2: Last Name Input
            Step(
                id="last_name",
                type=StepType.TEXT_INPUT,
                stage=StateStage.REGISTRATION.value,
                message=lambda state: self._create_text_prompt(
                    "And what's your last name?",
                    state.get("phone", "")
                ),
                validation=lambda value: self._validate_name(value, "Last name")[0],
                transform=lambda value: {"last_name": value.strip()},
                condition=lambda state: bool(state.get("first_name"))
            ),
            # Step 3: Confirmation
            Step(
                id="confirm",
                type=StepType.BUTTON_SELECT,
                stage=StateStage.REGISTRATION.value,
                message=self._create_confirmation_message,
                condition=lambda state: self._has_valid_registration(state),
                transform=lambda value: {"confirmed": value == "confirm_registration"},
                validation=lambda value: value == "confirm_registration"
            )
        ]

    def _create_text_prompt(self, prompt: str, phone: str) -> WhatsAppMessage:
        """Create a text input prompt message"""
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone,
            "type": "text",
            "text": {
                "body": prompt
            }
        }

    def _validate_name(self, value: str, field: str) -> Tuple[bool, str]:
        """Validate name input against API requirements"""
        try:
            value = value.strip()
            if not value:
                return False, f"{field} cannot be empty"

            if len(value) < 3:
                return False, f"{field} must be at least 3 letters"

            if len(value) > 50:
                return False, f"{field} cannot exceed 50 letters"

            if not value.replace(" ", "").isalpha():
                return False, f"{field} can only contain letters"

            return True, ""

        except Exception as e:
            logger.error(f"Error validating {field.lower()}: {str(e)}")
            return False, f"Invalid {field.lower()}"

    def _has_valid_registration(self, state: Dict[str, Any]) -> bool:
        """Check if registration data is valid"""
        first_name = state.get("first_name", {}).get("first_name", "")
        last_name = state.get("last_name", {}).get("last_name", "")

        # Revalidate both names to ensure they meet API requirements
        first_valid, _ = self._validate_name(first_name, "First name")
        last_valid, _ = self._validate_name(last_name, "Last name")

        return first_valid and last_valid

    def _create_confirmation_message(self, state: Dict[str, Any]) -> WhatsAppMessage:
        """Create confirmation message after successful registration"""
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": state.get("phone", ""),
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": (
                        f"✅ Please confirm your registration details:\n\n"
                        f"First Name: {state.get('first_name', {}).get('first_name', '')}\n"
                        f"Last Name: {state.get('last_name', {}).get('last_name', '')}\n"
                        f"Default Currency: USD\n\n"
                        "Is this information correct?"
                    )
                },
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": "confirm_registration",
                                "title": "Confirm"
                            }
                        }
                    ]
                }
            }
        }
