"""Handles credex-specific dashboard integration with strict state management"""
import logging
from typing import Any, Dict

from core.messaging.types import Message
from core.utils.flow_audit import FlowAuditLogger

from ...member.dashboard import handle_dashboard_display as DashboardFlow

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


def update_dashboard(state_manager: Any, update_data: Dict[str, Any]) -> Message:
    """Update dashboard with new data enforcing SINGLE SOURCE OF TRUTH

    Args:
        state_manager: State manager instance
        update_data: Data to update dashboard with

    Returns:
        Updated dashboard message

    Raises:
        StateException: If update fails
    """
    # Let StateManager validate state
    state_manager.get("channel")  # Validates channel exists

    # Update dashboard (raises StateException if fails)
    return DashboardFlow(
        state_manager=state_manager,
        success_message="Dashboard updated successfully"
    )


def validate_dashboard_state(state_manager: Any) -> None:
    """Validate dashboard state enforcing SINGLE SOURCE OF TRUTH

    Args:
        state_manager: State manager instance

    Raises:
        StateException: If validation fails
    """
    # Let StateManager validate required state through update
    state_manager.update_state({
        "dashboard": {
            "member_id": state_manager.get("member_id"),  # Validates member_id exists
            "account_id": state_manager.get("account_id"),  # Validates account_id exists
            "authenticated": state_manager.get("authenticated"),  # Validates authenticated exists
            "jwt_token": state_manager.get("jwt_token"),  # Validates jwt_token exists
            "flow_data": state_manager.get("flow_data")  # Validates flow_data exists
        }
    })


def process_dashboard_update(state_manager: Any, update_data: Dict[str, Any]) -> None:
    """Process dashboard update enforcing SINGLE SOURCE OF TRUTH

    Args:
        state_manager: State manager instance
        update_data: Data to update dashboard with

    Raises:
        StateException: If update fails
    """
    # Validate state (raises StateException if invalid)
    validate_dashboard_state(state_manager)

    # Let StateManager validate update data through state update
    state_manager.update_state({
        "dashboard": {
            "update_data": update_data
        }
    })
