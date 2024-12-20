"""Simple state data management"""
import logging
from typing import Dict, Any, Set, Tuple, Optional

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
                current_value = current[field]
                # Only preserve non-None values
                if current_value is not None:
                    result[field] = current_value
                    logger.debug(f"Preserved critical field {field}: {current_value}")

        return result

    @staticmethod
    def create_default() -> Dict[str, Any]:
        """Create empty state with initialized critical fields"""
        return {
            "flow_data": None,
            "profile": {},
            "current_account": None,
            "jwt_token": None,
            "authenticated": False,
            "member_id": None,
            "account_id": None
        }

    @classmethod
    def cleanup_state(cls, current: Dict[str, Any], preserve_fields: Optional[Set[str]] = None) -> Tuple[bool, Optional[str]]:
        """Clean up state while preserving specified fields"""
        try:
            # Start with default state
            clean_state = cls.create_default()

            # If preserve_fields provided, keep those values from current state
            if preserve_fields:
                for field in preserve_fields:
                    if field in current and current[field] is not None:
                        clean_state[field] = current[field]
                        logger.debug(f"Preserved field during cleanup: {field}")

            logger.debug(f"State cleanup result: {clean_state}")
            return True, None
        except Exception as e:
            logger.error(f"State cleanup error: {str(e)}")
            return False, str(e)

    @classmethod
    def merge(cls, current: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """Merge states preserving critical fields"""
        logger.debug("Starting state merge:")
        logger.debug(f"Current state: {current}")
        logger.debug(f"New state: {new}")

        result = current.copy()

        # Special handling for flow_data to ensure complete preservation
        if "flow_data" in new:
            current_flow = current.get("flow_data", {}) or {}
            new_flow = new.get("flow_data", {}) or {}

            if new_flow is None:
                # If new flow_data is None, it means we want to clear the flow
                result["flow_data"] = None
                logger.debug("Clearing flow data")
            else:
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

                    # Ensure we're working with non-None values
                    current_data = current_flow.get("data", {}) or {}
                    new_data = new_flow.get("data", {}) or {}

                    merged_flow["data"] = {**current_data, **new_data}
                    logger.debug(f"Merged data result: {merged_flow['data']}")
                else:
                    # If data field is only in one of them, use that one
                    merged_flow["data"] = new_flow.get("data", current_flow.get("data", {}))
                    logger.debug(f"Using single data source: {merged_flow['data']}")

                # Special handling for _previous_data
                if "_previous_data" in new_flow:
                    merged_flow["_previous_data"] = new_flow["_previous_data"]
                    logger.debug(f"Preserved previous data: {merged_flow['_previous_data']}")

                # Merge other flow fields
                for key, value in new_flow.items():
                    if key not in {"data", "_previous_data"}:
                        merged_flow[key] = value
                        logger.debug(f"Merged flow field {key}: {value}")

                result["flow_data"] = merged_flow
                logger.debug(f"Final merged flow data: {merged_flow}")

            # Remove flow_data from new to prevent double processing
            new = {k: v for k, v in new.items() if k != "flow_data"}

        # Update remaining fields
        for key, value in new.items():
            if value is not None:  # Only update with non-None values
                result[key] = value
                logger.debug(f"Updated field {key}: {value}")

        # Ensure critical fields are preserved
        final_result = cls.preserve(current, result)
        logger.debug(f"Final merged state: {final_result}")
