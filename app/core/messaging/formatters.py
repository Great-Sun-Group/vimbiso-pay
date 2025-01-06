"""Message formatters for different content types

This module provides message formatting for all content types:
- Account messages
- Registration messages
- Error messages
"""
from typing import Dict

from .greetings import get_random_greeting


class AccountFormatters:
    """Account-related message formatters"""

    # Account templates
    ACCOUNT_DASHBOARD = """*{account}* 💳
*Account Handle:* {handle}

*💰 SECURED BALANCES*
{securedNetBalancesByDenom}

*📊 NET ASSETS*
{netCredexAssetsInDefaultDenom}{tier_limit_display}"""

    @staticmethod
    def format_dashboard(balance_data: Dict) -> str:
        """Format dashboard display"""
        # Format secured balances with proper line breaks
        secured_balances = balance_data.get("securedNetBalancesByDenom", [])
        secured = "\n".join(secured_balances) if secured_balances else "0.00 USD"

        # Format net assets with proper default and denomination
        try:
            net_value = float(balance_data.get("netCredexAssetsInDefaultDenom", "0.00"))
            denom = balance_data.get("defaultDenom", "USD")
            net_assets = f"  {net_value:.2f} {denom}"
        except (ValueError, TypeError):
            net_assets = f"  0.00 {balance_data.get('defaultDenom', 'USD')}"

        # Format tier limit with 2 decimal places if present
        tier_limit = ""
        if "tier_limit_raw" in balance_data:
            try:
                limit_value = float(balance_data["tier_limit_raw"])
                tier_limit = f"\n\n⏳ DAILY MEMBER TIER LIMIT: {limit_value:.2f} USD"
            except (ValueError, TypeError):
                tier_limit = "\n\n⏳ DAILY MEMBER TIER LIMIT: 0.00 USD"

        return AccountFormatters.ACCOUNT_DASHBOARD.format(
            account=balance_data.get("accountName"),
            handle=balance_data.get("accountHandle"),
            securedNetBalancesByDenom=secured,
            netCredexAssetsInDefaultDenom=net_assets,
            tier_limit_display=tier_limit
        )


class RegistrationFormatters:
    """Registration-related message formatters"""

    REGISTER = """
{greeting}

Welcome to VimbisoPay 💰

We're your portal 🚪to the credex ecosystem 🌱

Become a member 🌐 and open a free account 💳 to get started 📈"""

    @staticmethod
    def format_welcome() -> str:
        """Format welcome message"""
        greeting = get_random_greeting(include_emoji=True, include_suffix=False)
        return RegistrationFormatters.REGISTER.format(greeting=greeting)


class ErrorFormatters:
    """Error-related message formatters"""

    INVALID_ACTION = """❌ Invalid option selected

⚠️ Your session has expired

Send me a greeting to log back in:
• hi
• ndeipi
• sawubona
... or any other greeting you prefer 👋"""

    @staticmethod
    def format_invalid_action() -> str:
        """Format invalid action message"""
        return ErrorFormatters.INVALID_ACTION
