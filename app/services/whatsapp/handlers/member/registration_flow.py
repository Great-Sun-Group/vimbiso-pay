"""Registration flow for member signup"""
import logging
from typing import Any, Dict, Tuple, Optional

from core.messaging.flow import Flow, Step, StepType
from services.state.service import StateStage
from ...types import WhatsAppMessage

logger = logging.getLogger(__name__)


class RegistrationFlow(Flow):
    """Progressive flow for member registration"""

    FLOW_ID = "registration"  # Flow identifier

    def __init__(self, flow_id: str, steps: list[Step]):
        """Initialize flow with ID"""
        super().__init__(flow_id, self._create_steps())
        self.state_service = None  # Will be injected

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
                logger.debug(f"{field} validation failed: empty value")
                return False, f"{field} cannot be empty"

            if len(value) < 3:
                logger.debug(f"{field} validation failed: too short ({len(value)} chars)")
                return False, f"{field} must be at least 3 letters"

            if len(value) > 50:
                logger.debug(f"{field} validation failed: too long ({len(value)} chars)")
                return False, f"{field} cannot exceed 50 letters"

            if not value.replace(" ", "").isalpha():
                logger.debug(f"{field} validation failed: contains non-letters")
                return False, f"{field} can only contain letters"

            logger.debug(f"{field} validation successful")
            return True, ""

        except Exception as e:
            logger.error(f"Error validating {field.lower()}: {str(e)}")
            return False, f"Invalid {field.lower()}"

    def _has_valid_registration(self, state: Dict[str, Any]) -> bool:
        """Check if registration data is valid"""
        try:
            logger.debug("Validating registration data")
            logger.debug(f"Current state: {state}")

            first_name = state.get("first_name", {}).get("first_name", "")
            last_name = state.get("last_name", {}).get("last_name", "")

            # Revalidate both names to ensure they meet API requirements
            first_valid, first_msg = self._validate_name(first_name, "First name")
            last_valid, last_msg = self._validate_name(last_name, "Last name")

            if not first_valid:
                logger.debug(f"First name validation failed: {first_msg}")
                return False
            if not last_valid:
                logger.debug(f"Last name validation failed: {last_msg}")
                return False

            logger.debug("Registration data validation successful")
            return True

        except Exception as e:
            logger.error(f"Error validating registration: {str(e)}")
            return False

    def _create_confirmation_message(self, state: Dict[str, Any]) -> WhatsAppMessage:
        """Create confirmation message after successful registration"""
        try:
            first_name = state.get("first_name", {}).get("first_name", "")
            last_name = state.get("last_name", {}).get("last_name", "")

            logger.debug(f"Creating confirmation message for {first_name} {last_name}")

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
                            f"First Name: {first_name}\n"
                            f"Last Name: {last_name}\n"
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
        except Exception as e:
            logger.error(f"Error creating confirmation message: {str(e)}")
            raise

    def validate_state(self) -> bool:
        """Validate current flow state"""
        try:
            # Check basic Flow validation first
            if not super().validate_state():
                logger.debug("Base flow validation failed")
                return False

            # Validate step index
            if not 0 <= self.current_step_index < len(self.steps):
                logger.debug(f"Invalid step index: {self.current_step_index}")
                return False

            # Get current step
            current = self.current_step
            if not current:
                logger.debug("No current step")
                return False

            # Check if current step should execute
            if not current.should_execute(self.state):
                logger.debug(f"Step {current.id} should not execute")
                return False

            # Validate state data based on current step
            if current.id == "last_name":
                if not self.state.get("first_name"):
                    logger.debug("Missing first_name data for last_name step")
                    return False
            elif current.id == "confirm":
                if not self._has_valid_registration(self.state):
                    logger.debug("Invalid registration data for confirm step")
                    return False

            logger.debug("Flow state validation successful")
            return True

        except Exception as e:
            logger.error(f"Flow state validation error: {str(e)}")
            return False

    def recover_state(self) -> bool:
        """Attempt to recover corrupted state"""
        try:
            logger.debug("Attempting state recovery")

            # Try base recovery first
            if super().recover_state():
                logger.debug("Base recovery successful")
                return True

            # Custom recovery logic
            if self.state.get("first_name") and self.state.get("last_name"):
                # If we have both names, move to confirmation
                self.current_step_index = 2
            elif self.state.get("first_name"):
                # If we have first name, move to last name
                self.current_step_index = 1
            else:
                # Start over
                self.current_step_index = 0

            # Validate recovered state
            if self.validate_state():
                logger.debug(f"State recovered to step {self.current_step_index}")
                return True

            logger.debug("State recovery failed")
            return False

        except Exception as e:
            logger.error(f"State recovery error: {str(e)}")
            return False

    def complete_flow(self) -> Tuple[bool, str]:
        """Complete the registration flow"""
        try:
            logger.debug("Completing registration flow")

            # Validate final state
            if not self._has_valid_registration(self.state):
                logger.error("Invalid registration data")
                return False, "Invalid registration data"

            # Get registration data
            first_name = self.state.get("first_name", {}).get("first_name", "")
            last_name = self.state.get("last_name", {}).get("last_name", "")

            # Update state service if available
            if self.state_service and self.state.get("phone"):
                current_state = self.state_service.get_state(self.state.get("phone"))
                current_state.update({
                    "registration": {
                        "first_name": first_name,
                        "last_name": last_name,
                        "completed": True,
                        "version": self._version
                    }
                })
                self.state_service.update_state(
                    user_id=self.state.get("phone"),
                    new_state=current_state,
                    stage=StateStage.MENU.value,
                    update_from="registration_complete",
                    option="handle_action_menu"
                )
                logger.debug("Registration state updated")

            logger.debug("Registration flow completed successfully")
            return True, "Registration completed successfully"

        except Exception as e:
            logger.error(f"Flow completion error: {str(e)}")
            return False, str(e)

    @classmethod
    def get_flow_by_id(cls, flow_id: str) -> Optional[Flow]:
        """Get flow instance by ID"""
        if flow_id == cls.FLOW_ID:
            return cls(flow_id, [])
        return None
