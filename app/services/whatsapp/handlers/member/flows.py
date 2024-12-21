"""Unified member flows implementation"""
import logging
from datetime import datetime
from typing import Dict, Any, List

from core.messaging.flow import Flow, Step, StepType
from core.messaging.types import Message
from core.utils.flow_audit import FlowAuditLogger
from .templates import MemberTemplates
from .validator import MemberFlowValidator

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class MemberFlow(Flow):
    """Base class for all member-related flows"""

    def __init__(self, flow_type: str, **kwargs):
        """Initialize flow"""
        self.flow_type = flow_type
        self.kwargs = kwargs
        self.validator = MemberFlowValidator()
        steps = self._create_steps()
        super().__init__(f"member_{flow_type}", steps)
        self.credex_service = None

        # Log flow initialization
        audit.log_flow_event(
            self.id,
            "initialization",
            None,
            {"flow_type": flow_type, **kwargs},
            "success"
        )

    def _create_steps(self) -> List[Step]:
        """Create flow steps based on type"""
        if self.flow_type == "registration":
            return [
                Step(
                    id="first_name",
                    type=StepType.TEXT,
                    message=self._get_first_name_prompt,
                    validator=self._validate_name,
                    transformer=lambda value: {"first_name": value.strip()}
                ),
                Step(
                    id="last_name",
                    type=StepType.TEXT,
                    message=self._get_last_name_prompt,
                    validator=self._validate_name,
                    transformer=lambda value: {"last_name": value.strip()}
                ),
                Step(
                    id="confirm",
                    type=StepType.BUTTON,
                    message=self._create_confirmation_message,
                    validator=self._validate_button_response
                )
            ]
        else:  # upgrade flow
            return [
                Step(
                    id="confirm",
                    type=StepType.BUTTON,
                    message=self._create_confirmation_message,
                    validator=self._validate_button_response
                )
            ]

    def _get_first_name_prompt(self, _) -> Message:
        """Get first name prompt"""
        return MemberTemplates.create_first_name_prompt(
            self.data.get("mobile_number")
        )

    def _get_last_name_prompt(self, _) -> Message:
        """Get last name prompt"""
        return MemberTemplates.create_last_name_prompt(
            self.data.get("mobile_number")
        )

    def _validate_name(self, name: str) -> bool:
        """Validate name input"""
        try:
            if not name:
                return False
            name = name.strip()
            is_valid = (
                3 <= len(name) <= 50 and
                name.replace(" ", "").isalpha()
            )

            audit.log_validation_event(
                self.id,
                self.current_step.id,
                name,
                is_valid,
                None if is_valid else "Invalid name format"
            )
            return is_valid

        except Exception as e:
            audit.log_validation_event(
                self.id,
                self.current_step.id,
                name,
                False,
                str(e)
            )
            return False

    def _validate_button_response(self, response: Dict[str, Any]) -> bool:
        """Validate button response"""
        try:
            is_valid = (
                response.get("type") == "interactive" and
                response.get("interactive", {}).get("type") == "button_reply" and
                response.get("interactive", {}).get("button_reply", {}).get("id") == "confirm_action"
            )

            audit.log_validation_event(
                self.id,
                self.current_step.id,
                response,
                is_valid,
                None if is_valid else "Invalid button response"
            )
            return is_valid

        except Exception as e:
            audit.log_validation_event(
                self.id,
                self.current_step.id,
                response,
                False,
                str(e)
            )
            return False

    def _create_confirmation_message(self, state: Dict[str, Any]) -> Message:
        """Create confirmation message based on flow type"""
        if self.flow_type == "registration":
            return self._create_registration_confirmation(state)
        return self._create_upgrade_confirmation(state)

    def _create_registration_confirmation(self, state: Dict[str, Any]) -> Message:
        """Create registration confirmation message"""
        first_name = state["first_name"]["first_name"]
        last_name = state["last_name"]["last_name"]

        return MemberTemplates.create_registration_confirmation(
            recipient=self.data.get("mobile_number"),
            first_name=first_name,
            last_name=last_name
        )

    def _create_upgrade_confirmation(self, _: Dict[str, Any]) -> Message:
        """Create tier upgrade confirmation message"""
        return MemberTemplates.create_upgrade_confirmation(
            self.data.get("mobile_number")
        )

    def _update_dashboard(self, response: Dict[str, Any]) -> None:
        """Update dashboard state"""
        try:
            if not hasattr(self.credex_service, '_parent_service'):
                audit.log_flow_event(
                    self.id,
                    "dashboard_update_error",
                    None,
                    self.data,
                    "failure",
                    "Service not properly initialized"
                )
                return

            dashboard = response.get("data", {}).get("dashboard")
            if not dashboard:
                audit.log_flow_event(
                    self.id,
                    "dashboard_update_error",
                    None,
                    self.data,
                    "failure",
                    "No dashboard data in response"
                )
                return

            user_state = self.credex_service._parent_service.user.state
            current_state = user_state.state

            # Validate current state
            validation = self.validator.validate_flow_state(current_state)
            if not validation.is_valid:
                audit.log_flow_event(
                    self.id,
                    "state_validation_error",
                    None,
                    current_state,
                    "failure",
                    validation.error_message
                )
                # Attempt recovery from last valid state
                last_valid = audit.get_last_valid_state(self.id)
                if last_valid:
                    current_state = last_valid

            current_profile = current_state.get("profile", {}).copy()

            # Preserve existing profile data
            if "data" in current_profile:
                current_profile["data"]["dashboard"] = dashboard
            else:
                current_profile["data"] = {"dashboard": dashboard}

            # Prepare new state
            new_state = {
                "profile": current_profile,
                "current_account": current_state.get("current_account"),
                "jwt_token": current_state.get("jwt_token"),
                "member_id": current_state.get("member_id"),
                "account_id": current_state.get("account_id")
            }

            # Validate new state
            validation = self.validator.validate_flow_state(new_state)
            if not validation.is_valid:
                audit.log_flow_event(
                    self.id,
                    "state_validation_error",
                    None,
                    new_state,
                    "failure",
                    validation.error_message
                )
                return

            # Log state transition
            audit.log_state_transition(
                self.id,
                current_state,
                new_state,
                "success"
            )

            user_state.update_state(new_state, "dashboard_update")

        except Exception as e:
            logger.error(f"Dashboard update error: {str(e)}")
            audit.log_flow_event(
                self.id,
                "dashboard_update_error",
                None,
                self.data,
                "failure",
                str(e)
            )

    def complete(self) -> Message:
        """Complete the flow"""
        try:
            # Validate final state
            validation = self.validator.validate_flow_state(self.data)
            if not validation.is_valid:
                audit.log_flow_event(
                    self.id,
                    "completion_validation_error",
                    None,
                    self.data,
                    "failure",
                    validation.error_message
                )
                return MemberTemplates.create_error_message(
                    self.data.get("mobile_number"),
                    f"Invalid flow state: {validation.error_message}"
                )

            if not self.credex_service:
                audit.log_flow_event(
                    self.id,
                    "completion_error",
                    None,
                    self.data,
                    "failure",
                    "Service not initialized"
                )
                return MemberTemplates.create_error_message(
                    self.data.get("mobile_number"),
                    "Service not initialized"
                )

            if self.flow_type == "registration":
                return self._complete_registration()
            return self._complete_upgrade()

        except Exception as e:
            logger.error(f"Flow completion error: {str(e)}")
            audit.log_flow_event(
                self.id,
                "completion_error",
                None,
                self.data,
                "failure",
                str(e)
            )
            return MemberTemplates.create_error_message(
                self.data.get("mobile_number"),
                str(e)
            )

    def _complete_registration(self) -> Message:
        """Complete registration flow"""
        try:
            # Get registration data
            first_name = self.data["first_name"]["first_name"]
            last_name = self.data["last_name"]["last_name"]
            phone = self.data.get("phone")

            if not phone:
                raise ValueError("Missing phone number")

            # Log registration attempt
            audit.log_flow_event(
                self.id,
                "registration_attempt",
                None,
                {
                    "first_name": first_name,
                    "last_name": last_name,
                    "phone": phone
                },
                "in_progress"
            )

            # Register member
            success, response = self.credex_service._auth.register_member({
                "phone": phone,
                "firstname": first_name,
                "lastname": last_name,
                "defaultDenom": "USD"
            })

            if not success:
                audit.log_flow_event(
                    self.id,
                    "registration_error",
                    None,
                    response,
                    "failure",
                    response.get("message", "Registration failed")
                )
                raise ValueError(response.get("message", "Registration failed"))

            # Update dashboard state
            self._update_dashboard(response)

            # Store JWT token
            if token := (
                response.get("data", {})
                .get("action", {})
                .get("details", {})
                .get("token")
            ):
                if hasattr(self.credex_service, '_parent_service'):
                    new_state = {
                        "jwt_token": token,
                        "authenticated": True
                    }

                    # Validate auth state
                    validation = self.validator.validate_flow_state(new_state)
                    if validation.is_valid:
                        self.credex_service._parent_service.user.state.update_state(
                            new_state,
                            "registration_auth"
                        )

            audit.log_flow_event(
                self.id,
                "registration_complete",
                None,
                response,
                "success"
            )

            return MemberTemplates.create_registration_success(
                self.data.get("mobile_number"),
                first_name
            )

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            audit.log_flow_event(
                self.id,
                "registration_error",
                None,
                self.data,
                "failure",
                str(e)
            )
            raise

    def _complete_upgrade(self) -> Message:
        """Complete tier upgrade flow"""
        try:
            account_id = self.data.get("account_id")
            if not account_id:
                raise ValueError("Missing account ID")

            # Log upgrade attempt
            audit.log_flow_event(
                self.id,
                "upgrade_attempt",
                None,
                {"account_id": account_id},
                "in_progress"
            )

            # Create recurring payment
            success, response = self.credex_service._recurring.create_recurring({
                "sourceAccountID": account_id,
                "templateType": "MEMBERTIER_SUBSCRIPTION",
                "payFrequency": 28,
                "startDate": datetime.now().strftime("%Y-%m-%d"),
                "memberTier": 3,
                "securedCredex": True,
                "amount": 1.00,
                "denomination": "USD"
            })

            if not success:
                audit.log_flow_event(
                    self.id,
                    "upgrade_error",
                    None,
                    response,
                    "failure",
                    response.get("message", "Failed to process subscription")
                )
                raise ValueError(response.get("message", "Failed to process subscription"))

            # Update dashboard state
            self._update_dashboard(response)

            audit.log_flow_event(
                self.id,
                "upgrade_complete",
                None,
                response,
                "success"
            )

            return MemberTemplates.create_upgrade_success(
                self.data.get("mobile_number")
            )

        except Exception as e:
            logger.error(f"Upgrade error: {str(e)}")
            audit.log_flow_event(
                self.id,
                "upgrade_error",
                None,
                self.data,
                "failure",
                str(e)
            )
            raise
