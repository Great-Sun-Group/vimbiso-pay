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
        current_state = {}
    if not isinstance(updates, dict):
        raise ValueError("Updates must be a dictionary")

    # Start with current state
    new_state = current_state.copy()

    # Handle member_id (SINGLE SOURCE OF TRUTH)
    if "member_id" in updates:
        new_state["member_id"] = updates["member_id"]

    # Handle channel updates (SINGLE SOURCE OF TRUTH)
    if "channel" in updates:
        if not isinstance(updates["channel"], dict):
            raise ValueError("Channel must be a dictionary")
        if "channel" not in new_state:
            new_state["channel"] = {"type": "whatsapp", "identifier": None, "metadata": {}}
        for field in ["type", "identifier"]:
            if field in updates["channel"]:
                new_state["channel"][field] = updates["channel"][field]
        # Handle metadata updates
        if "metadata" in updates["channel"]:
            if not isinstance(updates["channel"]["metadata"], dict):
                raise ValueError("Channel metadata must be a dictionary")
            new_state["channel"]["metadata"].update(updates["channel"]["metadata"])

    # Handle jwt_token (SINGLE SOURCE OF TRUTH)
    if "jwt_token" in updates:
        new_state["jwt_token"] = updates["jwt_token"]

    # Handle other updates
    for field, value in updates.items():
        if field not in ["member_id", "channel", "jwt_token"]:
            new_state[field] = value

    return new_state


def update_critical_fields(current_state: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update critical fields while enforcing SINGLE SOURCE OF TRUTH"""
    if not isinstance(current_state, dict):
        current_state = {}
    if not isinstance(updates, dict):
        raise ValueError("Updates must be a dictionary")

    new_state = current_state.copy()

    # Update critical fields (SINGLE SOURCE OF TRUTH)
    critical_fields = {
        "member_id",    # Primary identifier
        "jwt_token"     # Authentication token
    }

    for field in critical_fields:
        if field in updates:
            new_state[field] = updates[field]

    # Handle channel updates
    if "channel" in updates:
        if not isinstance(updates["channel"], dict):
            raise ValueError("Channel must be a dictionary")
        if "channel" not in new_state:
            new_state["channel"] = {"type": "whatsapp", "identifier": None, "metadata": {}}
        for field in ["type", "identifier"]:
            if field in updates["channel"]:
                new_state["channel"][field] = updates["channel"][field]

    return new_state
