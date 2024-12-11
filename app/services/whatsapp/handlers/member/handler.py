"""Handler for member registration"""
import logging
import time
from typing import Any, Dict, Tuple

from core.messaging.flow_handler import FlowHandler
from services.state.service import StateStage
from ...base_handler import BaseActionHandler
from ...types import WhatsAppMessage
from .registration_flow import RegistrationFlow

logger = logging.getLogger(__name__)


class MemberRegistrationHandler(BaseActionHandler):
    """Handler for member registration and initial account setup"""

    FLOW_ID = "registration"  # Consistent flow ID

    def __init__(self, service):
        logger.debug("Initializing MemberRegistrationHandler")
        super().__init__(service)

        # Initialize flow handler
        self.flow_handler = FlowHandler(self.service.state)
        self.flow_handler.register_flow(
            RegistrationFlow,
            service_injector=self._inject_flow_services
        )
        logger.debug("Registration flow initialized")

    def _inject_flow_services(self, flow: RegistrationFlow) -> None:
        """Inject required services into flow"""
        # No services needed for basic registration
        pass

    def _validate_name(self, name: str) -> bool:
        """Validate name against API requirements"""
        if not name or not isinstance(name, str):
            return False
        name = name.strip()
        return 3 <= len(name) <= 50 and name.replace(" ", "").isalpha()

    def _update_registration_state(
        self,
        current_state: Dict[str, Any],
        stage: str,
        update_from: str,
        preserve_flow: bool = True
    ) -> None:
        """Update state with consistent pattern"""
        try:
            # Create new state with only essential data
            new_state = {}

            # Preserve critical state data
            critical_fields = [
                "first_name",
                "last_name",
                "phone"
            ]
            for field in critical_fields:
                if field in current_state:
                    new_state[field] = current_state[field]

            # Preserve flow data if needed
            if preserve_flow and "flow_data" in current_state:
                new_state["flow_data"] = current_state["flow_data"]
                # Ensure flow data has required fields
                if "data" in new_state["flow_data"]:
                    for field in critical_fields:
                        if field in current_state:
                            new_state["flow_data"]["data"][field] = current_state[field]

            # Update state with proper context
            self.service.state.update_state(
                user_id=self.service.user.mobile_number,
                new_state=new_state,
                stage=stage,
                update_from=update_from
            )
            logger.debug(f"Registration state updated from {update_from}")
            logger.debug(f"Updated state: {new_state}")
        except Exception as e:
            logger.error(f"Error updating registration state: {str(e)}")

    def _onboard_member(self, flow_state: Dict[str, Any]) -> Tuple[bool, str]:
        """Onboard member and create initial personal account"""
        try:
            # Extract registration data
            first_name = flow_state.get("first_name", {}).get("first_name", "")
            last_name = flow_state.get("last_name", {}).get("last_name", "")
            phone = flow_state.get("phone", "")

            # Validate required fields
            if not all([first_name, last_name, phone]):
                logger.error("Missing required registration data")
                return False, "Missing required registration data"

            # Validate name lengths
            if not self._validate_name(first_name):
                return False, "First name must be 3-50 letters"
            if not self._validate_name(last_name):
                return False, "Last name must be 3-50 letters"

            # Show processing message
            self._format_message_response(
                "Processing your registration... Please wait."
            )

            # Call register_member endpoint which creates both member and initial account
            success, msg = self.service.credex_service._auth.register_member({
                "phone": phone,
                "firstname": first_name.strip(),    # API expects lowercase
                "lastname": last_name.strip(),      # API expects lowercase
                "defaultDenom": "USD"              # Default to USD
            })

            if not success:
                logger.error(f"Member registration failed: {msg}")
                return False, msg

            # Add small delay to ensure registration completes
            time.sleep(2)

            logger.info(f"Successfully registered member {phone}")

            # Return success but let handler show dashboard
            return True, f"Welcome {first_name} your account has been created successfully! 🎉"

        except Exception as e:
            logger.exception(f"Error during member registration: {str(e)}")
            return False, f"Registration failed: {str(e)}"

    def handle_registration(self) -> WhatsAppMessage:
        """Handle member registration with proper state management"""
        try:
            logger.debug("Starting handle_registration")
            current_state = self.service.current_state

            # Log message details
            logger.debug(f"Message type: {self.service.message_type}")
            logger.debug(f"Message body: {self.service.body}")
            if self.service.message_type == "interactive":
                interactive = self.service.message.get("interactive", {})
                logger.debug(f"Interactive type: {interactive.get('type')}")
                logger.debug(f"Interactive content: {interactive}")

            # Check if there's an active flow
            if "flow_data" in current_state:
                logger.debug("Found active flow, handling message")

                # Handle message with flow handler
                message = self.flow_handler.handle_message(
                    self.service.user.mobile_number,
                    self.service.message
                )

                # Get fresh state after flow handler update
                current_state = self.service.state.get_state(self.service.user.mobile_number)
                flow_state = current_state.get("flow_data", {}).get("data", {})
                logger.debug(f"Current flow state: {flow_state}")

                # Check if flow is complete (message is None)
                if message is None:
                    # Check confirmation in the updated flow state
                    confirmed = flow_state.get("confirm", {}).get("confirmed")
                    logger.debug(f"Confirmation state: {confirmed}")

                    if confirmed is True:
                        # Attempt to register member
                        success, msg = self._onboard_member(flow_state)

                        if success:
                            # Clear flow and move to menu
                            self._update_registration_state(
                                current_state=current_state,
                                stage=StateStage.MENU.value,
                                update_from="registration_complete",
                                preserve_flow=False
                            )
                            # Show dashboard with welcome message
                            from ...auth_handlers import AuthActionHandler
                            auth_handler = AuthActionHandler(self.service)
                            return auth_handler.handle_action_menu(message=msg, login=True)
                        else:
                            # Stay in registration state but show error
                            return self._format_error_response(msg)
                    else:
                        # Flow completed but no confirmation state
                        logger.error(f"Invalid confirmation state: {confirmed}")
                        return self._format_error_response(
                            "Something went wrong with your registration. Please try again."
                        )
                else:
                    # Flow still in progress
                    return WhatsAppMessage.from_core_message(message)

            # Start new flow if none active
            logger.debug("Starting new registration flow")

            # Initialize flow_data
            current_state["flow_data"] = {
                "data": {
                    "phone": self.service.user.mobile_number
                }
            }
            logger.debug(f"Initial flow_data: {current_state['flow_data']['data']}")

            # Update state with new flow
            self._update_registration_state(
                current_state=current_state,
                stage=StateStage.REGISTRATION.value,
                update_from="flow_init"
            )

            result = self.flow_handler.start_flow(
                self.FLOW_ID,
                self.service.user.mobile_number
            )

            # If result is a Flow instance
            if isinstance(result, RegistrationFlow):
                # Set initial state
                result.state.update(current_state["flow_data"]["data"])
                logger.debug(f"Flow state after initialization: {result.state}")

                # Get message from current step
                message = result.current_step.message
                if callable(message):
                    message = message(result.state)
                return WhatsAppMessage.from_core_message(message)

            # If result is already a message or dict
            return WhatsAppMessage.from_core_message(result)

        except Exception as e:
            logger.exception(f"Error handling registration: {str(e)}")
            error_message = self._format_error_response(str(e))
            return WhatsAppMessage.from_core_message(error_message)

    def _format_error_response(self, error_message: str) -> Dict[str, Any]:
        """Format error response message"""
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self.service.user.mobile_number,
            "type": "text",
            "text": {
                "body": f"❌ Error: {error_message}\n\nPlease try again."
            }
        }

    def _format_success_response(self, message: str) -> Dict[str, Any]:
        """Format success response message"""
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self.service.user.mobile_number,
            "type": "text",
            "text": {
                "body": f"✅ {message}"
            }
        }

    def _format_message_response(self, message: str) -> Dict[str, Any]:
        """Format generic message response"""
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self.service.user.mobile_number,
            "type": "text",
            "text": {
                "body": message
            }
        }
