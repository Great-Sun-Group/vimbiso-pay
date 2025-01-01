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

    # Let StateManager validate auth through update
    state_manager.update_state({
        "validation": {
            "type": "auth",
            "group": group,
            "action": action
        }
    })

    # Get validated auth data
    auth_data = state_manager.get_auth_data()
    if auth_data.get("token"):
        headers["Authorization"] = f"Bearer {auth_data['token']}"

    # For auth endpoints, let StateManager validate channel
    if group == 'auth' and action == 'login':
        state_manager.update_state({
            "validation": {
                "type": "channel",
                "required": True
            }
        })
        # Get validated channel data
        channel_data = state_manager.get_channel_data()
        payload = {"phone": channel_data["identifier"]}

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
