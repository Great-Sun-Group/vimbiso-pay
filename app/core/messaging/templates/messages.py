"""Message templates for different content types"""

# Account templates
ACCOUNT_DASHBOARD = """*{account}* 💳
*Account Handle:* {handle}

*💰 SECURED BALANCES*
{secured_balances}

*📊 NET ASSETS*
{net_assets}{tier_limit_display}"""

# Registration templates
REGISTER = """
{greeting}

Welcome to VimbisoPay 💰

We're your portal 🚪to the credex ecosystem 🌱

Become a member 🌐 and open a free account 💳 to get started 📈"""

# Error templates
INVALID_ACTION = """❌ Invalid option selected

⚠️ Your session has expired

Send me a greeting to log back in:
• hi
• ndeipi
• sawubona
... or any other greeting you prefer 👋"""

# Credex templates
AMOUNT_PROMPT = """💸 What offer amount and denomination?
- Defaults to USD 💵 (1, 73932.64)
- Valid denom placement ✨ (54 ZWG, ZWG 125.54)"""

HANDLE_PROMPT = "Enter account 💳 handle:"

OFFER_CONFIRMATION = """📝 Review your offer:
💸 Amount: {amount}
💳 To: {handle}"""

OFFER_COMPLETE = "✅ Your offer has been sent."

ACTION_PROMPT = "Select a credex offer to {action_type}:"

ACTION_CONFIRMATION = """📝 Review offer to {action_type}:
💸 Amount: {amount}
💳 From: {handle}"""

ACTION_COMPLETE = {
    "accept": "✅ Offer accepted successfully.",
    "decline": "✅ Offer declined successfully.",
    "cancel": "✅ Offer cancelled successfully.",
    "default": "✅ Action completed successfully."
}

ACTION_CANCELLED = {
    "accept": "Acceptance cancelled",
    "decline": "Decline cancelled",
    "cancel": "Cancellation cancelled",
    "default": "Action cancelled"
}

# Offer list templates
OFFER_LIST = """📋 {title}

{offers}"""

OFFER_ITEM = """💰 Amount: {amount}
👤 From: {counterparty}
📊 Status: {status}
"""
