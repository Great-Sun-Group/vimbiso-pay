"""Implementation of credex action flows (accept/decline/cancel)"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.messaging.flow import Flow, Step, StepType
from core.messaging.templates import ButtonSelection
from core.messaging.types import Message as WhatsAppMessage
from services.state.service import StateStage

logger = logging.getLogger(__name__)


class CredexActionFlow(Flow):
    """Base flow for credex actions (accept/decline/cancel)"""

    def __init__(self, id: str, action: str):
        self.action = action
        super().__init__(id, self._create_steps())
        self.credex_service = None  # Should be injected
        self.state_service = None  # Should be injected

    def _create_steps(self) -> list[Step]:
        """Create flow steps"""
        return [
            # Step 1: Confirmation
            Step(
                id="confirm",
                type=StepType.BUTTON_SELECT,
                stage=StateStage.CREDEX.value,
                message=self._create_confirmation_message,
                validation=lambda value: value in ["confirm", "cancel"],
                transform=lambda value: {"confirmed": value == "confirm"}
            )
        ]

    def _create_confirmation_message(self, state: Dict[str, Any]) -> WhatsAppMessage:
        """Create confirmation message based on action"""
        # Get credex details from state
        credex_id = state.get("credex_id")
        if not credex_id:
            raise ValueError("Missing credex ID")

        # Get amount info
        amount_data = state.get("amount", {})
        formatted_amount = f"${amount_data.get('amount', '0')}"

        # Get sender/recipient info
        sender = state.get("sender_name", "Unknown Sender")
        recipient = state.get("recipient_name", "Unknown Recipient")

        # Create action-specific message
        action_messages = {
            "accept": f"Accept credex offer for {formatted_amount}\nFrom: {sender}",
            "decline": f"Decline credex offer for {formatted_amount}\nFrom: {sender}",
            "cancel": f"Cancel credex offer for {formatted_amount}\nTo: {recipient}"
        }

        message = action_messages.get(self.action, "Invalid action")

        return ButtonSelection.create_buttons({
            "text": message,
            "buttons": [
                {"id": "confirm", "title": f"Confirm {self.action.title()}"},
                {"id": "cancel", "title": "Cancel"}
            ]
        }, state.get("phone", ""))

    def _has_required_data(self, state: Dict[str, Any]) -> bool:
        """Check if state has all required data"""
        return bool(
            state.get("credex_id") and
            state.get("phone") and
            isinstance(state.get("amount", {}), dict)
        )

    def complete_flow(self) -> Tuple[bool, str]:
        """Complete the flow by executing the credex action"""
        try:
            # Check if we have required data
            if not self._has_required_data(self.state):
                return False, "Missing required data"

            # Check if confirmed
            if not self.state.get("confirm", {}).get("confirmed"):
                return False, "Action not confirmed"

            # Check if credex service is initialized
            if not self.credex_service:
                return False, "Credex service not initialized"

            # Get credex ID
            credex_id = self.state.get("credex_id")

            # Execute action
            if self.action == "accept":
                success, response = self.credex_service.accept_credex(credex_id)
            elif self.action == "decline":
                success, response = self.credex_service.decline_credex(credex_id)
            elif self.action == "cancel":
                success, response = self.credex_service.cancel_credex(credex_id)
            else:
                return False, f"Invalid action: {self.action}"

            if not success:
                return False, response.get("message") if isinstance(response, dict) else f"Failed to {self.action} offer"

            # Get fresh dashboard data
            success, data = self.credex_service._member.get_dashboard(self.state.get("phone"))
            if success:
                # Update service state with fresh data
                current_state = self.state.copy()
                current_state["profile"] = data
                current_state["last_refresh"] = True
                current_state["current_account"] = None
                # Preserve JWT token
                if self.credex_service.jwt_token:
                    current_state["jwt_token"] = self.credex_service.jwt_token

                # Update state service
                if self.state_service:
                    self.state_service.update_state(
                        user_id=self.state.get("phone"),
                        new_state=current_state,
                        stage=StateStage.MENU.value,
                        update_from=f"{self.action}_complete",
                        option="handle_action_menu"
                    )

            return True, f"Successfully {self.action}ed credex offer"

        except Exception as e:
            logger.exception(f"Error completing {self.action} flow")
            return False, str(e)


class AcceptCredexFlow(CredexActionFlow):
    """Flow for accepting credex offers"""
    FLOW_ID = "accept_credex"

    def __init__(self, id: str):
        super().__init__(id, "accept")

    @classmethod
    def get_flow_by_id(cls, flow_id: str) -> Optional[Flow]:
        """Get flow instance by ID"""
        if flow_id == cls.FLOW_ID:
            return cls(flow_id)
        return None


class DeclineCredexFlow(CredexActionFlow):
    """Flow for declining credex offers"""
    FLOW_ID = "decline_credex"

    def __init__(self, id: str):
        super().__init__(id, "decline")

    @classmethod
    def get_flow_by_id(cls, flow_id: str) -> Optional[Flow]:
        """Get flow instance by ID"""
        if flow_id == cls.FLOW_ID:
            return cls(flow_id)
        return None


class CancelCredexFlow(CredexActionFlow):
    """Flow for canceling credex offers"""
    FLOW_ID = "cancel_credex"

    def __init__(self, id: str):
        super().__init__(id, "cancel")

    @classmethod
    def get_flow_by_id(cls, flow_id: str) -> Optional[Flow]:
        """Get flow instance by ID"""
        if flow_id == cls.FLOW_ID:
            return cls(flow_id)
        return None
