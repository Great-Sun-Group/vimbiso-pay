"""Unified member flows implementation"""
import logging
from datetime import datetime
from typing import Dict, Any, List

from core.messaging.flow import Flow, Step, StepType
from core.messaging.types import Message
from .templates import MemberTemplates

logger = logging.getLogger(__name__)


class MemberFlow(Flow):
    """Base class for all member-related flows"""

    def __init__(self, flow_type: str, **kwargs):
        """Initialize flow"""
        self.flow_type = flow_type
        self.kwargs = kwargs
        steps = self._create_steps()
        super().__init__(f"member_{flow_type}", steps)
        self.credex_service = None

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
        if not name:
            return False
        name = name.strip()
        return (
            3 <= len(name) <= 50 and
            name.replace(" ", "").isalpha()
        )

    def _validate_button_response(self, response: Dict[str, Any]) -> bool:
        """Validate button response"""
        return (
            response.get("type") == "interactive" and
            response.get("interactive", {}).get("type") == "button_reply" and
            response.get("interactive", {}).get("button_reply", {}).get("id") == "confirm_action"
        )

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
                return

            dashboard = response.get("data", {}).get("dashboard")
            if not dashboard:
                return

            user_state = self.credex_service._parent_service.user.state
            current_state = user_state.state
            current_profile = current_state.get("profile", {}).copy()

            # Preserve existing profile data
            if "data" in current_profile:
                current_profile["data"]["dashboard"] = dashboard
            else:
                current_profile["data"] = {"dashboard": dashboard}

            # Update state while preserving critical fields
            user_state.update_state({
                "profile": current_profile,
                "current_account": current_state.get("current_account"),
                "jwt_token": current_state.get("jwt_token")
            }, "dashboard_update")

        except Exception as e:
            logger.error(f"Dashboard update error: {str(e)}")

    def complete(self) -> Message:
        """Complete the flow"""
        try:
            if not self.credex_service:
                raise ValueError("Service not initialized")

            if self.flow_type == "registration":
                return self._complete_registration()
            return self._complete_upgrade()

        except Exception as e:
            logger.error(f"Flow completion error: {str(e)}")
            return MemberTemplates.create_error_message(
                self.data.get("mobile_number"),
                str(e)
            )

    def _complete_registration(self) -> Message:
        """Complete registration flow"""
        # Get registration data
        first_name = self.data["first_name"]["first_name"]
        last_name = self.data["last_name"]["last_name"]
        phone = self.data.get("phone")

        if not phone:
            raise ValueError("Missing phone number")

        # Register member
        success, response = self.credex_service._auth.register_member({
            "phone": phone,
            "firstname": first_name,
            "lastname": last_name,
            "defaultDenom": "USD"
        })

        if not success:
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
                self.credex_service._parent_service.user.state.update_state({
                    "jwt_token": token,
                    "authenticated": True
                }, "registration_auth")

        return MemberTemplates.create_registration_success(
            self.data.get("mobile_number"),
            first_name
        )

    def _complete_upgrade(self) -> Message:
        """Complete tier upgrade flow"""
        account_id = self.data.get("account_id")
        if not account_id:
            raise ValueError("Missing account ID")

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
            raise ValueError(response.get("message", "Failed to process subscription"))

        # Update dashboard state
        self._update_dashboard(response)

        return MemberTemplates.create_upgrade_success(
            self.data.get("mobile_number")
        )
