"""Core state utilities enforcing SINGLE SOURCE OF TRUTH"""
from typing import Any, Dict


def merge_updates(current_state: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Merge updates with current state without transformation"""
    if not isinstance(current_state, dict) or not isinstance(updates, dict):
        raise ValueError("Both current state and updates must be dictionaries")

    # Let StateManager handle validation
    merged = current_state.copy()
    merged.update(updates)
    return merged


def get_channel_info(state: Dict[str, Any]) -> Dict[str, Any]:
    """Get channel info without transformation"""
    if not isinstance(state, dict):
        raise ValueError("State must be a dictionary")

    # Return channel info directly
    channel = state.get("channel", {})
    if not isinstance(channel, dict):
        raise ValueError("Channel must be a dictionary")

    return channel
