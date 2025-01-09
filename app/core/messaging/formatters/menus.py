"""WhatsApp-specific menu formatters

This module provides menu formatting specific to WhatsApp interactions.
Organizes options into logical sections for better UX.
"""

from typing import Any, Dict


class WhatsAppMenus:
    """WhatsApp menu formatters"""

    # Menu sections with options
    ACCOUNT_DASHBOARD_MENU = {
        "Credex Actions": {
            "offer_secured": "💸 Offer secured credex",
            "accept_offers_bulk": "✅ Accept all pending offers{pending_in_formatted}",
            "accept_offer": "✅ Accept a pending offer{pending_in_formatted}",
            "decline_offer": "❌ Decline a pending offer{pending_in_formatted}",
            "cancel_offer": "🚫 Cancel your offer{pending_out_formatted}"
        },
        "Account Actions": {
            "view_ledger": "📊 View account ledger"
        },
        "Member Actions": {
            "upgrade_membertier": "⭐ Upgrade your member tier"
        }
    }

    @staticmethod
    def get_interactive_menu(active_account: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get menu in WhatsApp interactive list format

        Args:
            active_account: Optional active account data containing offers
        """
        # Get pending counts from active account
        pending_in = 0
        pending_out = 0
        if active_account:
            pending_in = len([
                o for o in active_account.get("offers", [])
                if o.get("status") == "pending" and o.get("type") == "incoming"
            ])
            pending_out = len([
                o for o in active_account.get("offers", [])
                if o.get("status") == "pending" and o.get("type") == "outgoing"
            ])

        # Format pending counts
        pending_in_formatted = f" ({pending_in})" if pending_in > 0 else ""
        pending_out_formatted = f" ({pending_out})" if pending_out > 0 else ""

        # Build menu sections
        sections = []
        menu_data = WhatsAppMenus.ACCOUNT_DASHBOARD_MENU.copy()

        # Filter out pending offer options if no pending offers
        credex_actions = menu_data["Credex Actions"].copy()
        if pending_in == 0:
            credex_actions.pop("accept_offers_bulk", None)
            credex_actions.pop("accept_offer", None)
            credex_actions.pop("decline_offer", None)
        if pending_out == 0:
            credex_actions.pop("cancel_offer", None)
        menu_data["Credex Actions"] = credex_actions

        # Build sections with formatted text
        for section_title, options in menu_data.items():
            section_rows = [
                {
                    "id": option_id,
                    "title": option_text.split(" ", 1)[1],  # Remove emoji for title
                    "description": option_text.format(  # Keep emoji in description
                        pending_in_formatted=pending_in_formatted,
                        pending_out_formatted=pending_out_formatted
                    )
                }
                for option_id, option_text in options.items()
            ]
            # Only add sections that have rows
            if section_rows:
                sections.append({
                    "title": section_title,
                    "rows": section_rows
                })

        return {
            "type": "list",
            "body": {"text": ""},
            "action": {
                "button": "🕹️ Select Action",
                "sections": sections
            }
        }

    @staticmethod
    def is_valid_option(option: Any) -> bool:
        """Check if option is valid menu selection

        Args:
            option: Either a string option ID or a dict containing interactive message data
        """
        # Handle interactive list selections
        if isinstance(option, dict):
            if option.get("type") == "interactive":
                interactive = option.get("interactive", {})
                if interactive.get("type") == "list_reply":
                    option_id = interactive.get("list_reply", {}).get("id")
                    if option_id:
                        return any(
                            option_id in section_options
                            for section_options in WhatsAppMenus.ACCOUNT_DASHBOARD_MENU.values()
                        )
            return False

        # Handle direct string options
        if isinstance(option, str):
            return any(
                option in section_options
                for section_options in WhatsAppMenus.ACCOUNT_DASHBOARD_MENU.values()
            )

        return False
