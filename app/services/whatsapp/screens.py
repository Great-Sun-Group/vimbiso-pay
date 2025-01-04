"""WhatsApp message templates and screens"""

# Account templates
ACCOUNT_HOME = """*💳 {account}*
*Account Handle:* {handle}

{balance}"""

# Dashboard template
ACCOUNT_DASHBOARD = """*💰 SECURED BALANCES*
{securedNetBalancesByDenom}

*📊 NET ASSETS*
  {netCredexAssetsInDefaultDenom}
{tier_limit_display}"""

# Registration templates
REGISTER = """Welcome to VimbisoPay 💰

We're your portal 🚪to the credex ecosystem 🌱

Become a member 🌐 and open a free account 💳 to get started 📈"""

# Error templates
INVALID_ACTION = """❌ Invalid option selected.

⚠️ Your session may have expired.
Send "hi" to log back in."""


# Message formatting helpers
def format_dashboard(balance_data: dict) -> str:
    """Format dashboard display"""
    secured = balance_data.get("securedNetBalancesByDenom", "")
    net_assets = balance_data.get("netCredexAssetsInDefaultDenom", "")
    tier_limit = balance_data.get("tier_limit_display", "")

    return ACCOUNT_DASHBOARD.format(
        securedNetBalancesByDenom=secured,
        netCredexAssetsInDefaultDenom=net_assets,
        tier_limit_display=tier_limit
    )


def format_account(account_data: dict) -> str:
    """Format account display"""
    account = account_data.get("account", "")
    handle = account_data.get("handle", "")
    balance = format_dashboard(account_data)

    return ACCOUNT_HOME.format(
        account=account,
        handle=handle,
        balance=balance
    )
