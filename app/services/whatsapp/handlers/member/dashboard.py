"""Dashboard flow implementation"""
import logging
from typing import Any, Dict, List, Optional

from core.messaging.flow import Flow
from core.messaging.types import (ChannelIdentifier, ChannelType,
                                  InteractiveContent, InteractiveType, Message,
                                  MessageRecipient, TextContent)
from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator

from ...screens import format_account

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class DashboardFlow(Flow):
    """Flow for handling dashboard display"""

    def __init__(self, success_message: Optional[str] = None):
        """Initialize dashboard flow"""
        self.success_message = success_message
        super().__init__("dashboard", [])
        self.credex_service = None

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
            balance_data = account_data.get("balanceData", {})
            dashboard = profile_data.get("dashboard", {})

            # Get counts
            pending_in = len(account_data.get("pendingInData", []))
            pending_out = len(account_data.get("pendingOutData", []))

            # Get secured balances array (pre-formatted strings from server)
            secured_balances = balance_data.get("securedNetBalancesByDenom", [])
            if not isinstance(secured_balances, list):
                secured_balances = []
                logger.error("Invalid securedNetBalancesByDenom format")

            # Add spacing to pre-formatted balance strings
            balances = "\n".join(f"  {bal}" for bal in secured_balances) if secured_balances else ""

            # Get tier info and remaining USD (only present for tier < 3)
            member_tier = dashboard.get("member", {}).get("memberTier", 1)
            remaining_usd = dashboard.get("remainingAvailableUSD")

            # Only show tier limit if remainingAvailableUSD exists in response
            tier_limit_display = ""
            if remaining_usd is not None and member_tier <= 2:
                tier_type = "OPEN" if member_tier == 1 else "VERIFIED"
                tier_limit_display = (
                    f"\n*{tier_type} TIER DAILY LIMIT*\n"
                    f"  ${remaining_usd} USD"
                )

            # Get net assets (pre-formatted string from server)
            net_assets = balance_data.get("netCredexAssetsInDefaultDenom", "")

            formatted_data = {
                "account_name": account_data.get("accountName", "Personal Account"),
                "handle": account_data.get("accountHandle", "Not Available"),
                "balances": balances,
                "net_assets": net_assets,
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

    def _create_error_message(self, error: str) -> Message:
        """Create error message with current state info"""
        current_state = self.credex_service._parent_service.user.state.state or {}
        channel_id = current_state.get("channel", {}).get("identifier", "unknown")
        member_id = current_state.get("member_id", "pending")

        return Message(
            recipient=MessageRecipient(
                member_id=member_id,
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel_id
                )
            ),
            content=TextContent(
                body=f"Failed to load dashboard: {error}"
            )
        )

    def _build_menu_options(
        self,
        is_owned: bool,
        pending_in: int,
        pending_out: int,
        member_tier: int
    ) -> Dict[str, Any]:
        """Build menu options"""
        # Build menu rows with proper WhatsApp format
        rows = [
            {
                "id": "offer",
                "title": "💸 Offer Secured Credex",
                "description": "Create secured credex offer"
            },
            {
                "id": "accept",
                "title": f"✅ Accept Offers ({pending_in})",
                "description": "Accept incoming offers"
            },
            {
                "id": "decline",
                "title": f"❌ Decline Offers ({pending_in})",
                "description": "Decline incoming offers"
            },
            {
                "id": "cancel",
                "title": f"📤 Cancel Outgoing Offers ({pending_out})",
                "description": "Cancel your outgoing offers"
            },
            {
                "id": "view",
                "title": "📒 View Transactions",
                "description": "View transaction history"
            }
        ]

        # Add upgrade option for lower tiers
        if member_tier <= 2:
            rows.append({
                "id": "upgrade",
                "title": "⭐️ Upgrade Member Tier",
                "description": "Increase transaction limits"
            })

        # Create menu with WhatsApp list format
        menu = {
            "button": "Options",
            "sections": [
                {
                    "title": "Account Options",
                    "rows": rows
                }
            ]
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

            channel_id = current_state.get("channel", {}).get("identifier")
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
                "channel": {
                    "type": "whatsapp",
                    "identifier": channel_id,
                },

                # Authentication and account
                "authenticated": current_state.get("authenticated", False),
                "jwt_token": current_state.get("jwt_token"),
                "account_id": current_state.get("account_id"),
                "current_account": selected_account,

                # Profile and flow data
                "profile": profile_data,
                "flow_data": {
                    "type": "dashboard",
                    "account_id": current_state.get("account_id")
                },
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
                return self._create_error_message(f"Failed to update state: {validation.error_message}")

            # Log state transition
            audit.log_state_transition(
                self.id,
                current_state,
                new_state,
                "success"
            )

            # Update state
            user_state.update_state(new_state)

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

            # Return formatted message using member ID and channel identifier
            menu_options = self._build_menu_options(
                display_data["is_owned"],
                display_data["pending_in"],
                display_data["pending_out"],
                display_data["member_tier"]
            )

            return Message(
                recipient=MessageRecipient(
                    member_id=member_id,
                    channel_id=ChannelIdentifier(
                        channel=ChannelType.WHATSAPP,
                        value=channel_id
                    )
                ),
                content=InteractiveContent(
                    interactive_type=InteractiveType.LIST,
                    body=dashboard_text,
                    action_items=menu_options  # Use menu options directly
                )
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

            return self._create_error_message(str(e))
