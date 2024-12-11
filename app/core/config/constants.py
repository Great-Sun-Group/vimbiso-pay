from django.core.cache import cache
from datetime import timedelta
import datetime
import os

GREETINGS = [
    "menu",
    "memu",
    "hi",
    "hie",
    "cancel",
    "home",
    "hy",
    "reset",
    "hello",
    "x",
    "c",
    "no",
    "No",
    "n",
    "N",
    "hey",
    "y",
    "yes",
    "retry",
]

# Feature flags
USE_PROGRESSIVE_FLOW = os.environ.get('USE_PROGRESSIVE_FLOW', 'False') == 'True'


def get_greeting(name):
    current_time = datetime.datetime.now() + timedelta(hours=2)
    hour = current_time.hour

    if 5 <= hour < 12:
        return f"Good Morning {name} 🌅"
    elif 12 <= hour < 18:
        return f"Good Afternoon {name} ☀️"
    elif 18 <= hour < 22:
        return f"Good Evening {name} 🌆"
    else:
        return f"Hello There {name} 🌙"


class CachedUserState:
    def __init__(self, user) -> None:
        self.user = user
        print("USER", user)

        # Get existing state values
        existing_direction = cache.get(f"{self.user.mobile_number}_direction")
        existing_stage = cache.get(f"{self.user.mobile_number}_stage")
        existing_option = cache.get(f"{self.user.mobile_number}_option")
        existing_state = cache.get(f"{self.user.mobile_number}")
        self.jwt_token = cache.get(f"{self.user.mobile_number}_jwt_token")

        # Initialize with defaults only if no state exists at all
        if not any([existing_direction, existing_stage, existing_option, existing_state]):
            cache.set(f"{self.user.mobile_number}_direction", "OUT", timeout=60 * 5)
            cache.set(f"{self.user.mobile_number}_stage", "handle_action_menu", timeout=60 * 5)
            cache.set(f"{self.user.mobile_number}", {}, timeout=60 * 5)
        else:
            # Refresh expiry for existing values
            if existing_direction:
                cache.set(f"{self.user.mobile_number}_direction", existing_direction, timeout=60 * 5)
            if existing_stage:
                cache.set(f"{self.user.mobile_number}_stage", existing_stage, timeout=60 * 5)
            if existing_option:
                cache.set(f"{self.user.mobile_number}_option", existing_option, timeout=60 * 5)
            if existing_state:
                cache.set(f"{self.user.mobile_number}", existing_state, timeout=60 * 5)

        # Load current values
        self.direction = cache.get(f"{self.user.mobile_number}_direction")
        self.stage = cache.get(f"{self.user.mobile_number}_stage")
        self.option = cache.get(f"{self.user.mobile_number}_option")
        self.state = cache.get(f"{self.user.mobile_number}")

    def update_state(
        self, state: dict, update_from, stage=None, option=None, direction=None
    ):
        """Update user state with proper cache management"""
        # Ensure we have a valid state object
        if not isinstance(state, dict):
            state = {}

        # Set state with increased timeout
        cache.set(f"{self.user.mobile_number}", state, timeout=60 * 5)

        # Update stage if provided
        if stage:
            cache.set(f"{self.user.mobile_number}_stage", stage, timeout=60 * 5)
            self.stage = stage

        # Update option if provided
        if option:
            cache.set(f"{self.user.mobile_number}_option", option, timeout=60 * 5)
            self.option = option

        # Update direction if provided
        if direction:
            cache.set(f"{self.user.mobile_number}_direction", direction, timeout=60 * 5)
            self.direction = direction

        # Update local state
        self.state = state

        # Force a cache refresh to ensure consistency
        cache.touch(f"{self.user.mobile_number}", timeout=60 * 5)
        if stage:
            cache.touch(f"{self.user.mobile_number}_stage", timeout=60 * 5)
        if option:
            cache.touch(f"{self.user.mobile_number}_option", timeout=60 * 5)
        if direction:
            cache.touch(f"{self.user.mobile_number}_direction", timeout=60 * 5)

    def get_state(self, user):
        """Get current state with proper cache handling"""
        state = cache.get(f"{user.mobile_number}")
        if state is None:
            state = {}
            cache.set(f"{user.mobile_number}", state, timeout=60 * 5)
        else:
            # Refresh cache timeout
            cache.touch(f"{user.mobile_number}", timeout=60 * 5)
        self.state = state
        return state

    def set_jwt_token(self, jwt_token):
        """Set JWT token with proper cache handling"""
        if jwt_token:
            cache.set(f"{self.user.mobile_number}_jwt_token", jwt_token, timeout=60 * 5)
            self.jwt_token = jwt_token
            # Refresh cache timeout
            cache.touch(f"{self.user.mobile_number}_jwt_token", timeout=60 * 5)

    def reset_state(self):
        """Reset all user state with proper cache handling"""
        # Save current JWT token
        current_jwt = self.jwt_token

        # Clear all existing state
        cache.delete(f"{self.user.mobile_number}")
        cache.delete(f"{self.user.mobile_number}_stage")
        cache.delete(f"{self.user.mobile_number}_option")
        cache.delete(f"{self.user.mobile_number}_direction")

        # Set default values with timeout
        cache.set(f"{self.user.mobile_number}", {}, timeout=60 * 5)
        cache.set(f"{self.user.mobile_number}_stage", "handle_action_menu", timeout=60 * 5)
        cache.set(f"{self.user.mobile_number}_direction", "OUT", timeout=60 * 5)

        # Update instance variables
        self.state = {}
        self.stage = "handle_action_menu"
        self.option = None
        self.direction = "OUT"

        # Restore JWT token if it exists
        if current_jwt:
            self.set_jwt_token(current_jwt)


