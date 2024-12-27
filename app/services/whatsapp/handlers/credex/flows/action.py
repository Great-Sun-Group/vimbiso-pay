"""Action flows implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, List

from core.messaging.flow import Step, StepType
from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator

from .base import CredexFlow
from .dashboard_handler import CredexDashboardHandler
from .messages import create_list_message, create_action_confirmation

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class ActionFlow(CredexFlow):
    """Base class for credex action flows (accept/decline/cancel) with strict state management"""

    def __init__(self, state_manager: Any, flow_type: str) -> None:
        """Initialize with state manager enforcing SINGLE SOURCE OF TRUTH

        Args:
            state_manager: State manager instance
            flow_type: Type of action flow (cancel/accept/decline)

        Raises:
            ValueError: If state validation fails or required data missing
        """
        if not state_manager:
            raise ValueError("State manager required")
        if not flow_type or flow_type not in {"cancel", "accept", "decline"}:
            raise ValueError("Invalid flow type")

        # Validate ALL required state at boundary
        required_fields = {"channel", "member_id", "authenticated", "flow_data"}
        current_state = {
            field: state_manager.get(field)
            for field in required_fields
        }

        # Initial validation
        validation = StateValidator.validate_before_access(
            current_state,
            {"channel", "member_id"}  # Core requirements
        )
        if not validation.is_valid:
            raise ValueError(f"State validation failed: {validation.error_message}")

        # Get channel info (SINGLE SOURCE OF TRUTH)
        channel = state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            raise ValueError("Channel identifier not found")

        # Initialize base class
        super().__init__(id=f"{flow_type}_flow")

        # Initialize services
        self.flow_type = flow_type
        self.state_manager = state_manager
        self.credex_service = state_manager.get_credex_service()
        if not self.credex_service:
            raise ValueError("Failed to initialize credex service")

        self.dashboard = CredexDashboardHandler(state_manager)
        if not self.dashboard:
            raise ValueError("Failed to initialize dashboard handler")

        self.steps = self._create_steps()

        # Log initialization
        audit.log_flow_event(
            self.id,
            "initialization",
            None,
            {
                "flow_type": flow_type,
                "channel_id": channel["identifier"]
            },
            "success"
        )

        logger.info(f"Initialized {flow_type} flow for channel {channel['identifier']}")

    def _create_steps(self) -> List[Step]:
        """Create steps for action flow with strict state validation"""
        return [
            Step(
                id="list",
                type=StepType.LIST,
                message=self._get_list_message,
                validator=self._validate_selection,
                transformer=self._store_selection
            ),
            Step(
                id="confirm",
                type=StepType.BUTTON,
                message=self._get_confirmation_message,
                validator=lambda x: x.lower() in ["yes", "no"]
            )
        ]

    def _get_list_message(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Get list message with strict state validation"""
        channel = self.state_manager.get("channel")
        return create_list_message(channel["identifier"], self.flow_type)

    def _validate_selection(self, selection: str) -> bool:
        """Validate selection input"""
        return selection.startswith(f"{self.flow_type}_")

    def _store_selection(self, selection: str) -> None:
        """Store selection enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate input
            if not selection or not isinstance(selection, str):
                raise ValueError("Invalid selection value")

            # Extract credex ID
            credex_id = selection[len(self.flow_type) + 1:] if selection.startswith(f"{self.flow_type}_") else None
            if not credex_id:
                raise ValueError("Invalid selection format")

            # Get flow data (SINGLE SOURCE OF TRUTH)
            flow_data = self.state_manager.get("flow_data")
            if not isinstance(flow_data, dict):
                flow_data = {}

            # Prepare new flow data
            new_flow_data = flow_data.copy()
            new_flow_data["selected_credex_id"] = credex_id

            # Validate state update
            new_state = {"flow_data": new_flow_data}
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                raise ValueError(f"Invalid flow data: {validation.error_message}")

            # Update state
            success, error = self.state_manager.update_state(new_state)
            if not success:
                raise ValueError(f"Failed to update flow data: {error}")

            # Log success
            channel = self.state_manager.get("channel")
            logger.info(f"Stored credex ID {credex_id} for {self.flow_type} flow on channel {channel['identifier']}")

        except ValueError as e:
            # Get channel info for error logging
            try:
                channel = self.state_manager.get("channel")
                channel_id = channel["identifier"] if channel else "unknown"
            except (ValueError, KeyError, TypeError) as err:
                logger.error(f"Failed to get channel for error logging: {str(err)}")
                channel_id = "unknown"

            logger.error(f"Failed to store selection: {str(e)} for channel {channel_id}")
            raise

    def _get_confirmation_message(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Get confirmation message with strict state validation"""
        try:
            # Validate state access at boundary
            validation = StateValidator.validate_before_access(
                {
                    "channel": self.state_manager.get("channel"),
                    "flow_data": self.state_manager.get("flow_data")
                },
                {"channel", "flow_data"}
            )
            if not validation.is_valid:
                raise ValueError(validation.error_message)

            channel = self.state_manager.get("channel")
            flow_data = self.state_manager.get("flow_data")

            return create_action_confirmation(
                channel["identifier"],
                flow_data["selected_credex_id"],
                self.flow_type
            )

        except ValueError as e:
            logger.error(f"Failed to create confirmation message: {str(e)}")
            raise

    def complete(self) -> Dict[str, Any]:
        """Complete action flow enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate ALL required state at boundary
            required_fields = {"channel", "member_id", "flow_data", "authenticated"}
            current_state = {
                field: self.state_manager.get(field)
                for field in required_fields
            }

            # Validate required fields
            validation = StateValidator.validate_before_access(
                current_state,
                {"channel", "member_id", "flow_data"}
            )
            if not validation.is_valid:
                raise ValueError(f"State validation failed: {validation.error_message}")

            # Get channel info (SINGLE SOURCE OF TRUTH)
            channel = self.state_manager.get("channel")
            if not channel or not channel.get("identifier"):
                raise ValueError("Channel identifier not found")

            # Get and validate flow data (SINGLE SOURCE OF TRUTH)
            flow_data = self.state_manager.get("flow_data")
            if not isinstance(flow_data, dict):
                raise ValueError("Invalid flow data format")

            # Get and validate credex ID
            credex_id = flow_data.get("selected_credex_id")
            if not credex_id:
                raise ValueError("Missing credex ID")

            # Log action attempt
            audit.log_flow_event(
                self.id,
                f"{self.flow_type}_attempt",
                None,
                {
                    "credex_id": credex_id,
                    "channel_id": channel["identifier"]
                },
                "in_progress"
            )

            # Make API call
            success, response = getattr(self.credex_service, f"{self.flow_type}_credex")(credex_id)
            if not success:
                error_msg = response.get("message", f"Failed to {self.flow_type} offer")
                logger.error(f"API call failed: {error_msg} for channel {channel['identifier']}")
                raise ValueError(error_msg)

            # Update dashboard
            try:
                self.dashboard.update(response)
            except ValueError as err:
                logger.error(f"Dashboard update failed: {str(err)} for channel {channel['identifier']}")
                raise ValueError(f"Failed to update dashboard: {str(err)}")

            # Log success
            audit.log_flow_event(
                self.id,
                f"{self.flow_type}_success",
                None,
                {
                    "credex_id": credex_id,
                    "channel_id": channel["identifier"],
                    "response": response
                },
                "success"
            )

            logger.info(f"Successfully completed {self.flow_type} flow for channel {channel['identifier']}")

            return {
                "success": True,
                "message": f"Successfully {self.flow_type}ed credex offer",
                "response": response
            }

        except ValueError as e:
            # Get channel info for error logging
            try:
                channel = self.state_manager.get("channel")
                channel_id = channel["identifier"] if channel else "unknown"
            except (ValueError, KeyError, TypeError) as err:
                logger.error(f"Failed to get channel for error logging: {str(err)}")
                channel_id = "unknown"

            logger.error(f"Failed to complete {self.flow_type}: {str(e)} for channel {channel_id}")
            raise


class CancelFlow(ActionFlow):
    """Flow for canceling a credex offer"""

    def __init__(self, state_manager: Any) -> None:
        super().__init__(state_manager=state_manager, flow_type="cancel")


class AcceptFlow(ActionFlow):
    """Flow for accepting a credex offer"""

    def __init__(self, state_manager: Any) -> None:
        super().__init__(state_manager=state_manager, flow_type="accept")


class DeclineFlow(ActionFlow):
    """Flow for declining a credex offer"""

    def __init__(self, state_manager: Any) -> None:
        super().__init__(state_manager=state_manager, flow_type="decline")
