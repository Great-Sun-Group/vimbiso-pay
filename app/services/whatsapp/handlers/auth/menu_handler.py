"""Menu and dashboard handling enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Optional

from core.messaging.types import (ChannelIdentifier, ChannelType, Message,
                                  MessageRecipient, TextContent)
from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator

from ...base_handler import BaseActionHandler
from ..member.dashboard import DashboardFlow

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class MenuHandler(BaseActionHandler):
    """Handler for menu and dashboard interactions with strict state management"""

    def __init__(self, state_manager: Any):
        """Initialize with state manager enforcing SINGLE SOURCE OF TRUTH

        Args:
            state_manager: State manager instance

        Raises:
            ValueError: If state validation fails or required data missing
        """
        if not state_manager:
            raise ValueError("State manager required")

        # Validate ALL required state at boundary
        required_fields = {"channel", "authenticated"}
        current_state = {
            field: state_manager.get(field)
            for field in required_fields
        }

        # Initial validation
        validation = StateValidator.validate_before_access(
            current_state,
            {"channel"}  # Core requirement
        )
        if not validation.is_valid:
            raise ValueError(f"State validation failed: {validation.error_message}")

        # Get channel info (SINGLE SOURCE OF TRUTH)
        channel = state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            raise ValueError("Channel identifier not found")

        # Initialize base class
        super().__init__(state_manager)

        # Initialize services
        self.credex_service = state_manager.get_or_create_credex_service()
        if not self.credex_service:
            raise ValueError("Failed to initialize credex service")

        self.auth_flow = None  # Will be set by auth handler

        # Log initialization
        logger.info(f"Initialized MenuHandler for channel {channel['identifier']}")

    def show_dashboard(self, message: Optional[str] = None) -> Message:
        """Display dashboard enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate ALL required state at boundary
            required_fields = {"channel", "member_id", "account_id", "authenticated", "jwt_token"}
            current_state = {
                field: self.state_manager.get(field)
                for field in required_fields
            }

            # Validate required fields
            validation = StateValidator.validate_before_access(
                current_state,
                required_fields  # All fields required for dashboard
            )
            if not validation.is_valid:
                raise ValueError(f"State validation failed: {validation.error_message}")

            # Get channel info (SINGLE SOURCE OF TRUTH)
            channel = self.state_manager.get("channel")
            if not channel or not channel.get("identifier"):
                raise ValueError("Channel identifier not found")

            # Initialize and validate dashboard flow
            flow = DashboardFlow(
                state_manager=self.state_manager,
                success_message=message
            )
            if not flow:
                raise ValueError("Failed to initialize dashboard flow")

            # Log dashboard display attempt
            logger.info(f"Displaying dashboard for channel {channel['identifier']}")

            # Complete flow
            return flow.complete()

        except ValueError as e:
            # Get channel info for error logging
            try:
                channel = self.state_manager.get("channel")
                channel_id = channel["identifier"] if channel else "unknown"
            except (ValueError, KeyError, TypeError) as err:
                logger.error(f"Failed to get channel for error logging: {str(err)}")
                channel_id = "unknown"

            logger.error(f"Dashboard display error: {str(e)} for channel {channel_id}")
            return self._create_error_message(str(e))

    def handle_menu(self, message: Optional[str] = None, login: bool = False) -> Message:
        """Display main menu enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate ALL required state at boundary
            required_fields = {"channel", "authenticated", "member_id"}
            current_state = {
                field: self.state_manager.get(field)
                for field in required_fields
            }

            # Validate required fields
            validation = StateValidator.validate_before_access(
                current_state,
                {"channel", "authenticated"}
            )
            if not validation.is_valid:
                raise ValueError(f"State validation failed: {validation.error_message}")

            # Get channel info (SINGLE SOURCE OF TRUTH)
            channel = self.state_manager.get("channel")
            if not channel or not channel.get("identifier"):
                raise ValueError("Channel identifier not found")

            # Validate auth flow
            if not self.auth_flow:
                raise ValueError("Auth flow not initialized")

            # Handle menu display based on state
            if login:
                logger.info(f"Showing post-login dashboard for channel {channel['identifier']}")
                return self.show_dashboard(message="Login successful" if not message else message)

            if self.state_manager.get("authenticated"):
                logger.info(f"Showing authenticated dashboard for channel {channel['identifier']}")
                return self.show_dashboard(message=message)

            # Show registration for unauthenticated users
            logger.info(f"Showing registration menu for channel {channel['identifier']}")
            return self.auth_flow.handle_registration(register=True)

        except ValueError as e:
            # Get channel info for error logging
            try:
                channel = self.state_manager.get("channel")
                channel_id = channel["identifier"] if channel else "unknown"
            except (ValueError, KeyError, TypeError) as err:
                logger.error(f"Failed to get channel for error logging: {str(err)}")
                channel_id = "unknown"

            logger.error(f"Menu display error: {str(e)} for channel {channel_id}")
            return self._create_error_message(str(e))

    def handle_hi(self) -> Message:
        """Handle initial greeting enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate ALL required state at boundary
            required_fields = {"channel", "authenticated"}
            current_state = {
                field: self.state_manager.get(field)
                for field in required_fields
            }

            # Validate required fields
            validation = StateValidator.validate_before_access(
                current_state,
                {"channel"}
            )
            if not validation.is_valid:
                raise ValueError(f"State validation failed: {validation.error_message}")

            # Get channel info (SINGLE SOURCE OF TRUTH)
            channel = self.state_manager.get("channel")
            if not channel or not channel.get("identifier"):
                raise ValueError("Channel identifier not found")

            # Validate auth flow
            if not self.auth_flow:
                raise ValueError("Auth flow not initialized")

            # Log greeting event
            audit.log_flow_event(
                "auth_handler",
                "greeting",
                None,
                {"channel_id": channel["identifier"]},
                "in_progress"
            )

            logger.info(f"Processing greeting for channel {channel['identifier']}")

            # Always attempt login to refresh state
            success, dashboard_data = self.auth_flow.attempt_login()

            if success:
                logger.info(f"Login successful for channel {channel['identifier']}")
                return self.handle_menu(login=True)

            logger.info(f"Showing registration for new user on channel {channel['identifier']}")
            return self.auth_flow.handle_registration(register=True)

        except ValueError as e:
            # Get channel info for error logging
            try:
                channel = self.state_manager.get("channel")
                channel_id = channel["identifier"] if channel else "unknown"
            except (ValueError, KeyError, TypeError) as err:
                logger.error(f"Failed to get channel for error logging: {str(err)}")
                channel_id = "unknown"

            logger.error(f"Greeting error: {str(e)} for channel {channel_id}")
            return self._create_error_message(str(e))

    def handle_refresh(self) -> Message:
        """Handle dashboard refresh enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate ALL required state at boundary
            required_fields = {"channel", "authenticated", "member_id"}
            current_state = {
                field: self.state_manager.get(field)
                for field in required_fields
            }

            # Validate required fields
            validation = StateValidator.validate_before_access(
                current_state,
                {"channel"}
            )
            if not validation.is_valid:
                raise ValueError(f"State validation failed: {validation.error_message}")

            # Get channel info (SINGLE SOURCE OF TRUTH)
            channel = self.state_manager.get("channel")
            if not channel or not channel.get("identifier"):
                raise ValueError("Channel identifier not found")

            # Log refresh event
            audit.log_flow_event(
                "auth_handler",
                "refresh",
                None,
                {"channel_id": channel["identifier"]},
                "in_progress"
            )

            logger.info(f"Refreshing dashboard for channel {channel['identifier']}")
            return self.handle_menu(message="Dashboard refreshed")

        except ValueError as e:
            # Get channel info for error logging
            try:
                channel = self.state_manager.get("channel")
                channel_id = channel["identifier"] if channel else "unknown"
            except (ValueError, KeyError, TypeError) as err:
                logger.error(f"Failed to get channel for error logging: {str(err)}")
                channel_id = "unknown"

            logger.error(f"Refresh error: {str(e)} for channel {channel_id}")
            return self._create_error_message(str(e))

    def _create_error_message(self, error: str) -> Message:
        """Create error message enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate ALL required state at boundary
            required_fields = {"channel", "member_id"}
            current_state = {
                field: self.state_manager.get(field)
                for field in required_fields
            }

            # Validate minimum required state
            validation = StateValidator.validate_before_access(
                current_state,
                {"channel"}  # Only channel required
            )
            if not validation.is_valid:
                raise ValueError(f"State validation failed: {validation.error_message}")

            # Get channel info (SINGLE SOURCE OF TRUTH)
            channel = self.state_manager.get("channel")
            if not channel or not channel.get("identifier"):
                raise ValueError("Channel identifier not found")

            # Get member ID (SINGLE SOURCE OF TRUTH)
            member_id = self.state_manager.get("member_id")

            # Log error creation
            logger.info(f"Creating error message for channel {channel['identifier']}")

            return Message(
                recipient=MessageRecipient(
                    member_id=member_id or "pending",
                    channel_id=ChannelIdentifier(
                        channel=ChannelType.WHATSAPP,
                        value=channel["identifier"]
                    )
                ),
                content=TextContent(
                    body="❌ Error: Unable to process request. Please try again."
                )
            )

        except ValueError as e:
            logger.error(f"Failed to create error message: {str(e)}")
            return Message(
                recipient=MessageRecipient(
                    member_id="unknown",
                    channel_id=ChannelIdentifier(
                        channel=ChannelType.WHATSAPP,
                        value="unknown"
                    )
                ),
                content=TextContent(
                    body="❌ Critical Error: System temporarily unavailable"
                )
            )
