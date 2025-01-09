"""WhatsApp-specific menu formatters

This module provides menu formatting specific to WhatsApp interactions.
Organizes options into logical sections for better UX.
"""

from typing import Dict, Any


class WhatsAppMenus:
    """WhatsApp menu formatters"""

    # Menu sections with options
    MENU_SECTIONS = {
        "Credex Actions": {
            "offer_secured": "💸 Make a secured offer",
            "accept_offers": "✅ Accept pending offers",
            "decline_offers": "❌ Decline pending offers",
            "cancel_offers": "🚫 Cancel your offers"
        },
        "Account Actions": {
            "view_ledger": "📊 View your ledger"
        },
        "Member Actions": {
            "upgrade_membertier": "⭐ Upgrade your tier"
        }
    }

    @staticmethod
    def get_interactive_menu() -> Dict[str, Any]:
        """Get menu in WhatsApp interactive list format"""
        sections = []
        for section_title, options in WhatsAppMenus.MENU_SECTIONS.items():
            section_rows = [
                {
                    "id": option_id,
                    "title": option_text.split(" ", 1)[1],  # Remove emoji for title
                    "description": option_text  # Keep emoji in description
                }
                for option_id, option_text in options.items()
            ]
            sections.append({
                "title": section_title,
                "rows": section_rows
            })

        return {
            "type": "list",
            "body": {"text": "*Account Dashboard Actions*\nChoose an option from the menu below:"},
            "action": {
                "button": "🕹️ Select Action",
                "sections": sections
            }
        }

    @staticmethod
    def is_valid_option(option: str) -> bool:
        """Check if option is valid menu selection"""
        return any(
            option in section_options
            for section_options in WhatsAppMenus.MENU_SECTIONS.values()
        )
