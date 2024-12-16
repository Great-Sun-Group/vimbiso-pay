from django.conf import settings
from datetime import timedelta
import datetime
import os
import redis
import json
from urllib.parse import urlparse

# Initialize Redis client for state management
redis_url = urlparse(settings.REDIS_STATE_URL)
state_redis = redis.Redis(
    host=redis_url.hostname or 'localhost',
    port=redis_url.port or 6380,
    db=int(redis_url.path[1:]) if redis_url.path else 0,
    password=redis_url.password,
    decode_responses=True,
    socket_timeout=30,
    socket_connect_timeout=30,
    retry_on_timeout=True
)

# TTL Constants
ACTIVITY_TTL = 300  # 5 minutes in seconds for activity-based expiration
ABSOLUTE_JWT_TTL = 21600  # 6 hours in seconds for absolute token expiration

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

        # Get existing state values with debug logging
        existing_direction = state_redis.get(f"{self.user.mobile_number}_direction")
        existing_stage = state_redis.get(f"{self.user.mobile_number}_stage")
        existing_option = state_redis.get(f"{self.user.mobile_number}_option")
        existing_state = state_redis.get(f"{self.user.mobile_number}")
        self.jwt_token = state_redis.get(f"{self.user.mobile_number}_jwt_token")

        # Log existing state for debugging
        print("EXISTING STATE:", {
            "direction": existing_direction,
            "stage": existing_stage,
            "option": existing_option,
            "state": existing_state,
            "jwt_token": self.jwt_token
        })

        # Try to restore state from Redis
        if not existing_state:
            # Initialize with default state if none exists
            initial_state = {
                "stage": "handle_action_menu",
                "option": None,
                "profile": {
                    "data": {
                        "action": {},
                        "details": {}
                    }
                },
                "current_account": None,
                "flow_data": None
            }
            state_redis.setex(f"{self.user.mobile_number}", ACTIVITY_TTL, json.dumps(initial_state))
        else:
            # Ensure existing state has required structure
            try:
                current_state = json.loads(existing_state)
                if not isinstance(current_state, dict):
                    current_state = {}

                # Ensure profile structure exists
                if "profile" not in current_state:
                    current_state["profile"] = {
                        "data": {
                            "action": {},
                            "details": {}
                        }
                    }
                elif not isinstance(current_state["profile"], dict):
                    current_state["profile"] = {
                        "data": {
                            "action": {},
                            "details": {}
                        }
                    }
                elif "data" not in current_state["profile"]:
                    current_state["profile"]["data"] = {
                        "action": {},
                        "details": {}
                    }

                # Update state with proper structure
                state_redis.setex(f"{self.user.mobile_number}", ACTIVITY_TTL, json.dumps(current_state))
            except (json.JSONDecodeError, TypeError):
                # Reset to initial state if corrupted
                initial_state = {
                    "stage": "handle_action_menu",
                    "option": None,
                    "profile": {
                        "data": {
                            "action": {},
                            "details": {}
                        }
                    },
                    "current_account": None,
                    "flow_data": None
                }
                state_redis.setex(f"{self.user.mobile_number}", ACTIVITY_TTL, json.dumps(initial_state))

        # Refresh expiry for existing values
        if existing_direction:
            state_redis.setex(f"{self.user.mobile_number}_direction", ACTIVITY_TTL, existing_direction)
        if existing_stage:
            state_redis.setex(f"{self.user.mobile_number}_stage", ACTIVITY_TTL, existing_stage)
        if existing_option:
            state_redis.setex(f"{self.user.mobile_number}_option", ACTIVITY_TTL, existing_option)

        # Load current values
        self.direction = state_redis.get(f"{self.user.mobile_number}_direction")
        self.stage = state_redis.get(f"{self.user.mobile_number}_stage")
        self.option = state_redis.get(f"{self.user.mobile_number}_option")
        self.state = state_redis.get(f"{self.user.mobile_number}")
        if self.state:
            try:
                self.state = json.loads(self.state)
            except (json.JSONDecodeError, TypeError):
                self.state = {}
        else:
            self.state = {}

    def update_state(
        self, state: dict, update_from, stage=None, option=None, direction=None
    ):
        """Update user state with proper Redis management"""
        # Ensure we have a valid state object
        if not isinstance(state, dict):
            state = {}

        # Ensure profile structure exists
        if "profile" not in state:
            state["profile"] = {
                "data": {
                    "action": {},
                    "details": {}
                }
            }
        elif not isinstance(state["profile"], dict):
            state["profile"] = {
                "data": {
                    "action": {},
                    "details": {}
                }
            }
        elif "data" not in state["profile"]:
            state["profile"]["data"] = {
                "action": {},
                "details": {}
            }

        # Convert state to JSON string
        state_json = json.dumps(state)

        # Set state with activity timeout
        state_redis.setex(f"{self.user.mobile_number}", ACTIVITY_TTL, state_json)

        # Update stage if provided
        if stage:
            state_redis.setex(f"{self.user.mobile_number}_stage", ACTIVITY_TTL, stage)
            self.stage = stage

        # Update option if provided
        if option:
            state_redis.setex(f"{self.user.mobile_number}_option", ACTIVITY_TTL, option)
            self.option = option

        # Update direction if provided
        if direction:
            state_redis.setex(f"{self.user.mobile_number}_direction", ACTIVITY_TTL, direction)
            self.direction = direction

        # Update local state
        self.state = state

    def get_state(self, user):
        """Get current state with proper Redis handling"""
        state_json = state_redis.get(f"{user.mobile_number}")
        if state_json is None:
            # Initialize with proper structure
            state = {
                "stage": "handle_action_menu",
                "option": None,
                "profile": {
                    "data": {
                        "action": {},
                        "details": {}
                    }
                },
                "current_account": None,
                "flow_data": None
            }
            state_redis.setex(f"{user.mobile_number}", ACTIVITY_TTL, json.dumps(state))
        else:
            try:
                state = json.loads(state_json)
                # Ensure profile structure exists
                if "profile" not in state:
                    state["profile"] = {
                        "data": {
                            "action": {},
                            "details": {}
                        }
                    }
                elif not isinstance(state["profile"], dict):
                    state["profile"] = {
                        "data": {
                            "action": {},
                            "details": {}
                        }
                    }
                elif "data" not in state["profile"]:
                    state["profile"]["data"] = {
                        "action": {},
                        "details": {}
                    }
                state_redis.setex(f"{user.mobile_number}", ACTIVITY_TTL, json.dumps(state))
            except (json.JSONDecodeError, TypeError):
                state = {
                    "stage": "handle_action_menu",
                    "option": None,
                    "profile": {
                        "data": {
                            "action": {},
                            "details": {}
                        }
                    },
                    "current_account": None,
                    "flow_data": None
                }
                state_redis.setex(f"{user.mobile_number}", ACTIVITY_TTL, json.dumps(state))

        self.state = state
        return state

    def set_jwt_token(self, jwt_token):
        """Set JWT token with proper Redis handling"""
        if jwt_token:
            # Store token with absolute expiration
            state_redis.setex(f"{self.user.mobile_number}_jwt_token", ABSOLUTE_JWT_TTL, jwt_token)
            self.jwt_token = jwt_token

    def reset_state(self):
        """Reset all user state with proper Redis handling"""
        # Save current JWT token if within absolute expiry
        current_jwt = self.jwt_token
        jwt_ttl = state_redis.ttl(f"{self.user.mobile_number}_jwt_token")
        preserve_jwt = current_jwt and jwt_ttl > 0 and jwt_ttl <= ABSOLUTE_JWT_TTL

        # Clear all existing state
        state_redis.delete(f"{self.user.mobile_number}")
        state_redis.delete(f"{self.user.mobile_number}_stage")
        state_redis.delete(f"{self.user.mobile_number}_option")
        state_redis.delete(f"{self.user.mobile_number}_direction")

        # Set default values with activity timeout
        initial_state = {
            "stage": "handle_action_menu",
            "option": None,
            "profile": {
                "data": {
                    "action": {},
                    "details": {}
                }
            },
            "current_account": None,
            "flow_data": None
        }
        state_redis.setex(f"{self.user.mobile_number}", ACTIVITY_TTL, json.dumps(initial_state))
        state_redis.setex(f"{self.user.mobile_number}_stage", ACTIVITY_TTL, "handle_action_menu")
        state_redis.setex(f"{self.user.mobile_number}_direction", ACTIVITY_TTL, "OUT")

        # Update instance variables
        self.state = initial_state
        self.stage = "handle_action_menu"
        self.option = None
        self.direction = "OUT"

        # Restore JWT token if still valid
        if preserve_jwt:
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

REGISTER = """
{message}
"""

PROFILE_SELECTION = """
> *👤 Profile*
{message}
"""
INVALID_ACTION = "I'm sorry, I didn't understand that. Can you please try again?"
DELAY = "Please wait while I process your request..."
