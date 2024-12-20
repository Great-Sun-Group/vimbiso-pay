"""Simple state data management"""
import logging
from typing import Dict, Any, Set

logger = logging.getLogger(__name__)


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
        logger.debug("Starting state merge:")
        logger.debug(f"Current state: {current}")
        logger.debug(f"New state: {new}")

        result = current.copy()

        # Special handling for flow_data to ensure complete preservation
        if "flow_data" in new and "flow_data" in current:
            current_flow = current.get("flow_data", {}) or {}
            new_flow = new.get("flow_data", {}) or {}

            logger.debug("Merging flow data:")
            logger.debug(f"Current flow data: {current_flow}")
            logger.debug(f"New flow data: {new_flow}")

            # Deep merge of flow data
            merged_flow = {**current_flow}

            # Special handling for nested data field
            if "data" in new_flow and "data" in current_flow:
                logger.debug("Merging nested data field:")
                logger.debug(f"Current data: {current_flow.get('data', {})}")
                logger.debug(f"New data: {new_flow.get('data', {})}")

                merged_flow["data"] = {
                    **(current_flow.get("data", {}) or {}),
                    **(new_flow.get("data", {}) or {})
                }

                logger.debug(f"Merged data result: {merged_flow['data']}")
            else:
                # If data field is only in one of them, use that one
                merged_flow["data"] = new_flow.get("data", current_flow.get("data", {}))
                logger.debug(f"Using single data source: {merged_flow['data']}")

            # Merge other flow fields
            for key, value in new_flow.items():
                if key != "data":
                    merged_flow[key] = value
                    logger.debug(f"Merged flow field {key}: {value}")

            result["flow_data"] = merged_flow
            logger.debug(f"Final merged flow data: {merged_flow}")

            # Remove flow_data from new to prevent overwrite in update
            new = {k: v for k, v in new.items() if k != "flow_data"}

        result.update(new)
        return cls.preserve(current, result)
