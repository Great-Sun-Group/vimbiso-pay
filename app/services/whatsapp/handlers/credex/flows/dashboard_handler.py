"""Integration with member dashboard functionality enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, List

from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator
from services.whatsapp.handlers.member.dashboard import DashboardFlow

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class CredexDashboardHandler:
    """Handles credex-specific dashboard integration with strict state management"""

    def __init__(self, state_manager: Any) -> None:
        """Initialize with state manager enforcing SINGLE SOURCE OF TRUTH

        Args:
            state_manager: State manager instance

        Raises:
            ValueError: If state validation fails or required data missing
        """
        if not state_manager:
            raise ValueError("State manager required")

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

        # Initialize services
        self.state_manager = state_manager
        self.credex_service = state_manager.get_credex_service()
        if not self.credex_service:
            raise ValueError("Failed to initialize credex service")

        # Log initialization
        logger.info(f"Initialized CredexDashboardHandler for channel {channel['identifier']}")

    def update(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Update dashboard enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate input parameters
            if not isinstance(response, dict):
                raise ValueError("Invalid response format")

            # Validate ALL required state at boundary
            required_fields = {"channel", "member_id", "account_id", "flow_data", "authenticated"}
            current_state = {
                field: self.state_manager.get(field)
                for field in required_fields
            }

            # Validate required fields
            validation = StateValidator.validate_before_access(
                current_state,
                {"channel", "member_id", "account_id", "flow_data"}
            )
            if not validation.is_valid:
                raise ValueError(f"State validation failed: {validation.error_message}")

            # Get channel info (SINGLE SOURCE OF TRUTH)
            channel = self.state_manager.get("channel")
            if not channel or not channel.get("identifier"):
                raise ValueError("Channel identifier not found")

            # Create and validate dashboard flow
            dashboard = DashboardFlow(
                state_manager=self.state_manager,
                success_message="Dashboard updated successfully"
            )
            if not dashboard:
                raise ValueError("Failed to initialize dashboard flow")

            # Complete dashboard flow
            result = dashboard.complete()
            if not result:
                raise ValueError("Failed to complete dashboard flow")

            # Log success
            audit.log_flow_event(
                "credex_flow",
                "dashboard_update",
                None,
                {
                    "channel_id": channel["identifier"],
                    "response": response
                },
                "success"
            )

            return result

        except ValueError as e:
            # Get channel info for error logging
            try:
                channel = self.state_manager.get("channel")
                channel_id = channel["identifier"] if channel else "unknown"
            except (ValueError, KeyError, TypeError) as err:
                logger.error(f"Failed to get channel for error logging: {str(err)}")
                channel_id = "unknown"

            logger.error(f"Dashboard update error: {str(e)} for channel {channel_id}")
            raise

    def get_pending_offers(self, direction: str = "in") -> List[Dict[str, Any]]:
        """Get pending offers enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate input parameters
            if direction not in ["in", "out"]:
                raise ValueError("Invalid direction")

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

            # Get flow data (SINGLE SOURCE OF TRUTH)
            flow_data = self.state_manager.get("flow_data")
            if not isinstance(flow_data, dict):
                logger.warning(f"Invalid flow data format for channel {channel['identifier']}")
                return []

            # Get offers based on direction
            offers = flow_data.get(f"pending_{direction}_offers", [])
            if not isinstance(offers, list):
                logger.warning(f"Invalid offers format for channel {channel['identifier']}")
                return []

            return offers

        except ValueError as e:
            # Get channel info for error logging
            try:
                channel = self.state_manager.get("channel")
                channel_id = channel["identifier"] if channel else "unknown"
            except (ValueError, KeyError, TypeError) as err:
                logger.error(f"Failed to get channel for error logging: {str(err)}")
                channel_id = "unknown"

            logger.error(f"Get pending offers error: {str(e)} for channel {channel_id}")
            return []

    def get_account_info(self) -> Dict[str, Any]:
        """Get account info enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate ALL required state at boundary
            required_fields = {"channel", "member_id", "account_id", "flow_data", "authenticated"}
            current_state = {
                field: self.state_manager.get(field)
                for field in required_fields
            }

            # Validate required fields
            validation = StateValidator.validate_before_access(
                current_state,
                {"channel", "member_id", "account_id", "flow_data"}
            )
            if not validation.is_valid:
                raise ValueError(f"State validation failed: {validation.error_message}")

            # Get channel info (SINGLE SOURCE OF TRUTH)
            channel = self.state_manager.get("channel")
            if not channel or not channel.get("identifier"):
                raise ValueError("Channel identifier not found")

            # Get flow data (SINGLE SOURCE OF TRUTH)
            flow_data = self.state_manager.get("flow_data")
            if not isinstance(flow_data, dict):
                raise ValueError("Invalid flow data format")

            # Get and validate account info
            account_info = flow_data.get("account_info")
            if not isinstance(account_info, dict):
                raise ValueError("Invalid account info format")

            # Log access
            logger.info(f"Retrieved account info for channel {channel['identifier']}")

            return account_info

        except ValueError as e:
            # Get channel info for error logging
            try:
                channel = self.state_manager.get("channel")
                channel_id = channel["identifier"] if channel else "unknown"
            except (ValueError, KeyError, TypeError) as err:
                logger.error(f"Failed to get channel for error logging: {str(err)}")
                channel_id = "unknown"

            logger.error(f"Get account info error: {str(e)} for channel {channel_id}")
            raise
