"""Integration with member dashboard functionality"""
import logging
from typing import Any, Dict, Optional

from core.utils import audit
from ...handlers.member.dashboard import DashboardFlow
from services.whatsapp.state_manager import StateManager

logger = logging.getLogger(__name__)


class CredexDashboardHandler:
    """Handles credex-specific dashboard integration"""

    def __init__(self, state_manager: StateManager) -> None:
        """Initialize with state manager"""
        if not state_manager:
            raise ValueError("State manager required")
        self._state_manager = state_manager

    def update_dashboard(self, response: Dict[str, Any], flow_id: Optional[str] = None) -> None:
        """Update dashboard using member dashboard flow"""
        try:
            # Get current state
            current_state = self._state_manager.get_state()

            # Validate state has required fields
            if not current_state.get("member_id"):
                raise ValueError("Missing member ID in state")

            # Create dashboard flow with current state
            dashboard_flow = DashboardFlow(
                state=current_state,
                success_message="CredEx operation completed successfully"
            )

            # Set credex service from state manager
            dashboard_flow.credex_service = self._state_manager.credex_service

            # Complete dashboard flow to update state
            result = dashboard_flow.complete()

            # Log dashboard update
            if flow_id:
                audit.log_flow_event(
                    flow_id,
                    "dashboard_update",
                    None,
                    {
                        "member_id": current_state.get("member_id"),
                        "channel": current_state.get("channel"),
                        "success": True
                    },
                    "success"
                )

            return result

        except Exception as e:
            logger.error(f"Dashboard update error: {str(e)}")
            if flow_id:
                audit.log_flow_event(
                    flow_id,
                    "dashboard_update_error",
                    None,
                    {"error": str(e)},
                    "failure"
                )
            raise

    def get_pending_offers(self, direction: str = "in") -> list:
        """Get pending offers using dashboard flow"""
        try:
            # Get current state
            current_state = self._state_manager.get_state()

            # Create dashboard flow
            dashboard_flow = DashboardFlow(state=current_state)
            dashboard_flow.credex_service = self._state_manager.credex_service

            # Get account info from dashboard
            account = dashboard_flow._get_selected_account(
                dashboard_flow.credex_service._parent_service.user.state.state.get("profile", {}).get("dashboard", {}).get("accounts", []),
                current_state.get("member_id"),
                StateManager.get_channel_identifier(current_state)
            )

            if not account:
                return []

            # Return appropriate offers list
            if direction == "in":
                return account.get("pendingInData", [])
            return account.get("pendingOutData", [])

        except Exception as e:
            logger.error(f"Error getting pending offers: {str(e)}")
            return []

    def get_account_info(self) -> Dict[str, Any]:
        """Get account info using dashboard flow"""
        try:
            # Get current state
            current_state = self._state_manager.get_state()

            # Create dashboard flow
            dashboard_flow = DashboardFlow(state=current_state)
            dashboard_flow.credex_service = self._state_manager.credex_service

            # Get account info
            account = dashboard_flow._get_selected_account(
                dashboard_flow.credex_service._parent_service.user.state.state.get("profile", {}).get("dashboard", {}).get("accounts", []),
                current_state.get("member_id"),
                StateManager.get_channel_identifier(current_state)
            )

            if not account:
                return {}

            return {
                "account_id": account.get("accountID"),
                "account_name": account.get("accountName"),
                "handle": account.get("accountHandle"),
                "type": account.get("accountType")
            }

        except Exception as e:
            logger.error(f"Error getting account info: {str(e)}")
            return {}
