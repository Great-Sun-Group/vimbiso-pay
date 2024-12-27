"""Flow processing and continuation logic enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any

from core.messaging.flow import Flow
from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator

from ...types import WhatsAppMessage
from ..credex.flows.action import AcceptFlow, CancelFlow, DeclineFlow
from ..credex.flows.offer import OfferFlow
from ..member.dashboard import DashboardFlow
from ..member.registration import RegistrationFlow
from ..member.upgrade import UpgradeFlow

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class FlowProcessor:
    """Handles flow processing and continuation with strict state management"""

    FLOW_MAP = {
        "registration": RegistrationFlow,
        "upgrade": UpgradeFlow,
        "offer": OfferFlow,
        "accept": AcceptFlow,
        "decline": DeclineFlow,
        "cancel": CancelFlow
    }

    @staticmethod
    def process_flow(
        state_manager: Any,
        input_handler: Any,
        flow_data: dict
    ) -> WhatsAppMessage:
        """Process flow continuation enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate ALL required state at boundary
            required_fields = {"channel", "flow_data", "member_id", "authenticated"}
            current_state = {
                field: state_manager.get(field)
                for field in required_fields
            }

            # Initial validation
            validation = StateValidator.validate_before_access(
                current_state,
                {"channel", "flow_data"}  # Core requirements
            )
            if not validation.is_valid:
                raise ValueError(f"State validation failed: {validation.error_message}")

            # Get channel info (SINGLE SOURCE OF TRUTH)
            channel = state_manager.get("channel")
            if not channel or not channel.get("identifier"):
                raise ValueError("Channel identifier not found")

            # Validate flow data structure
            if not isinstance(flow_data, dict):
                raise ValueError("Invalid flow data structure")

            # Get and validate flow type
            flow_type = flow_data.get("id")
            if not flow_type or not isinstance(flow_type, str):
                raise ValueError("Invalid flow type")

            # Initialize flow with state manager
            flow_class = FlowProcessor.FLOW_MAP.get(flow_type)
            if not flow_class:
                raise ValueError(f"Unsupported flow type: {flow_type}")

            flow = flow_class(state_manager=state_manager)
            if not flow:
                raise ValueError("Failed to initialize flow")

            # Process input
            input_value = input_handler.extract_input_value()
            result = flow.process_step(input_value)

            # Handle direct response
            if isinstance(result, WhatsAppMessage):
                return result

            # Handle flow completion
            if not result:
                # Validate state update
                new_state = {"flow_data": None}
                validation = StateValidator.validate_state(new_state)
                if not validation.is_valid:
                    raise ValueError(f"Invalid state update: {validation.error_message}")

                # Clear flow data
                success, error = state_manager.update_state(new_state)
                if not success:
                    raise ValueError(f"Failed to clear flow data: {error}")

                return flow.handle_menu()

            # Handle confirmation step
            step = flow_data.get("step", 0)
            if not isinstance(step, int):
                raise ValueError("Invalid step value")

            if step >= len(flow.steps):
                if flow.current_step and flow.current_step.id == "confirm":
                    return FlowProcessor.handle_confirmation(state_manager, flow)

                # Validate state update
                new_state = {"flow_data": None}
                validation = StateValidator.validate_state(new_state)
                if not validation.is_valid:
                    raise ValueError(f"Invalid state update: {validation.error_message}")

                # Clear flow data
                success, error = state_manager.update_state(new_state)
                if not success:
                    raise ValueError(f"Failed to clear flow data: {error}")

                return flow.handle_menu()

            return WhatsAppMessage.from_core_message(result)

        except ValueError as e:
            # Get channel info for error response
            try:
                channel = state_manager.get("channel")
                channel_id = channel["identifier"] if channel else "unknown"
            except (ValueError, KeyError, TypeError) as err:
                logger.error(f"Failed to get channel for error response: {str(err)}")
                channel_id = "unknown"

            logger.error(f"Flow processing error: {str(e)} for channel {channel_id}")
            return WhatsAppMessage.create_text(
                channel_id,
                "Error: Unable to process flow. Please try again."
            )

    @staticmethod
    def handle_confirmation(state_manager: Any, flow: Flow) -> WhatsAppMessage:
        """Handle confirmation step enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate ALL required state at boundary
            required_fields = {"channel", "member_id", "flow_data", "authenticated"}
            current_state = {
                field: state_manager.get(field)
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
            channel = state_manager.get("channel")
            if not channel or not channel.get("identifier"):
                raise ValueError("Channel identifier not found")

            # Log completion
            audit.log_flow_event(
                "bot_service",
                "flow_complete",
                None,
                {"channel_id": channel["identifier"]},
                "success"
            )

            # Validate state update
            new_state = {"flow_data": None}
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                raise ValueError(f"Invalid state update: {validation.error_message}")

            # Clear flow data
            success, error = state_manager.update_state(new_state)
            if not success:
                raise ValueError(f"Failed to clear flow data: {error}")

            # Show dashboard
            dashboard = DashboardFlow(
                state_manager=state_manager,
                success_message="Operation completed successfully"
            )
            if not dashboard:
                raise ValueError("Failed to initialize dashboard")

            return dashboard.complete()

        except ValueError as e:
            # Get channel info for error response
            try:
                channel = state_manager.get("channel")
                channel_id = channel["identifier"] if channel else "unknown"
            except (ValueError, KeyError, TypeError) as err:
                logger.error(f"Failed to get channel for error response: {str(err)}")
                channel_id = "unknown"

            logger.error(f"Flow completion error: {str(e)} for channel {channel_id}")
            return WhatsAppMessage.create_text(
                channel_id,
                "Error: Unable to complete flow. Please try again."
            )
