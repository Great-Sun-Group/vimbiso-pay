"""Authentication components

This module provides components for handling authentication flows:
- LoginHandler: Handles login attempts
- LoginCompleteHandler: Handles successful login
"""

from typing import Any, Dict

from core.utils.exceptions import ComponentException, SystemException
from services.credex.auth import login
from .base import Component


class LoginHandler(Component):
    """Handles login attempts via CredEx API"""

    def __init__(self):
        super().__init__("login")

    def validate(self, value: Any) -> Dict:
        """Validate login attempt"""
        # No validation needed - login is triggered by "hi"
        return {"valid": True}

    def to_verified_data(self, value: Any) -> Dict:
        """Attempt login via CredEx API"""
        # Get state manager from context
        if not hasattr(self, "state_manager"):
            raise ComponentException(
                message="State manager required",
                component=self.type,
                field="state_manager",
                value="None"
            )

        # Attempt login
        success, response = login(self.state_manager)

        # Check response type
        if not success:
            if isinstance(response, dict) and response.get("error", {}).get("type") == "system":
                # System error - propagate
                error = response["error"]
                raise SystemException(
                    message=error["message"],
                    code=error["details"]["code"],
                    service=error["details"]["service"],
                    action=error["details"]["action"]
                )
            else:
                # Auth failure - return false with response
                return {
                    "success": False,
                    "response": response
                }

        # Login successful
        return {
            "success": True,
            "response": response
        }


class LoginCompleteHandler(Component):
    """Handles successful login completion"""

    def __init__(self):
        super().__init__("login_complete")

    def validate(self, value: Any) -> Dict:
        """Validate login response"""
        if not isinstance(value, dict):
            raise ComponentException(
                message="Invalid login response",
                component=self.type,
                field="response",
                value=str(value)
            )

        # Validate required fields
        required = {"memberID", "token", "member", "accounts"}
        missing = required - set(value.keys())
        if missing:
            raise ComponentException(
                message=f"Missing required fields: {missing}",
                component=self.type,
                field="response",
                value=str(value)
            )

        return {"valid": True}

    def to_verified_data(self, value: Any) -> Dict:
        """Convert login response to verified data"""
        return {
            "member_id": value["memberID"],
            "jwt_token": value["token"],
            "authenticated": True,
            "member_data": value["member"],
            "accounts": value["accounts"],
            "active_account_id": value["accounts"][0]["accountID"] if value["accounts"] else None
        }


class DashboardDisplay(Component):
    """Displays dashboard with menu options"""

    def __init__(self):
        super().__init__("dashboard")

    def validate(self, value: Any) -> Dict:
        """Validate dashboard data"""
        if not isinstance(value, dict):
            raise ComponentException(
                message="Invalid dashboard data",
                component=self.type,
                field="data",
                value=str(value)
            )

        # Validate required fields
        required = {"member_id"}
        missing = required - set(value.keys())
        if missing:
            raise ComponentException(
                message=f"Missing required fields: {missing}",
                component=self.type,
                field="data",
                value=str(value)
            )

        return {"valid": True}

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified dashboard data"""
        # Get state manager from context
        if not hasattr(self, "state_manager"):
            raise ComponentException(
                message="State manager required",
                component=self.type,
                field="state_manager",
                value="None"
            )

        # Get required state data
        accounts = self.state_manager.get("accounts")
        active_id = self.state_manager.get("active_account_id")
        member_data = self.state_manager.get("member_data")

        # Get active account
        active_account = next(
            account for account in accounts
            if account["accountID"] == active_id
        )

        # Count pending offers
        pending_count = len(active_account.get("pendingInData", []))
        outgoing_count = len(active_account.get("pendingOutData", []))

        # Format tier limit if applicable
        tier_display = ""
        if member_data["memberTier"] < 3 and member_data.get("remainingAvailableUSD") is not None:
            tier_name = "OPEN" if member_data["memberTier"] == 1 else "VERIFIED"
            tier_display = f"DAILY {tier_name} TIER LIMIT: {member_data['remainingAvailableUSD']} USD"

        return {
            "account": active_account["accountName"],
            "handle": active_account["accountHandle"],
            "balances": active_account["balanceData"]["securedNetBalancesByDenom"],
            "net_assets": active_account["balanceData"]["netCredexAssetsInDefaultDenom"],
            "tier_limit": tier_display,
            "pending_count": pending_count,
            "outgoing_count": outgoing_count
        }
