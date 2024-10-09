from django.core.cache import cache
from datetime import timedelta

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
    "retry"
]

import datetime


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
        self.direction = cache.get(f"{self.user.mobile_number}_direction", "OUT")
        self.stage = cache.get(f"{self.user.mobile_number}_stage", "handle_action_menu")
        self.option = cache.get(f"{self.user.mobile_number}_option")
        self.state = cache.get(f"{self.user.mobile_number}", {})
        self.jwt_token = cache.get(f"{self.user.mobile_number}_jwt_token")

    def update_state(self, state: dict, update_from, stage=None, option=None, direction=None):
        """Get wallets by user."""
        # pylint: disable=no-member
        # print("UPDATING FROM ", update_from, stage, option, direction, state)
        cache.set(f"{self.user.mobile_number}", state, timeout=60 * 5)
        if stage:
            cache.set(f"{self.user.mobile_number}_stage", stage, timeout=60 * 5)
        if option:
            cache.set(f"{self.user.mobile_number}_option", option, timeout=60 * 5)
        if direction:
            cache.set(f"{self.user.mobile_number}_direction", direction, timeout=60 * 5)
        self.state = cache.get(f"{self.user.mobile_number}")
        self.stage = cache.get(f"{self.user.mobile_number}_stage")
        self.option = cache.get(f"{self.user.mobile_number}_option")
        self.direction = cache.get(f"{self.user.mobile_number}_direction")

    def get_state(self, user):
        self.state = cache.get(f"{user.mobile_number}", {})
        return self.state
    
    def set_jwt_token(self, jwt_token):
        cache.set(f"{self.user.mobile_number}_jwt_token", jwt_token, timeout=60 * 5)
        # print("SETTING JWT TOKEN", jwt_token)
        self.jwt_token = cache.get(f"{self.user.mobile_number}_jwt_token")

    def reset_state(self):
        state = cache.get(f"{self.user.mobile_number}", {})
        state['state'] = {}
        cache.set(f"{self.user.mobile_number}_stage", "handle_action_menu")
        cache.delete(f"{self.user.mobile_number}_option")
        cache.set(f"{self.user.mobile_number}", {}, timeout=60 * 5)
        self.state = cache.get(f"{self.user.mobile_number}")
        self.stage = cache.get(f"{self.user.mobile_number}_stage")
        self.option = cache.get(f"{self.user.mobile_number}_option")


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
    '1': "handle_action_offer_credex",
    'handle_action_offer_credex': "handle_action_offer_credex",
    '2': "handle_action_pending_offers_in",
    'handle_action_pending_offers_in': "handle_action_pending_offers_in",
    '3': "handle_action_pending_offers_out",
    'handle_action_pending_offers_out': "handle_action_pending_offers_out",
    '4': "handle_action_transactions",
    'handle_action_transactions': "handle_action_transactions",
    '5': "handle_action_switch_account",
    'handle_action_switch_account': "handle_action_switch_account",
}

MENU_OPTIONS_2 = {
    '1': "handle_action_offer_credex",
    'handle_action_offer_credex': "handle_action_offer_credex",
    '2': "handle_action_pending_offers_in",
    'handle_action_pending_offers_in': "handle_action_pending_offers_in",
    '3': "handle_action_pending_offers_out",
    'handle_action_pending_offers_out': "handle_action_pending_offers_out",
    '4': "handle_action_transactions",
    'handle_action_transactions': "handle_action_transactions",
    '5': "handle_action_authorize_member",
    'handle_action_authorize_member': "handle_action_authorize_member",
    '6': "handle_action_notifications",
    'handle_action_notifications': "handle_action_notifications",
    '7': "handle_action_switch_account",
    'handle_action_switch_account': "handle_action_switch_account",

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
