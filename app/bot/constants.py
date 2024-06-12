
from django.core.cache import cache
from datetime import timedelta

def truncate_item_name(item_name, max_length=4):
    actual_length = len(item_name.replace(" ", ""))
    item_name = item_name.capitalize()
    occurances = lambda string : max_length + sum([string.count('i'), string.count('l'), string.count(" "), string.count('r'), string.count('-')]) - sum([string.count('m'), string.count('w'), string.count(" ")])
    if actual_length > max_length:
        mxl = occurances(item_name[:max_length])
        return item_name[:max_length if mxl > max_length else mxl ] + " {:<{}}".format("...", 1)
    else:
        return item_name

def print_receipt(items, fees, total):
    max_item_length = len(max(truncate_item_name(item[0]) for item in items))
    header = "{:<{}} {:<{}}     {:<{}}".format("*Item*", 12, "*Qty*", 3, " *Cost*", 5)
    # receipt +="\n"+"---------------------------------"
    receipt = f"\n{header}"
    receipt +="\n"+"................................"
    for item in items:
        diff = int(max_item_length)-len(truncate_item_name(item[0]))
        receipt +="\n {:<{}}   {:<{}}   {:<{}}".format(truncate_item_name(item[0]) if len(truncate_item_name(item[0])) == int(max_item_length) else truncate_item_name(item[0]) + " "*diff, 3, item[1], 3 if len(str(item[1]))==1 else 2, f"${item[2]}{0 if len(str(item[2])) == 3 else ''}", 1)
    receipt +="\n"+"................................"
    for item in fees:
        receipt +="\n {:<{}} {:<{}} {:<{}}".format(item[0], 0, item[1], 2, f"${item[2]}{0 if len(str(item[2])) == 2 else ''}", 1)
    # receipt +="\n"+"*" * (max_item_length + max_quantity_length + max_price_length + 18)
    receipt +="\n"+"................................"
    for item in total:
        receipt +="\n {:<{}} {:<{}} {:<{}}".format(item[0], 0, item[1], 2, f"*${item[2]}*{0 if len(str(item[2])) == 2 else ''}", 1)

    # receipt +="\n"+"---------------------------------"
    return receipt

# items = [('Sleep Onesie 2.5 Tog Oatmeal Marle', 1, 3.65), ('Comfortable First Walker Baby Sheep Ear Shoes', 1, 2.5), ('Original Instant Mixed Coffee', 1, 6.5)]
# for item in items:
#     max_item_length = len(max(truncate_item_name(item[0]) for item in items))
#     print(len(truncate_item_name(item[0])) , type(len(truncate_item_name(item[0])) ))
#     print(max_item_length, type(max_item_length))
    
#     print(">>", diff, type(diff))
#     print())



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
        self.direction = cache.get(f"{self.user.mobile_number}_direction", "OUT")
        self.stage = cache.get(f"{self.user.mobile_number}_stage", "handle_action_menu")
        self.option = cache.get(f"{self.user.mobile_number}_option")
        self.state = cache.get(f"{self.user.mobile_number}", {})


    def update_state(self, state: dict, update_from, stage=None, option=None, direction=None):
        """Get wallets by user."""
        # pylint: disable=no-member
        print("UPDATING STATE : ", update_from)
        cache.set(f"{self.user.mobile_number}", state, timeout=60*15)
        if stage:
            cache.set(f"{self.user.mobile_number}_stage", stage, timeout=60*15)
        if option:
            cache.set(f"{self.user.mobile_number}_option", option, timeout=60*15)
        if direction:
            cache.set(f"{self.user.mobile_number}_direction", direction, timeout=60*15)
      
    def get_state(self, user):
        self.state = cache.get(f"{user.mobile_number}", {})
        return self.state
    
    def reset_state(self):
        state = cache.get(f"{self.user.mobile_number}", {})
        state['state'] = {}
        cache.set(f"{self.user.mobile_number}_stage", "handle_action_menu")
        cache.delete(f"{self.user.mobile_number}_option")
        return cache.set(f"{self.user.mobile_number}", state)

class CachedUser:
    def __init__(self, mobile_number) -> None:
        self.first_name = "Welcome"
        self.last_name = "Visitor"
        self.role = "DEFAULT"
        self.email = "customer@credex.co.zw"
        self.mobile_number = mobile_number
        self.registration_complete = False
        self.state = CachedUserState(self)
        

  
MENU_OPTIONS = {
    '1': "handle_action_pending_offers_in",
    'handle_action_pending_offers_in': "handle_action_pending_offers_in",
    '2': "handle_action_pending_offers_out",
    'handle_action_pending_offers_out': "handle_action_pending_offers_out",
    '3': "handle_action_offer_credex",
    'handle_action_offer_credex': "handle_action_offer_credex",
    '4': "handle_action_transactions",
    'handle_action_transactions': "handle_action_transactions"
}


ABOUT ="""
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
use the charge they’ve received 
to purchase goods and services
within the credex ecosystem, 
also at no charge. When an 
account charge is cashed out 
at aregistered agent, there 
is a 2% fee.
"""

