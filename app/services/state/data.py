"""Simple state data management"""
from typing import Dict, Any, Set


class StateData:
    """Manages state data preservation"""

    # Critical fields that should be preserved during updates
    CRITICAL_FIELDS: Set[str] = {
        "jwt_token",
        "profile",
        "current_account",
        "member",
        "flow_data",  # Added to preserve flow state
        "authenticated",  # Added for completeness
        "member_id",  # Added for member identification
        "account_id"  # Added for account identification
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

        # Special handling for flow_data to ensure complete preservation
        if "flow_data" in new and "flow_data" in current:
            # Merge flow data preserving all fields
            result["flow_data"] = {
                **(current.get("flow_data", {}) or {}),
                **(new.get("flow_data", {}) or {})
            }
            # Remove flow_data from new to prevent overwrite in update
            new = {k: v for k, v in new.items() if k != "flow_data"}

        result.update(new)
        return cls.preserve(current, result)
