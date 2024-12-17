"""State data structure and preservation"""
from typing import Dict, Any, Set


class StateData:
    """Manages state data structure and critical field preservation"""

    # Critical fields that must be preserved during state updates
    CRITICAL_FIELDS: Set[str] = {
        "jwt_token",
        "profile",
        "current_account",
        "member",
        "authorizer_member_id",
        "issuer_member_id",
        "sender_account",
        "sender_account_id"
    }

    @classmethod
    def preserve(cls, current: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """Preserve critical fields when updating state"""
        result = new.copy()

        # Preserve critical fields from current state if not in new state
        for field in cls.CRITICAL_FIELDS:
            if field in current and field not in new:
                result[field] = current[field]

        return result

    @staticmethod
    def create_default() -> Dict[str, Any]:
        """Create default state structure"""
        return {
            "stage": "INIT",
            "data": {},
            "profile": {}
        }

    @classmethod
    def validate(cls, state: Dict[str, Any]) -> bool:
        """Validate state structure"""
        if not isinstance(state, dict):
            return False

        # Check required fields
        if "stage" not in state or "data" not in state:
            return False

        # Validate field types
        if not isinstance(state["stage"], str):
            return False
        if not isinstance(state["data"], dict):
            return False
        if "profile" in state and not isinstance(state["profile"], dict):
            return False

        return True

    @classmethod
    def merge(cls, current: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """Merge new state with current state, preserving critical fields"""
        result = current.copy()
        result.update(new)  # Update with new data
        return cls.preserve(current, result)  # Ensure critical fields are preserved
