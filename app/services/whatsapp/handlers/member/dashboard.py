"""Dashboard flow implementation"""
import logging
from typing import Dict, Any, List, Optional

from core.messaging.flow import Flow
from ...screens import format_account
from ...types import WhatsAppMessage

logger = logging.getLogger(__name__)


class DashboardFlow(Flow):
    """Flow for handling dashboard display"""

    def __init__(
        self,
        flow_type: str = "view",
        success_message: Optional[str] = None,
        **kwargs
    ):
        """Initialize dashboard flow"""
        self.flow_type = flow_type
        self.success_message = success_message
        self.kwargs = kwargs
        super().__init__(f"dashboard_{flow_type}", [])
        self.credex_service = None

    def process_input(self, input_data: Any) -> Optional[str]:
        """Override to skip input processing for dashboard display"""
        return self.complete()

    def _get_selected_account(
        self,
        accounts: List[Dict[str, Any]],
        mobile_number: str
    ) -> Optional[Dict[str, Any]]:
        """Get selected account from dashboard data"""
        try:
            if not accounts:
                return None

            # Try to find personal account first
            personal_account = next(
                (account for account in accounts
                 if account.get("accountType") == "PERSONAL"),
                None
            )
            if personal_account:
                return personal_account

            # Fallback to mobile number match
            return next(
                (account for account in accounts
                 if account.get("accountHandle") == mobile_number),
                None
            )

        except Exception as e:
            logger.error(f"Account selection error: {str(e)}")
            return None

    def _format_dashboard_data(
        self,
        account: Dict[str, Any],
        profile_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format dashboard data for display"""
        try:
            account_data = account
            balance_data = account_data["balanceData"]
            dashboard = profile_data.get("dashboard", {})

            # Get counts
            pending_in = len(account_data.get("pendingInData", []))
            pending_out = len(account_data.get("pendingOutData", []))

            # Format balances
            balances = "\n".join(
                f"  {bal}"
                for bal in balance_data["securedNetBalancesByDenom"]
            )

            # Get tier info
            member_tier = dashboard.get("member", {}).get("memberTier", 1)
            remaining_usd = dashboard.get("remainingAvailableUSD", 0)

            # Format tier display
            tier_limit_display = ""
            if member_tier <= 2:
                tier_type = "OPEN" if member_tier == 1 else "VERIFIED"
                tier_limit_display = (
                    f"\n*{tier_type} TIER DAILY LIMIT*\n"
                    f"  ${remaining_usd} USD"
                )

            return {
                "account_name": account_data.get("accountName", "Personal Account"),
                "handle": account_data.get("accountHandle"),
                "balances": balances,
                "net_assets": balance_data.get("netCredexAssetsInDefaultDenom"),
                "tier_limit_display": tier_limit_display,
                "is_owned": account_data.get("isOwnedAccount", False),
                "pending_in": pending_in,
                "pending_out": pending_out,
                "member_tier": member_tier
            }

        except Exception as e:
            logger.error(f"Dashboard formatting error: {str(e)}")
            return {}

    def _build_menu_options(
        self,
        is_owned: bool,
        pending_in: int,
        pending_out: int,
        member_tier: int
    ) -> Dict[str, Any]:
        """Build menu options"""
        options = [
            {
                "id": "offer_credex",
                "title": "💸 Offer Secured Credex",
            },
            {
                "id": "accept_credex",
                "title": f"✅ Accept Offers ({pending_in})",
            },
            {
                "id": "decline_credex",
                "title": f"❌ Decline Offers ({pending_in})",
            },
            {
                "id": "cancel_credex",
                "title": f"📤 Cancel Outgoing ({pending_out})",
            },
            {
                "id": "view_transactions",
                "title": "📒 Review Transactions",
            }
        ]

        if member_tier <= 2:
            options.append({
                "id": "upgrade_tier",
                "title": "⭐️ Upgrade Member Tier",
            })

        return {
            "button": "🕹️ Options",
            "sections": [{"title": "Options", "rows": options}]
        }

    def complete(self) -> Dict[str, Any]:
        """Complete flow and return formatted dashboard"""
        try:
            # Validate service
            if not self.credex_service:
                raise ValueError("Service not initialized")

            if not hasattr(self.credex_service, '_parent_service'):
                raise ValueError("Cannot access service state")

            # Get current state
            user_state = self.credex_service._parent_service.user.state
            current_state = user_state.state
            profile_data = current_state.get("profile", {})
            if not profile_data:
                raise ValueError("No profile data found")

            # Get accounts
            accounts = profile_data.get("dashboard", {}).get("accounts", [])
            if not accounts:
                raise ValueError("No accounts found")

            # Get selected account
            selected_account = self._get_selected_account(
                accounts,
                self.data.get("mobile_number")
            )
            if not selected_account:
                raise ValueError("Personal account not found")

            # Update state while preserving critical fields
            user_state.update_state({
                "current_account": selected_account,
                "profile": profile_data,
                "jwt_token": current_state.get("jwt_token")
            }, "account_select")

            # Format dashboard data
            display_data = self._format_dashboard_data(selected_account, profile_data)
            if not display_data:
                raise ValueError("Failed to format dashboard")

            # Create dashboard text
            dashboard_text = format_account({
                "account": display_data["account_name"],
                "handle": display_data["handle"],
                "securedNetBalancesByDenom": display_data["balances"],
                "netCredexAssetsInDefaultDenom": display_data["net_assets"],
                "tier_limit_display": display_data["tier_limit_display"]
            })

            if self.success_message:
                dashboard_text = f"✅ {self.success_message}\n\n{dashboard_text}"

            # Return formatted message
            return WhatsAppMessage.create_list(
                to=self.data.get("mobile_number"),
                text=dashboard_text,
                button="🕹️ Options",
                sections=[{
                    "title": "Options",
                    "rows": self._build_menu_options(
                        display_data["is_owned"],
                        display_data["pending_in"],
                        display_data["pending_out"],
                        display_data["member_tier"]
                    )["sections"][0]["rows"]
                }]
            )

        except Exception as e:
            logger.error(f"Dashboard completion error: {str(e)}")
            return WhatsAppMessage.create_text(
                self.data.get("mobile_number"),
                f"Failed to load dashboard: {str(e)}"
            )
