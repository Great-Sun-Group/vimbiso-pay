"""Handles credex-specific dashboard integration with strict state management"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.utils.exceptions import StateException
from core.utils.flow_audit import FlowAuditLogger
from core.messaging.types import Message

from ...member.dashboard import handle_dashboard_display as DashboardFlow

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


def update_dashboard(state_manager: Any, update_data: Dict[str, Any]) -> Message:
    """Update dashboard with new data enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get channel (StateManager validates)

        # Update dashboard
        return DashboardFlow(
            state_manager=state_manager,
            success_message="Dashboard updated successfully"
        )

    except StateException as e:
        logger.error(f"Dashboard update failed: {str(e)}")
        raise


def validate_dashboard_data(state_manager: Any) -> Tuple[bool, Optional[str]]:
    """Validate dashboard data enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get required data (StateManager validates)
        state_manager.get("channel")
        state_manager.get("member_id")
        state_manager.get("account_id")
        state_manager.get("authenticated")
        state_manager.get("jwt_token")
        state_manager.get("flow_data")

        return True, None

    except StateException as e:
        logger.error(f"Dashboard validation failed: {str(e)}")
        return False, str(e)


def process_dashboard_update(state_manager: Any, update_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Process dashboard update enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get required data (StateManager validates)
        state_manager.get("channel")
        state_manager.get("member_id")
        state_manager.get("account_id")
        state_manager.get("authenticated")
        state_manager.get("jwt_token")
        state_manager.get("flow_data")

        # Process update
        return True, None

    except StateException as e:
        logger.error(f"Dashboard update processing failed: {str(e)}")
        return False, str(e)
