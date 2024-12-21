"""Action flows implementation for accept, decline and cancel"""
import logging
from typing import Any, Dict, List

from core.messaging.flow import Step, StepType

from .base import CredexFlow

logger = logging.getLogger(__name__)


class ActionFlow(CredexFlow):
    """Base class for credex action flows (accept/decline/cancel)"""

    def __init__(self, flow_type: str = None, state: Dict = None, **kwargs):
        # Extract flow type from state if not provided directly
        if flow_type is None and state is not None:
            flow_data = state.get('flow_data', {})
            flow_type = flow_data.get('flow_type')

        if flow_type is None:
            raise ValueError("flow_type must be provided either directly or through state")

        # Set action prefix before parent initialization
        self.action_prefix = flow_type  # e.g. "cancel_", "accept_", "decline_"
        super().__init__(flow_type=flow_type, state=state, **kwargs)

    def _create_steps(self) -> List[Step]:
        """Create steps for action flow"""
        return [
            Step(
                id="list",
                type=StepType.LIST,
                message=self._create_list_message,
                validator=lambda x: x.startswith(f"{self.action_prefix}_"),
                transformer=self._transform_selection
            ),
            Step(
                id="confirm",
                type=StepType.BUTTON,
                message=self._create_confirmation_message,
                validator=self._validate_button_response
            )
        ]

    def _transform_selection(self, selection: str) -> Dict[str, Any]:
        """Transform list selection into credex data"""
        credex_id = selection[len(self.action_prefix) + 1:] if selection.startswith(f"{self.action_prefix}_") else None
        if not credex_id:
            return {"error": "Invalid selection"}

        pending_offers = self.data.get("pending_offers", [])
        selected_offer = next(
            (offer for offer in pending_offers if offer["id"] == credex_id),
            None
        )

        if not selected_offer:
            return {"error": "Selected offer not found"}

        return {
            "credex_id": credex_id,
            "amount": selected_offer["amount"],
            "counterparty": selected_offer["to"]
        }

    def complete(self) -> Dict[str, Any]:
        """Complete the action flow"""
        if self.current_step.id != "confirm":
            return {
                "success": False,
                "message": "Confirmation required"
            }

        credex_id = self.data.get("credex_id")
        if not credex_id:
            return {
                "success": False,
                "message": "Missing credex ID"
            }

        actions = {
            "cancel": self.credex_service.cancel_credex,
            "accept": self.credex_service.accept_credex,
            "decline": self.credex_service.decline_credex
        }

        success, response = actions[self.flow_type](credex_id)
        if not success:
            action_name = self.flow_type.replace("_credex", "")
            return {
                "success": False,
                "message": response.get("message", f"Failed to {action_name} offer"),
                "response": response
            }

        self._update_dashboard(response)
        return {
            "success": True,
            "message": f"Successfully {self.flow_type.replace('_credex', '')}ed credex offer",
            "response": response
        }


class CancelFlow(ActionFlow):
    """Flow for canceling a credex offer"""

    def __init__(self, flow_type: str = None, state: Dict = None, **kwargs):
        # Default to cancel if not provided
        if flow_type is None and (state is None or "flow_type" not in state.get("flow_data", {})):
            flow_type = "cancel"
        super().__init__(flow_type=flow_type, state=state, **kwargs)


class AcceptFlow(ActionFlow):
    """Flow for accepting a credex offer"""

    def __init__(self, flow_type: str = None, state: Dict = None, **kwargs):
        # Default to accept if not provided
        if flow_type is None and (state is None or "flow_type" not in state.get("flow_data", {})):
            flow_type = "accept"
        super().__init__(flow_type=flow_type, state=state, **kwargs)


class DeclineFlow(ActionFlow):
    """Flow for declining a credex offer"""

    def __init__(self, flow_type: str = None, state: Dict = None, **kwargs):
        # Default to decline if not provided
        if flow_type is None and (state is None or "flow_type" not in state.get("flow_data", {})):
            flow_type = "decline"
        super().__init__(flow_type=flow_type, state=state, **kwargs)