class CachedUser:
    def __init__(self, mobile_number) -> None:
        self.first_name = "Welcome"
        self.last_name = "Visitor"
        self.role = "DEFAULT"
        self.email = "customer@credex.co.zw"
        self.mobile_number = mobile_number
        self.registration_complete = False
        self.state = CachedUserState(self)
        self.jwt_token = self.state.jwt_token


MENU_OPTIONS_1 = {
    "1": "handle_action_offer_credex",
    "handle_action_offer_credex": "handle_action_offer_credex",
    "2": "handle_action_pending_offers_in",
    "handle_action_pending_offers_in": "handle_action_pending_offers_in",
    "3": "handle_action_pending_offers_out",
    "handle_action_pending_offers_out": "handle_action_pending_offers_out",
    "4": "handle_action_transactions",
    "handle_action_transactions": "handle_action_transactions",
    "5": "handle_action_switch_account",
    "handle_action_switch_account": "handle_action_switch_account",
}

MENU_OPTIONS_2 = {
    "1": "handle_action_offer_credex",
    "handle_action_offer_credex": "handle_action_offer_credex",
    "2": "handle_action_pending_offers_in",
    "handle_action_pending_offers_in": "handle_action_pending_offers_in",
    "3": "handle_action_pending_offers_out",
    "handle_action_pending_offers_out": "handle_action_pending_offers_out",
    "4": "handle_action_transactions",
    "handle_action_transactions": "handle_action_transactions",
    "5": "handle_action_authorize_member",
    "handle_action_authorize_member": "handle_action_authorize_member",
    "6": "handle_action_notifications",
    "handle_action_notifications": "handle_action_notifications",
    "7": "handle_action_switch_account",
    "handle_action_switch_account": "handle_action_switch_account",
}

ABOUT = """
Today credex is being used
for combi rides in Harare.
Credex solves the problem
of small change. Riders
charge their credex account
with USD at a verified agent,
and then use that charge in
any amount to pay for one
ride at a time.

When a combi accepts your
credex, your charge is
transferred to their
account, and they can cash
it out at a registered agent.
There is no fee to charge
your account, or to use that
charge to pay for goods and
services.

Combi drivers and owners can
use the charge they've received
to purchase goods and services
within the credex ecosystem,
also at no charge. When an
account charge is cashed out
at aregistered agent, there
is a 2% fee.
"""

# Add the missing constants
REGISTER = """
{message}
"""

PROFILE_SELECTION = """
> *👤 Profile*
{message}
"""
INVALID_ACTION = "I'm sorry, I didn't understand that. Can you please try again?"
DELAY = "Please wait while I process your request..."
