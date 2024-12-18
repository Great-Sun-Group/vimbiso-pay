"""Unified member flows implementation"""
import logging
from typing import Dict, Any, List

from core.messaging.flow import Flow, Step, StepType

logger = logging.getLogger(__name__)


class MemberFlow(Flow):
    """Base class for all member-related flows"""

    def __init__(self, flow_type: str, **kwargs):
        """Initialize flow

        Args:
            flow_type: Type of flow ('registration', 'upgrade')
            **kwargs: Flow-specific arguments
        """
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
                    message=lambda _: "What's your first name?",
                    validator=self._validate_name,
                    transformer=lambda value: {"first_name": value.strip()}
                ),
                Step(
                    id="last_name",
                    type=StepType.TEXT,
                    message=lambda _: "And what's your last name?",
                    validator=self._validate_name,
                    transformer=lambda value: {"last_name": value.strip()}
                ),
                Step(
                    id="confirm",
                    type=StepType.BUTTON,
                    message=self._create_registration_confirmation,
                    validator=lambda x: x == "confirm"
                )
            ]
        else:  # upgrade flow
            return [
                Step(
                    id="confirm",
                    type=StepType.BUTTON,
                    message=self._create_upgrade_confirmation,
                    validator=lambda x: x == "confirm"
                )
            ]

    def _validate_name(self, name: str) -> bool:
        """Validate name input"""
        if not name:
            return False
        name = name.strip()
        return (
            3 <= len(name) <= 50 and
            name.replace(" ", "").isalpha()
        )

    def _create_registration_confirmation(self, state: Dict[str, Any]) -> str:
        """Create registration confirmation message"""
        first_name = state["first_name"]["first_name"]
        last_name = state["last_name"]["last_name"]

        return (
            f"✅ Please confirm your registration details:\n\n"
            f"First Name: {first_name}\n"
            f"Last Name: {last_name}\n"
            f"Default Currency: USD\n\n"
            "[confirm] Confirm Registration"
        )

    def _create_upgrade_confirmation(self, state: Dict[str, Any]) -> str:
        """Create tier upgrade confirmation message"""
        return (
            "*Upgrade to the Hustler tier for $1/month.*\n\n"
            "Subscribe with the button below to unlock unlimited credex transactions.\n\n"
            "Clicking below authorizes a $1 payment to be automatically processed "
            "from your credex account every 4 weeks (28 days), starting today.\n\n"
            "[confirm] Hustle Hard"
        )

    def _update_dashboard_state(self, response: Dict[str, Any]) -> None:
        """Update dashboard data in state from API response"""
        try:
            if not hasattr(self.credex_service, '_parent_service') or not hasattr(self.credex_service._parent_service, 'user'):
                logger.warning("Cannot update dashboard state: missing required service attributes")
                return

            # Get dashboard data from response
            dashboard = response.get("data", {}).get("dashboard")
            if dashboard is None:
                logger.warning("No dashboard data in response to update state with")
                return

            # Get current state
            user_state = self.credex_service._parent_service.user.state
            current_state = user_state.state
            current_profile = current_state.get("profile", {})

            # Update dashboard while preserving other profile data
            if "data" in current_profile:
                current_profile["data"]["dashboard"] = dashboard
            else:
                current_profile["data"] = {"dashboard": dashboard}

            # Update state
            user_state.update_state({
                "profile": current_profile
            }, "dashboard_update")

            logger.info(f"Successfully updated state with new dashboard data for {self.flow_type} operation")

        except Exception as e:
            logger.error(f"Failed to update dashboard state: {str(e)}")
            # Don't raise the error since this is a non-critical operation
            # The member operation itself was successful

    def complete(self) -> str:
        """Complete the flow"""
        try:
            if not self.credex_service:
                raise ValueError("Service not initialized")

            if self.flow_type == "registration":
                return self._complete_registration()
            else:
                return self._complete_upgrade()

        except Exception as e:
            logger.error(f"Flow completion error: {str(e)}")
            raise ValueError(str(e))

    def _complete_registration(self) -> str:
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

        # Update dashboard state with registration response
        self._update_dashboard_state(response)

        # Store JWT token and auth state
        token = (
            response.get("data", {})
            .get("action", {})
            .get("details", {})
            .get("token")
        )
        if token and hasattr(self.credex_service, '_parent_service') and hasattr(self.credex_service._parent_service, 'user'):
            self.credex_service._parent_service.user.state.update_state({
                "jwt_token": token,
                "authenticated": True
            }, "registration_auth")

        return f"Welcome {first_name}! Your account has been created successfully! 🎉"

    def _complete_upgrade(self) -> str:
        """Complete tier upgrade flow"""
        # Get account ID from state
        account_id = self.data.get("account_id")
        if not account_id:
            raise ValueError("Missing account ID")

        # Create recurring payment
        from datetime import datetime
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

        # Update dashboard state with upgrade response
        self._update_dashboard_state(response)

        return "🎉 Successfully upgraded to Hustler tier!"
