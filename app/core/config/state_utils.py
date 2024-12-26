"""Utility functions for state management"""
from typing import Any, Dict

from core.utils.state_validator import StateValidator


def create_initial_state() -> Dict[str, Any]:
    """Create initial state with proper structure"""
    base_state = {
        "jwt_token": None,
        "profile": StateValidator.ensure_profile_structure({}),
        "current_account": {},
        "flow_data": None,
        "member_id": None,
        "account_id": None,
        "authenticated": False,
        "channel": {
            "type": "whatsapp",
            "identifier": None,  # Will be set when user connects
            "metadata": {}
        },
        "_validation_context": {},
        "_validation_state": {},
        "_previous_state": {}
    }
    return StateValidator.ensure_validation_context(base_state)


def prepare_state_update(current_state: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare state update preserving validation context"""
    new_state = current_state.copy()
    new_state.update(updates)
    new_state["_previous_state"] = current_state.copy()
    new_state["_previous_state"].pop("_previous_state", None)
    return StateValidator.ensure_validation_context(new_state)


def update_critical_fields(state: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update critical fields with priority handling"""
    critical_fields = ["jwt_token", "member_id", "account_id", "authenticated", "channel"]
    for field in critical_fields:
        if updates.get(field) is not None:
            if field == "channel" and isinstance(updates[field], dict):
                # Update channel fields individually to preserve structure
                if not isinstance(state.get("channel"), dict):
                    state["channel"] = {
                        "type": "whatsapp",
                        "identifier": None,
                        "metadata": {}
                    }
                for k, v in updates["channel"].items():
                    if k in ["type", "identifier", "metadata"]:
                        state["channel"][k] = v
            else:
                state[field] = updates[field]
    return state
