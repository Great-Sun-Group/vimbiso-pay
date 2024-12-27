"""Dashboard flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Optional

from core.messaging.flow import Flow
from core.messaging.types import (ChannelIdentifier, ChannelType,
                                  InteractiveContent, InteractiveType, Message,
                                  MessageRecipient)
from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator

from ...screens import format_account

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class DashboardFlow(Flow):
    """Flow for handling dashboard display with strict state management"""

    def __init__(self, state_manager: Any, success_message: Optional[str] = None, flow_type: str = "dashboard"):
        """Initialize dashboard flow enforcing SINGLE SOURCE OF TRUTH

        Args:
            state_manager: State manager instance
            success_message: Optional message to display
            flow_type: Flow type identifier

        Raises:
            ValueError: If state validation fails or required data missing
        """
        if not state_manager:
            raise ValueError("State manager is required")
        if flow_type not in {"dashboard", "refresh", "offers", "transactions"}:
            raise ValueError("Invalid flow type")

        # Validate ALL required state at boundary
        required_fields = {"channel", "member_id", "account_id", "authenticated", "jwt_token"}
        current_state = {
            field: state_manager.get(field)
            for field in required_fields
        }

        # Initial validation
        validation = StateValidator.validate_before_access(
            current_state,
            required_fields  # All fields required for dashboard
        )
        if not validation.is_valid:
            raise ValueError(f"State validation failed: {validation.error_message}")

        # Get channel info (SINGLE SOURCE OF TRUTH)
        channel = state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            raise ValueError("Channel identifier not found")

        # Initialize services
        self.state_manager = state_manager
        self.success_message = success_message
        self.credex_service = state_manager.get_or_create_credex_service()
        if not self.credex_service:
            raise ValueError("Failed to initialize credex service")

        # Initialize base Flow class with static ID
        super().__init__(id="dashboard_flow", steps=[])  # Dashboard has no steps, just displays info

        # Log initialization
        audit.log_flow_event(
            self.id,
            "initialization",
            None,
            {
                "flow_type": flow_type,
                "channel_id": channel["identifier"]
            },
            "success"
        )

        logger.info(f"Initialized {flow_type} dashboard flow for channel {channel['identifier']}")

    def complete(self) -> Message:
        """Complete flow enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate ALL required state at boundary
            required_fields = {"channel", "member_id", "account_id", "authenticated", "jwt_token"}
            current_state = {
                field: self.state_manager.get(field)
                for field in required_fields
            }

            # Validate required fields
            validation = StateValidator.validate_before_access(
                current_state,
                required_fields
            )
            if not validation.is_valid:
                raise ValueError(f"State validation failed: {validation.error_message}")

            # Get channel info (SINGLE SOURCE OF TRUTH)
            channel = self.state_manager.get("channel")
            if not channel or not channel.get("identifier"):
                raise ValueError("Channel identifier not found")

            # Get member and account info (SINGLE SOURCE OF TRUTH)
            member_id = self.state_manager.get("member_id")
            if not member_id:
                raise ValueError("Member ID not found")

            account_id = self.state_manager.get("account_id")
            if not account_id:
                raise ValueError("Account ID not found")

            # Log dashboard fetch attempt
            logger.info(f"Fetching dashboard data for channel {channel['identifier']}")

            # Get account details from CredEx service
            success, account_data = self.credex_service.get_member_accounts(member_id)
            if not success:
                error_msg = account_data.get("message", "Failed to get account details")
                logger.error(f"API call failed: {error_msg} for channel {channel['identifier']}")
                raise ValueError(error_msg)

            # Validate account data
            if not isinstance(account_data, dict) or "accounts" not in account_data:
                raise ValueError("Invalid account data format")

            # Find personal account
            personal_account = next(
                (account for account in account_data["accounts"]
                 if account.get("accountID") == account_id),
                None
            )
            if not personal_account:
                raise ValueError("Account not found")

            # Create dashboard text
            account_info = {
                "account": personal_account.get("name", "Personal Account"),
                "handle": personal_account.get("handle", "Not Available"),
                "securedNetBalancesByDenom": personal_account.get("securedNetBalancesByDenom", ""),
                "netCredexAssetsInDefaultDenom": personal_account.get("netCredexAssetsInDefaultDenom", ""),
                "tier_limit_display": personal_account.get("tierLimitDisplay", "")
            }

            dashboard_text = format_account(account_info)

            # Get menu options
            menu_options = {
                "button": "Options",
                "sections": [
                    {
                        "title": "Account Options",
                        "rows": [
                            {
                                "id": "refresh",
                                "title": "🔄 Refresh Dashboard"
                            },
                            {
                                "id": "offers",
                                "title": "💰 View Offers"
                            },
                            {
                                "id": "transactions",
                                "title": "📊 View Transactions"
                            }
                        ]
                    }
                ]
            }

            # Add success message if provided
            if self.success_message:
                dashboard_text = f"{self.success_message}\n\n{dashboard_text}"

            # Log success
            logger.info(f"Successfully fetched dashboard for channel {channel['identifier']}")

            # Return formatted message
            return Message(
                recipient=MessageRecipient(
                    member_id=member_id,
                    channel_id=ChannelIdentifier(
                        channel=ChannelType.WHATSAPP,
                        value=channel["identifier"]
                    )
                ),
                content=InteractiveContent(
                    interactive_type=InteractiveType.LIST,
                    body=dashboard_text,
                    action_items=menu_options
                )
            )

        except ValueError as e:
            # Get channel info for error logging
            try:
                channel = self.state_manager.get("channel")
                channel_id = channel["identifier"] if channel else "unknown"
            except (ValueError, KeyError, TypeError) as err:
                logger.error(f"Failed to get channel for error logging: {str(err)}")
                channel_id = "unknown"

            logger.error(f"Dashboard error: {str(e)} for channel {channel_id}")

            # Return error message
            return Message(
                recipient=MessageRecipient(
                    member_id="unknown",
                    channel_id=ChannelIdentifier(
                        channel=ChannelType.WHATSAPP,
                        value=channel_id
                    )
                ),
                content=InteractiveContent(
                    interactive_type=InteractiveType.LIST,
                    body="❌ Error: Unable to load dashboard. Please try again.",
                    action_items={
                        "button": "Options",
                        "sections": [
                            {
                                "title": "Available Actions",
                                "rows": [
                                    {
                                        "id": "refresh",
                                        "title": "🔄 Try Again"
                                    }
                                ]
                            }
                        ]
                    }
                )
            )
