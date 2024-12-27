"""Handles credex-specific dashboard integration with strict state management"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator
from core.messaging.types import Message

from ...member.dashboard import handle_dashboard_display as DashboardFlow

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()

REQUIRED_FIELDS = {"channel", "member_id", "account_id", "authenticated", "jwt_token"}


def update_dashboard(state_manager: Any, update_data: Dict[str, Any]) -> Message:
    """Update dashboard with new data enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {field: state_manager.get(field) for field in REQUIRED_FIELDS},
            REQUIRED_FIELDS
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # Get channel info (SINGLE SOURCE OF TRUTH)
        channel = state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            raise ValueError("Invalid channel data")

        # Update dashboard
        return DashboardFlow(
            state_manager=state_manager,
            success_message="Dashboard updated successfully"
        )

    except ValueError as e:
        logger.error(f"Dashboard update failed: {str(e)}")
        try:
            channel = state_manager.get("channel")
            channel_id = channel["identifier"] if channel else "unknown"
        except Exception:
            channel_id = "unknown"
        return Message.create_error(channel_id, str(e))


def validate_dashboard_data(state_manager: Any) -> Tuple[bool, Optional[str]]:
    """Validate dashboard data enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {field: state_manager.get(field) for field in REQUIRED_FIELDS},
            REQUIRED_FIELDS
        )
        if not validation.is_valid:
            return False, validation.error_message

        # Get channel info (SINGLE SOURCE OF TRUTH)
        channel = state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            return False, "Invalid channel data"

        # Get flow data (SINGLE SOURCE OF TRUTH)
        flow_data = state_manager.get("flow_data")
        if not isinstance(flow_data, dict):
            return False, "Invalid flow data"

        return True, None

    except Exception as e:
        logger.error(f"Dashboard validation failed: {str(e)}")
        return False, str(e)


def process_dashboard_update(state_manager: Any, update_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Process dashboard update enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {field: state_manager.get(field) for field in REQUIRED_FIELDS},
            REQUIRED_FIELDS
        )
        if not validation.is_valid:
            return False, validation.error_message

        # Get channel info (SINGLE SOURCE OF TRUTH)
        channel = state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            return False, "Invalid channel data"

        # Get flow data (SINGLE SOURCE OF TRUTH)
        flow_data = state_manager.get("flow_data")
        if not isinstance(flow_data, dict):
            return False, "Invalid flow data"

        # Process update
        return True, None

    except Exception as e:
        logger.error(f"Dashboard update processing failed: {str(e)}")
        return False, str(e)
