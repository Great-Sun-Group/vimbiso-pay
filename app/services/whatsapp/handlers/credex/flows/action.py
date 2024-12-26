"""Action flows implementation for accept, decline and cancel"""
import logging
from typing import Any, Dict, List, Optional

from core.messaging.flow import Step, StepType, FlowState
from core.utils.flow_audit import FlowAuditLogger

from .base import CredexFlow

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class ActionFlow(CredexFlow):
    """Base class for credex action flows (accept/decline/cancel)"""

    def __init__(self, id: str, steps: List[Step] = None, flow_type: str = None, state: Optional[FlowState] = None, **kwargs):
        """Initialize action flow with proper state management"""
        try:
            # Set action prefix before parent initialization
            self.action_prefix = flow_type  # e.g. "cancel_", "accept_", "decline_"

            # Create steps if not provided
            if steps is None:
                steps = self._create_steps()

            # Initialize base CredexFlow class
            super().__init__(
                id=id,
                steps=steps,
                flow_type=flow_type,
                state=state,
                **kwargs
            )

            # Get member ID from state if available
            member_id = state.member_id if state else None
            channel = {"type": "whatsapp", "identifier": self._get_channel_identifier()} if self.credex_service else None

            # Log initialization with member context
            audit.log_flow_event(
                self.id,
                "initialization",
                None,
                {
                    "flow_type": flow_type,
                    "member_id": member_id,
                    "channel": channel,
                    **kwargs
                },
                "success"
            )

        except Exception as e:
            # Log initialization error
            error_msg = f"Flow initialization error: {str(e)}"
            logger.error(error_msg)
            audit.log_flow_event(
                id,  # Use provided ID instead of flow_id
                "initialization_error",
                None,
                {
                    "error": error_msg,
                    "flow_type": flow_type
                },
                "failure"
            )
            raise

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

        # Get offers from current account
        if self.flow_type in ["accept", "decline"]:
            pending_offers = self.data.get("current_account", {}).get("pendingInData", [])
        else:
            pending_offers = self.data.get("current_account", {}).get("pendingOutData", [])

        if not pending_offers:
            return {"error": "No pending offers found"}

        selected_offer = next(
            (offer for offer in pending_offers if offer["credexID"] == credex_id),
            None
        )

        if not selected_offer:
            return {"error": "Selected offer not found"}

        result = {
            "credex_id": credex_id,
            "amount": selected_offer["formattedInitialAmount"],
            "counterparty": selected_offer["counterpartyAccountName"]
        }

        # Update flow data with the transformed selection
        self.data.update(result)

        # Get member ID and channel info from top level state - SINGLE SOURCE OF TRUTH
        current_state = self.credex_service._parent_service.user.state.state
        member_id = current_state.get("member_id")
        channel = current_state.get("channel")

        # Log selection with member context
        audit.log_flow_event(
            self.id,
            "selection_transform",
            None,
            {
                "member_id": member_id,  # Get from top level state
                "channel": channel,  # Get from top level state
                "selection": result
            },
            "success"
        )

        return result

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

        # Get member ID and channel info from top level state - SINGLE SOURCE OF TRUTH
        current_state = self.credex_service._parent_service.user.state.state
        member_id = current_state.get("member_id")
        if not member_id:
            return {
                "success": False,
                "message": "Missing member ID in state"
            }

        channel_id = self._get_channel_identifier()
        if not channel_id:
            return {
                "success": False,
                "message": "Missing channel identifier"
            }

        # Log action attempt with member context
        audit_context = {
            "member_id": member_id,
            "channel": {
                "type": "whatsapp",
                "identifier": channel_id
            },
            "credex_id": credex_id
        }
        audit.log_flow_event(
            self.id,
            f"{self.flow_type}_attempt",
            None,
            audit_context,
            "in_progress"
        )

        actions = {
            "cancel": self.credex_service.cancel_credex,
            "accept": self.credex_service.accept_credex,
            "decline": self.credex_service.decline_credex
        }

        # Add member context to API call
        success, response = actions[self.flow_type]({
            "credex_id": credex_id,
            "member_id": member_id,
            "channel": {
                "type": "whatsapp",
                "identifier": channel_id
            }
        })

        if not success:
            action_name = self.flow_type.replace("_credex", "")
            error_msg = response.get("message", f"Failed to {action_name} offer")

            # Log error with member context
            audit.log_flow_event(
                self.id,
                f"{self.flow_type}_error",
                None,
                {**audit_context, "error": error_msg},
                "failure"
            )

            return {
                "success": False,
                "message": error_msg,
                "response": response
            }

        # Update dashboard with member-centric state
        self._update_dashboard(response)

        # Log success with member context
        audit.log_flow_event(
            self.id,
            f"{self.flow_type}_success",
            None,
            {**audit_context, "response": response},
            "success"
        )

        return {
            "success": True,
            "message": f"Successfully {self.flow_type.replace('_credex', '')}ed credex offer",
            "response": response
        }


class CancelFlow(ActionFlow):
    """Flow for canceling a credex offer"""

    def __init__(self, id: str, steps: List[Step] = None, state: Optional[FlowState] = None, **kwargs):
        super().__init__(id=id, steps=steps, flow_type="cancel", state=state, **kwargs)


class AcceptFlow(ActionFlow):
    """Flow for accepting a credex offer"""

    def __init__(self, id: str, steps: List[Step] = None, state: Optional[FlowState] = None, **kwargs):
        super().__init__(id=id, steps=steps, flow_type="accept", state=state, **kwargs)


class DeclineFlow(ActionFlow):
    """Flow for declining a credex offer"""

    def __init__(self, id: str, steps: List[Step] = None, state: Optional[FlowState] = None, **kwargs):
        super().__init__(id=id, steps=steps, flow_type="decline", state=state, **kwargs)
