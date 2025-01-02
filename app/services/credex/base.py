"""Base CredEx functionality using pure functions"""
from typing import Any, Dict

import requests
from core.utils.error_handler import error_decorator
from core.utils.exceptions import APIException

from .config import CredExConfig, CredExEndpoints


@error_decorator
def make_credex_request(
    group: str,
    action: str,
    payload: Dict[str, Any] = None,
    state_manager: Any = None,
    method: str = "POST"
) -> Dict[str, Any]:
    """Make an HTTP request to the CredEx API using endpoint groups"""
    # Get endpoint info
    path = CredExEndpoints.get_path(group, action)
    # Build request
    config = CredExConfig.from_env()
    url = config.get_url(path)
    headers = config.get_headers()

    # Check if endpoint requires authentication
    if CredExEndpoints.requires_auth(group, action):
        # Get token directly from state (SINGLE SOURCE OF TRUTH)
        jwt_token = state_manager.get("jwt_token")
        if not jwt_token:
            raise APIException("Authentication required for this endpoint")
        headers["Authorization"] = f"Bearer {jwt_token}"

    # For auth endpoints, get channel info directly (SINGLE SOURCE OF TRUTH)
    if group == 'auth' and action == 'login':
        channel = state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            raise APIException("Channel identifier required for authentication")
        payload = {"phone": channel["identifier"]}

    # Get current flow state
    flow_data = state_manager.get("flow_data") or {}

    # Update flow state preserving flow type and step
    state_manager.update_state({
        "flow_data": {
            "flow_type": flow_data.get("flow_type"),  # Preserve flow type
            "step": flow_data.get("step", 0),         # Preserve step number
            "current_step": flow_data.get("current_step"),  # Preserve step name
            "type": "api_request",  # Add request info
            "data": {
                "group": group,
                "action": action,
                "payload": payload,
                **(flow_data.get("data", {}))  # Preserve existing data
            }
        }
    })

    try:
        # Make request
        response = requests.request(method, url, headers=headers, json=payload)

        # Handle API errors
        if not response.ok:
            try:
                error_data = {
                    "status_code": response.status_code,
                    "response": response.json()
                }
            except ValueError:
                error_data = {
                    "status_code": response.status_code,
                    "response": response.text
                }
            raise APIException(
                f"API request failed: {response.status_code}",
                error_data
            )

        # Return response data
        return response.json()

    except requests.exceptions.RequestException as e:
        # Handle network errors
        error_data = {"url": url, "error": str(e)}
        raise APIException(
            f"Connection error: {str(e)}",
            error_data
        )
