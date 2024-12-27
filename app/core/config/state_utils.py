"""Core state utilities enforcing SINGLE SOURCE OF TRUTH"""
from typing import Any, Dict


def create_initial_state() -> Dict[str, Any]:
    """Create minimal initial state structure"""
    return {
        # Core identity (SINGLE SOURCE OF TRUTH)
        "member_id": None,
        "channel": {
            "type": "whatsapp",
            "identifier": None,
            "metadata": {}
        },
        # Authentication (SINGLE SOURCE OF TRUTH)
        "jwt_token": None,
        # Essential state
        "flow_data": None
    }


def prepare_state_update(current_state: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update state preserving SINGLE SOURCE OF TRUTH"""
    if not isinstance(current_state, dict):
        raise ValueError("Current state must be a dictionary")
    if not isinstance(updates, dict):
        raise ValueError("Updates must be a dictionary")

    # Create new state (without copying to prevent duplication)
    new_state = {}

    # Handle critical fields first (SINGLE SOURCE OF TRUTH)
    for field in ["member_id", "jwt_token"]:
        new_state[field] = updates.get(field) if field in updates else current_state.get(field)

    # Handle channel updates (SINGLE SOURCE OF TRUTH)
    if "channel" in updates:
        if not isinstance(updates["channel"], dict):
            raise ValueError("Channel must be a dictionary")

        new_state["channel"] = {
            "type": updates["channel"].get("type", current_state.get("channel", {}).get("type", "whatsapp")),
            "identifier": updates["channel"].get("identifier", current_state.get("channel", {}).get("identifier")),
            "metadata": updates["channel"].get("metadata", {}) if "metadata" in updates["channel"] else current_state.get("channel", {}).get("metadata", {})
        }
    else:
        new_state["channel"] = {
            "type": current_state.get("channel", {}).get("type", "whatsapp"),
            "identifier": current_state.get("channel", {}).get("identifier"),
            "metadata": current_state.get("channel", {}).get("metadata", {})
        }

    # Handle other updates (non-critical fields)
    for field, value in updates.items():
        if field not in ["member_id", "channel", "jwt_token"]:
            new_state[field] = value

    # Copy over any remaining fields from current state
    for field, value in current_state.items():
        if field not in new_state and field not in ["member_id", "channel", "jwt_token"]:
            new_state[field] = value

    return new_state


def update_critical_fields(current_state: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update critical fields while enforcing SINGLE SOURCE OF TRUTH"""
    if not isinstance(current_state, dict):
        raise ValueError("Current state must be a dictionary")
    if not isinstance(updates, dict):
        raise ValueError("Updates must be a dictionary")

    # Create new state (without copying to prevent duplication)
    new_state = {}

    # Update critical fields (SINGLE SOURCE OF TRUTH)
    for field in ["member_id", "jwt_token"]:
        new_state[field] = updates.get(field) if field in updates else current_state.get(field)

    # Handle channel updates (SINGLE SOURCE OF TRUTH)
    if "channel" in updates:
        if not isinstance(updates["channel"], dict):
            raise ValueError("Channel must be a dictionary")

        new_state["channel"] = {
            "type": updates["channel"].get("type", current_state.get("channel", {}).get("type", "whatsapp")),
            "identifier": updates["channel"].get("identifier", current_state.get("channel", {}).get("identifier")),
            "metadata": current_state.get("channel", {}).get("metadata", {})  # Metadata not updated in critical fields
        }
    else:
        new_state["channel"] = {
            "type": current_state.get("channel", {}).get("type", "whatsapp"),
            "identifier": current_state.get("channel", {}).get("identifier"),
            "metadata": current_state.get("channel", {}).get("metadata", {})
        }

    return new_state
