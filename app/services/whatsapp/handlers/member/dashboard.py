"""Dashboard flow implementation"""
import logging
from typing import Dict, Any, List, Optional

from core.messaging.flow import Flow
from ...screens import ACCOUNT_HOME, BALANCE

logger = logging.getLogger(__name__)


class DashboardFlow(Flow):
    """Flow for handling dashboard display"""

    def __init__(self, flow_type: str = "view", success_message: Optional[str] = None, **kwargs):
        """Initialize flow

        Args:
            flow_type: Type of flow ('view', 'refresh', 'login')
            success_message: Optional success message to show at top of dashboard
            **kwargs: Flow-specific arguments
        """
        self.flow_type = flow_type
        self.success_message = success_message
        self.kwargs = kwargs
        super().__init__(f"dashboard_{flow_type}", [])
        self.credex_service = None

    def _get_selected_account(self, accounts: List[Dict[str, Any]], mobile_number: str) -> Optional[Dict[str, Any]]:
        """Get selected account from dashboard data"""
        try:
            if not accounts:
                return None

            # Find personal account by name first
            for account in accounts:
                if (account.get("success") and
                        account["data"].get("accountType") == "PERSONAL"):
                    return account

            # Fallback to mobile number match if no Personal account found
            for account in accounts:
                if (account.get("success") and
                        account["data"].get("accountHandle") == mobile_number):
                    return account

            return None

        except Exception as e:
            logger.error(f"Account selection failed: {str(e)}")
            return None

    def _format_dashboard_display(self, account: Dict[str, Any], profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format dashboard data for display"""
        try:
            # Get counts
            pending_in = len(account["data"]["pendingInData"].get("data", []))
            pending_out = len(account["data"]["pendingOutData"].get("data", []))

            # Format balances
            balances = ""
            balance_data = account["data"]["balanceData"]["data"]
            for bal in balance_data["securedNetBalancesByDenom"]:
                balances += f"  {bal}\n"

            # Get tier info from dashboard data
            dashboard = profile_data.get("dashboard", {})
            member_tier = dashboard.get("memberTier", {}).get("low", 1)
            remaining_usd = dashboard.get("remainingAvailableUSD", {}).get("low", 0)

            # Format tier display
            tier_limit_display = ""
            if member_tier <= 2:
                tier_type = "OPEN" if member_tier == 1 else "VERIFIED"
                tier_limit_display = f"\n*{tier_type} TIER DAILY LIMIT*\n  ${remaining_usd} USD"

            return {
                "account_name": account["data"].get("accountName", "Personal Account"),
                "handle": account["data"]["accountHandle"],
                "balances": balances.rstrip(),
                "net_assets": balance_data["netCredexAssetsInDefaultDenom"],
                "tier_limit_display": tier_limit_display,
                "is_owned": account["data"].get("isOwnedAccount", False),
                "pending_in": pending_in,
                "pending_out": pending_out,
                "member_tier": member_tier
            }

        except Exception as e:
            logger.error(f"Dashboard formatting failed: {str(e)}")
            return {}

    def _build_menu_actions(
        self,
        is_owned_account: bool,
        pending_in: int,
        pending_out: int,
        member_tier: int
    ) -> Dict[str, Any]:
        """Build menu options"""
        base_options = [
            {
                "id": "offer_credex",
                "title": "💸 Offer Secured Credex",
            },
            {
                "id": "accept_credex",  # Updated from handle_action_accept_offers
                "title": f"✅ Accept Offers ({pending_in})",
            },
            {
                "id": "decline_credex",  # Updated from handle_action_decline_offers
                "title": f"❌ Decline Offers ({pending_in})",
            },
            {
                "id": "cancel_credex",
                "title": f"📤 Cancel Outgoing ({pending_out})",
            },
            {
                "id": "view_transactions",  # Updated from handle_action_transactions
                "title": "📒 Review Transactions",
            },
        ]

        if member_tier <= 2:
            base_options.append({
                "id": "upgrade_tier",
                "title": "⭐️ Upgrade Member Tier",
            })

        return {
            "button": "🕹️ Options",
            "sections": [{"title": "Options", "rows": base_options}],
        }

    def complete(self) -> Dict[str, Any]:
        """Complete the flow and return formatted dashboard"""
        try:
            if not self.credex_service:
                raise ValueError("Service not initialized")

            # Get current state
            if not hasattr(self.credex_service, '_parent_service') or not hasattr(self.credex_service._parent_service, 'user'):
                raise ValueError("Cannot access user state")

            current_state = self.credex_service._parent_service.user.state.state
            profile_data = current_state.get("profile", {})
            if not profile_data:
                raise ValueError("No profile data in state")

            # Log profile data structure for debugging
            logger.info(f"Profile data structure: {profile_data}")

            # Get accounts from dashboard - accounts are in profile.dashboard.accounts
            accounts = profile_data.get("dashboard", {}).get("accounts", [])
            if not accounts:
                logger.error("No accounts found in profile data structure")
                raise ValueError("No accounts found")

            # Log accounts structure
            logger.info(f"Found accounts: {accounts}")

            # Get selected account
            selected_account = self._get_selected_account(accounts, self.data.get("mobile_number"))
            if not selected_account:
                raise ValueError("Personal account not found")

            # Store selected account
            self.credex_service._parent_service.user.state.update_state({
                "current_account": selected_account
            }, "account_select")

            # Format dashboard for display
            display_data = self._format_dashboard_display(selected_account, profile_data)
            if not display_data:
                raise ValueError("Failed to format dashboard")

            # Add success message if present
            dashboard_text = ACCOUNT_HOME.format(
                account=display_data["account_name"],
                handle=display_data["handle"],
                balance=BALANCE.format(
                    securedNetBalancesByDenom=display_data["balances"],
                    netCredexAssetsInDefaultDenom=display_data["net_assets"],
                    tier_limit_display=display_data["tier_limit_display"]
                )
            )
            if self.success_message:
                dashboard_text = f"✅ {self.success_message}\n\n{dashboard_text}"

            # Build WhatsApp response
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self.data.get("mobile_number"),
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "body": {
                        "text": dashboard_text
                    },
                    "action": self._build_menu_actions(
                        display_data["is_owned"],
                        display_data["pending_in"],
                        display_data["pending_out"],
                        display_data["member_tier"]
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Dashboard flow completion failed: {str(e)}")
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self.data.get("mobile_number"),
                "type": "text",
                "text": {"body": f"Failed to load dashboard: {str(e)}"}
            }
