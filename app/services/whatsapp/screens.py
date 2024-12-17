"""WhatsApp message templates and screens"""

ACCOUNT_HOME = """*💳 {account}*
*Account Handle:* {handle}

{balance}"""

INVALID_ACTION = """❌ Invalid option selected.

⚠️ Your session may have expired.
Send "hi" to log back in."""

BALANCE = """*💰 SECURED BALANCES*
{securedNetBalancesByDenom}

*📊 NET ASSETS*
  {netCredexAssetsInDefaultDenom}
{tier_limit_display}"""

REGISTER = """Welcome to VimbisoPay 💰

We're your portal 🚪🌐
to the credex ecosystem 🌱

Open a free credex account 💳
to get started 📈"""
