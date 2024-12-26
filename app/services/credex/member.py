import logging
from typing import Any, Dict, Optional, Tuple

from .base import BaseCredExService
from .exceptions import ValidationError

logger = logging.getLogger(__name__)


class CredExMemberService(BaseCredExService):
    """Service for CredEx member operations"""

    def get_dashboard(self, phone: str) -> Tuple[bool, Dict[str, Any]]:
        """Get dashboard information"""
        if not phone:
            raise ValidationError("Phone number is required")

        try:
            response = self._make_request(
                'member', 'get_dashboard',
                payload={"phone": phone}
            )
            data = response.json()

            # Extract dashboard data
            if dashboard := data.get("data", {}).get("dashboard"):
                # Update state if available
                self._update_state({"profile": {"dashboard": dashboard}})
                return True, data
            return False, {"message": "No dashboard data received"}

        except Exception as e:
            logger.error(f"Dashboard fetch failed: {str(e)}")
            return False, {"message": str(e)}

    def validate_handle(self, handle: str) -> Tuple[bool, Dict[str, Any]]:
        """Validate CredEx handle"""
        if not handle:
            raise ValidationError("Handle is required")

        try:
            response = self._make_request(
                'member', 'validate_handle',
                payload={"accountHandle": handle.lower()}
            )
            data = response.json()

            # Extract account details
            if details := data.get("data", {}).get("action", {}).get("details"):
                if account_id := details.get("accountID"):
                    return True, {
                        "data": {
                            "accountID": account_id,
                            "accountName": details.get("accountName", ""),
                            "accountHandle": handle
                        }
                    }
            return False, {"message": "Account not found"}

        except Exception as e:
            logger.error(f"Handle validation failed: {str(e)}")
            return False, {"message": str(e)}

    def refresh_member_info(
        self, phone: str, reset: bool = True, silent: bool = True, init: bool = False
    ) -> Optional[str]:
        """Refresh member information"""
        if not phone:
            raise ValidationError("Phone number is required")

        try:
            # Re-authenticate to get fresh data
            response = self._make_request(
                'auth', 'login',
                payload={"phone": phone}
            )
            data = response.json()

            if token := (data.get("data", {})
                         .get("action", {})
                         .get("details", {})
                         .get("token")):
                self._update_token(token)
                return None
            return "Failed to refresh member info"

        except Exception as e:
            logger.error(f"Member info refresh failed: {str(e)}")
            return str(e)

    def get_member_accounts(self, member_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Get member accounts"""
        if not member_id:
            raise ValidationError("Member ID is required")

        try:
            response = self._make_request(
                'member', 'get_accounts',
                payload={"memberID": member_id}
            )
            data = response.json()

            if accounts := data.get("data", {}).get("accounts"):
                return True, {"data": {"accounts": accounts}}
            return False, {"message": "No accounts found"}

        except Exception as e:
            logger.error(f"Failed to get member accounts: {str(e)}")
            return False, {"message": str(e)}

    def _update_state(self, updates: Dict[str, Any]) -> None:
        """Update state if parent service available"""
        if hasattr(self, '_parent_service') and hasattr(self._parent_service, 'user'):
            self._parent_service.user.state.update_state(updates)
