"""Simple state data management"""
from typing import Dict, Any, Set


class StateData:
    """Manages state data preservation"""

    # Critical fields that should be preserved during updates
    CRITICAL_FIELDS: Set[str] = {
        "jwt_token",
        "profile",
        "current_account",
        "member"
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
        """Create empty state"""
        return {}

    @classmethod
    def merge(cls, current: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """Merge states preserving critical fields"""
        result = current.copy()
        result.update(new)
        return cls.preserve(current, result)
