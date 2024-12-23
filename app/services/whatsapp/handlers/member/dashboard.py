"""Dashboard flow implementation"""
import logging
from typing import Any, Dict, List, Optional

from core.messaging.flow import Flow
from ...state_manager import StateManager
from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator

from ...screens import format_account
from ...types import WhatsAppMessage

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


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
        # Log flow event
        audit.log_flow_event(
            self.id,
            "process_input",
            None,
            self.data,
            "in_progress"
        )
        return self.complete()

    def _get_selected_account(
        self,
        accounts: List[Dict[str, Any]],
        member_id: str,
        channel_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get selected account from dashboard data using member-centric approach"""
        try:
            if not accounts:
                audit.log_flow_event(
                    self.id,
                    "account_selection",
                    None,
                    {"accounts": accounts},
                    "failure",
                    "No accounts available"
                )
                return None

            # Try to find personal account first
            personal_account = next(
                (account for account in accounts
                 if account.get("accountType") == "PERSONAL" and
                 account.get("memberID") == member_id),
                None
            )
            if personal_account:
                audit.log_flow_event(
                    self.id,
                    "account_selection",
                    None,
                    {
                        "selected": personal_account,
                        "member_id": member_id,
                        "channel": {
                            "type": "whatsapp",
                            "identifier": channel_id
                        }
                    },
                    "success"
                )
                return personal_account

            # Fallback to channel identifier match
            channel_account = next(
                (account for account in accounts
                 if account.get("accountHandle") == channel_id),
                None
            )

            audit.log_flow_event(
                self.id,
                "account_selection",
                None,
                {
                    "selected": channel_account,
                    "member_id": member_id,
                    "channel": {
                        "type": "whatsapp",
                        "identifier": channel_id
                    }
                },
                "success" if channel_account else "failure"
            )
            return channel_account

        except Exception as e:
            logger.error(f"Account selection error: {str(e)}")
            audit.log_flow_event(
                self.id,
                "account_selection",
                None,
                {"accounts": accounts},
                "failure",
                str(e)
            )
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

            formatted_data = {
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

            audit.log_flow_event(
                self.id,
                "format_dashboard",
                None,
                formatted_data,
                "success"
            )
            return formatted_data

        except Exception as e:
            logger.error(f"Dashboard formatting error: {str(e)}")
            audit.log_flow_event(
                self.id,
                "format_dashboard",
                None,
                {"account": account},
                "failure",
                str(e)
            )
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
                "id": "offer",
                "title": "💸 Offer Secured Credex",
            },
            {
                "id": "accept",
                "title": f"✅ Accept Offers ({pending_in})",
            },
            {
                "id": "decline",
                "title": f"❌ Decline Offers ({pending_in})",
            },
            {
                "id": "cancel",
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

        menu = {
            "button": "🕹️ Options",
            "sections": [{"title": "Options", "rows": options}]
        }

        audit.log_flow_event(
            self.id,
            "build_menu",
            None,
            menu,
            "success"
        )
        return menu

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
            current_state = user_state.state or {}

            # Ensure validation context is present before validation
            current_state = StateValidator.ensure_validation_context(current_state)

            # Validate current state
            validation = StateValidator.validate_state(current_state)
            if not validation.is_valid:
                audit.log_flow_event(
                    self.id,
                    "state_validation_error",
                    None,
                    current_state,
                    "failure",
                    validation.error_message
                )
                # Attempt recovery from last valid state
                last_valid = audit.get_last_valid_state(self.id)
                if last_valid:
                    current_state = last_valid
                else:
                    raise ValueError(f"Invalid state: {validation.error_message}")

            profile_data = current_state.get("profile", {})
            if not profile_data:
                raise ValueError("No profile data found")

            # Get accounts
            accounts = profile_data.get("dashboard", {}).get("accounts", [])
            if not accounts:
                raise ValueError("No accounts found")

            # Get member ID and channel info from top level state - SINGLE SOURCE OF TRUTH
            member_id = current_state.get("member_id")
            if not member_id:
                raise ValueError("Missing member ID in state")

            channel_id = StateManager.get_channel_identifier(current_state)
            if not channel_id:
                raise ValueError("Missing channel identifier")

            # Get selected account
            selected_account = self._get_selected_account(
                accounts,
                member_id,
                channel_id
            )
            if not selected_account:
                raise ValueError("Personal account not found")

            # Prepare new state with member-centric structure
            new_state = {
                # Core identity at top level - SINGLE SOURCE OF TRUTH
                "member_id": member_id,  # Primary identifier

                # Channel info at top level - SINGLE SOURCE OF TRUTH
                "channel": StateManager.create_channel_data(
                    identifier=channel_id,
                    channel_type="whatsapp"
                ),

                # Authentication and account
                "authenticated": current_state.get("authenticated", False),
                "jwt_token": current_state.get("jwt_token"),
                "account_id": current_state.get("account_id"),
                "current_account": selected_account,

                # Profile and flow data
                "profile": profile_data,
                "flow_data": current_state.get("flow_data") or {
                    "id": "user_state",
                    "step": 0,
                    "data": {
                        "account_id": current_state.get("account_id"),
                        "flow_type": current_state.get("flow_type", "dashboard"),
                        "_validation_context": current_state.get("_validation_context", {}),
                        "_validation_state": current_state.get("_validation_state", {})
                    },
                    "_previous_data": {}
                },

                # Validation context
                "_validation_context": current_state.get("_validation_context", {}),
                "_validation_state": current_state.get("_validation_state", {}),
                "_last_updated": audit.get_current_timestamp()
            }

            # Log state preparation
            logger.debug(f"[Dashboard {self.id}] Preparing new state:")
            logger.debug(f"[Dashboard {self.id}] - Current state keys: {list(current_state.keys())}")
            logger.debug(f"[Dashboard {self.id}] - New state keys: {list(new_state.keys())}")
            logger.debug(f"[Dashboard {self.id}] - Flow data: {new_state['flow_data']}")

            # Validate new state
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                audit.log_flow_event(
                    self.id,
                    "state_validation_error",
                    None,
                    new_state,
                    "failure",
                    validation.error_message
                )
                return WhatsAppMessage.create_text(
                    channel_id,  # Use channel identifier from top level state
                    f"Failed to update state: {validation.error_message}"
                )

            # Log state transition
            audit.log_state_transition(
                self.id,
                current_state,
                new_state,
                "success"
            )

            # Update state
            user_state.update_state(new_state, "account_select")

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

            # Return formatted message using channel identifier from top level state
            return WhatsAppMessage.create_list(
                to=channel_id,  # Use channel identifier from top level state
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
            audit.log_flow_event(
                self.id,
                "completion_error",
                None,
                self.data,
                "failure",
                str(e)
            )

            # Get channel identifier from top level state
            current_state = self.credex_service._parent_service.user.state.state or {}
            channel_id = StateManager.get_channel_identifier(current_state)
            if not channel_id:
                raise ValueError("Missing channel identifier")

            return WhatsAppMessage.create_text(
                channel_id,  # Use channel identifier from top level state
                f"Failed to load dashboard: {str(e)}"
            )
