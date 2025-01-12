"""API response management

This module handles state updates from API responses. All API responses contain both
dashboard and action sections that flow through here.

The state updates are protected by schema validation:
- dashboard: Member state after operation (accounts, profile, etc.)
- action: Operation results and details
- auth: Authentication state when token present

Components can still store their own unvalidated data in component_data.data.
"""

import logging
from typing import Any, Dict, Optional, Tuple

from core.state.interface import StateManagerInterface

logger = logging.getLogger(__name__)


def update_state_from_response(
    api_response: Dict[str, Any],
    state_manager: StateManagerInterface
) -> Tuple[bool, Optional[str]]:
    """Store API response in state

    Simple storage of API response data:
    - No validation
    - No transformation
    - Components handle their own validation/transformation

    Args:
        api_response: API response to store
        state_manager: State manager instance

    Returns:
        Tuple[bool, Optional[str]]: Success flag and optional error message
    """
    try:
        # Get data section
        data = api_response.get("data", {})

        # Store sections that exist
        state_update = {}
        if "dashboard" in data:
            state_update["dashboard"] = data["dashboard"]
        if "action" in data:
            state_update["action"] = data["action"]
            # Extract auth token if present
            if data["action"].get("details", {}).get("token"):
                state_update["auth"] = {
                    "token": data["action"]["details"]["token"]
                }

        # Update state
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Storing API response in state")
        state_manager.update_state(state_update)
        return True, None

    except Exception as e:
        logger.error(f"Failed to store API response: {e}")
        return False, str(e)
