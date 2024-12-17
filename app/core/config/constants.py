"""Constants and cached user state management"""
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
        existing_state_json = state_redis.get(f"{self.user.mobile_number}")
        self.jwt_token = state_redis.get(f"{self.user.mobile_number}_jwt_token")

        # Initialize state data
        state_data = None

        # Try to parse existing state
        try:
            if existing_state_json:
                state_data = json.loads(existing_state_json)
                if isinstance(state_data, dict):
                    # Preserve JWT token if it exists in state
                    if "jwt_token" in state_data:
                        self.jwt_token = state_data["jwt_token"]
                        # Update Redis JWT token
                        if self.jwt_token:
                            state_redis.setex(f"{self.user.mobile_number}_jwt_token", ABSOLUTE_JWT_TTL, self.jwt_token)

                    # Ensure profile structure exists
                    if "profile" not in state_data:
                        state_data["profile"] = {
                            "data": {
                                "action": {},
                                "details": {}
                            }
                        }
                    elif not isinstance(state_data["profile"], dict):
                        state_data["profile"] = {
                            "data": {
                                "action": {},
                                "details": {}
                            }
                        }
                    elif "data" not in state_data["profile"]:
                        state_data["profile"]["data"] = {
                            "action": {},
                            "details": {}
                        }
        except json.JSONDecodeError:
            state_data = None

        # Create initial state structure
        initial_state = {
            "stage": existing_stage or "handle_action_menu",
            "option": existing_option,
            "direction": existing_direction or "OUT",
            "profile": {
                "data": {
                    "action": {},
                    "details": {}
                }
            },
            "current_account": None,
            "flow_data": None
        }

        # Merge with existing state if available
        if state_data and isinstance(state_data, dict):
            # Merge profile data properly
            if "profile" in state_data and isinstance(state_data["profile"], dict):
                initial_state["profile"] = self._ensure_profile_structure(state_data["profile"])
            # Merge other fields
            for key, value in state_data.items():
                if key != "profile":  # Skip profile as we've already handled it
                    initial_state[key] = value

        # Add JWT token if it exists
        if self.jwt_token:
            initial_state["jwt_token"] = self.jwt_token

        # Store the complete state
        self.state = initial_state
        self.stage = initial_state["stage"]
        self.option = initial_state["option"]
        self.direction = initial_state["direction"]

        # Log existing state for debugging
        print("EXISTING STATE:", self.state)

        # Update Redis with complete state
        state_redis.setex(f"{self.user.mobile_number}", ACTIVITY_TTL, json.dumps(self.state))
        if self.stage:
            state_redis.setex(f"{self.user.mobile_number}_stage", ACTIVITY_TTL, self.stage)
        if self.option:
            state_redis.setex(f"{self.user.mobile_number}_option", ACTIVITY_TTL, self.option)
        if self.direction:
            state_redis.setex(f"{self.user.mobile_number}_direction", ACTIVITY_TTL, self.direction)
        if self.jwt_token:
            state_redis.setex(f"{self.user.mobile_number}_jwt_token", ABSOLUTE_JWT_TTL, self.jwt_token)

    def _ensure_profile_structure(self, profile_data: dict) -> dict:
        """Ensure profile data has proper structure"""
        if not isinstance(profile_data, dict):
            return {
                "data": {
                    "action": {},
                    "details": {}
                }
            }

        # Create a deep copy to avoid modifying the original
        result = profile_data.copy()

        # Handle both direct and nested data structures
        if "data" not in result:
            # Preserve existing data by moving it into data field
            result = {
                "data": result
            }

        # Ensure data is a dictionary
        if not isinstance(result["data"], dict):
            result["data"] = {}

        # Ensure action exists and is a dictionary
        if "action" not in result["data"]:
            result["data"]["action"] = {}
        elif not isinstance(result["data"]["action"], dict):
            result["data"]["action"] = {}

        # Ensure details exists and is a dictionary
        if "details" not in result["data"]["action"]:
            result["data"]["action"]["details"] = {}
        elif not isinstance(result["data"]["action"]["details"], dict):
            result["data"]["action"]["details"] = {}

        return result

    def update_state(
        self, state: dict, update_from, stage=None, option=None, direction=None
    ):
        """Update user state with proper Redis management"""
        # Ensure we have a valid state object
        if not isinstance(state, dict):
            state = {}

        # Create a copy to avoid modifying the input
        new_state = state.copy()

        # Preserve existing state data
        for key, value in self.state.items():
            if key not in new_state:
                new_state[key] = value

        # Ensure profile structure exists and preserve existing data
        if "profile" in new_state:
            new_state["profile"] = self._ensure_profile_structure(new_state["profile"])
        else:
            # If no profile exists, try to preserve existing profile from current state
            if "profile" in self.state:
                new_state["profile"] = self._ensure_profile_structure(self.state["profile"])
            else:
                new_state["profile"] = {
                    "data": {
                        "action": {},
                        "details": {}
                    }
                }

        # Update stage and option in state object
        if stage:
            new_state["stage"] = stage
        if option:
            new_state["option"] = option
        if direction:
            new_state["direction"] = direction

        # Always preserve JWT token if it exists
        if self.jwt_token:
            new_state["jwt_token"] = self.jwt_token
            # Refresh JWT token expiry
            state_redis.setex(f"{self.user.mobile_number}_jwt_token", ABSOLUTE_JWT_TTL, self.jwt_token)

        # Preserve JWT token in flow data if it exists
        if self.jwt_token and "flow_data" in new_state:
            if isinstance(new_state["flow_data"], dict) and "data" in new_state["flow_data"]:
                new_state["flow_data"]["data"]["jwt_token"] = self.jwt_token

        # Convert state to JSON string
        state_json = json.dumps(new_state)

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
        self.state = new_state

    def get_state(self, user):
        """Get current state with proper Redis handling"""
        state_json = state_redis.get(f"{user.mobile_number}")
        if state_json is None:
            # Initialize with proper structure
            state = {
                "stage": "handle_action_menu",
                "option": None,
                "direction": "OUT",
                "profile": {
                    "data": {
                        "action": {},
                        "details": {}
                    }
                },
                "current_account": None,
                "flow_data": None
            }
            # Add JWT token if it exists
            if self.jwt_token:
                state["jwt_token"] = self.jwt_token

            state_redis.setex(f"{user.mobile_number}", ACTIVITY_TTL, json.dumps(state))
            return state
        else:
            try:
                state = json.loads(state_json)
                # Ensure profile structure exists while preserving data
                if "profile" in state:
                    state["profile"] = self._ensure_profile_structure(state["profile"])
                else:
                    # If no profile exists, try to preserve existing profile from current state
                    if hasattr(self, 'state') and "profile" in self.state:
                        state["profile"] = self._ensure_profile_structure(self.state["profile"])
                    else:
                        state["profile"] = {
                            "data": {
                                "action": {},
                                "details": {}
                            }
                        }

                # Add JWT token if it exists
                if self.jwt_token:
                    state["jwt_token"] = self.jwt_token

                state_redis.setex(f"{user.mobile_number}", ACTIVITY_TTL, json.dumps(state))
                return state
            except json.JSONDecodeError:
                state = {
                    "stage": "handle_action_menu",
                    "option": None,
                    "direction": "OUT",
                    "profile": {
                        "data": {
                            "action": {},
                            "details": {}
                        }
                    },
                    "current_account": None,
                    "flow_data": None
                }
                # Add JWT token if it exists
                if self.jwt_token:
                    state["jwt_token"] = self.jwt_token

                state_redis.setex(f"{user.mobile_number}", ACTIVITY_TTL, json.dumps(state))
                return state

    def set_jwt_token(self, jwt_token):
        """Set JWT token with proper Redis handling"""
        if jwt_token:
            # Store token with absolute expiration
            state_redis.setex(f"{self.user.mobile_number}_jwt_token", ABSOLUTE_JWT_TTL, jwt_token)
            self.jwt_token = jwt_token

            # Update state with token
            current_state = self.state.copy()
            current_state["jwt_token"] = jwt_token

            # Update flow data with token if it exists
            if "flow_data" in current_state:
                if isinstance(current_state["flow_data"], dict) and "data" in current_state["flow_data"]:
                    current_state["flow_data"]["data"]["jwt_token"] = jwt_token

            self.update_state(current_state, "set_jwt_token")

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
            "direction": "OUT",
            "profile": {
                "data": {
                    "action": {},
                    "details": {}
                }
            },
            "current_account": None,
            "flow_data": None
        }

        # Preserve JWT token if still valid
        if preserve_jwt:
            initial_state["jwt_token"] = current_jwt
            # Refresh JWT token expiry
            state_redis.setex(f"{self.user.mobile_number}_jwt_token", ABSOLUTE_JWT_TTL, current_jwt)

        state_redis.setex(f"{self.user.mobile_number}", ACTIVITY_TTL, json.dumps(initial_state))
        state_redis.setex(f"{self.user.mobile_number}_stage", ACTIVITY_TTL, "handle_action_menu")
        state_redis.setex(f"{self.user.mobile_number}_direction", ACTIVITY_TTL, "OUT")

        # Update instance variables
        self.state = initial_state
        self.stage = initial_state["stage"]
        self.option = initial_state["option"]
        self.direction = initial_state["direction"]

        # Restore JWT token if still valid
        if preserve_jwt:
            self.jwt_token = current_jwt

    def __getattr__(self, name):
        """Handle attribute access for state data"""
        if name in self.state:
            return self.state[name]
        raise AttributeError(f"'CachedUserState' object has no attribute '{name}'")


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
