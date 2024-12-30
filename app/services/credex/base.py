"""Base CredEx functionality using pure functions"""
from typing import Any, Dict

import requests
from core.utils.error_handler import error_decorator

from .config import CredExConfig, CredExEndpoints


@error_decorator
def make_credex_request(
    group: str,
    action: str,
    method: str = "POST",
    payload: Dict[str, Any] = None,
    state_manager: Any = None
) -> requests.Response:
    """Make an HTTP request to the CredEx API using endpoint groups"""
    # Get endpoint info
    path = CredExEndpoints.get_path(group, action)

    # Let StateManager validate through flow state update
    state_manager.update_state({
        "flow_data": {
            "flow_type": group,  # StateManager validates auth requirements
            "step": 1,
            "current_step": action,
            "data": {
                "request": {
                    "method": method,
                    "payload": payload
                }
            }
        }
    })

    # Build request
    config = CredExConfig.from_env()
    url = config.get_url(path)
    headers = config.get_headers()

    # Add token from validated state
    jwt_token = state_manager.get("jwt_token")
    if jwt_token:
        headers["Authorization"] = f"Bearer {jwt_token}"

    # Make request
    response = requests.request(method, url, headers=headers, json=payload)

    # Let StateManager validate through flow advance
    state_manager.update_state({
        "flow_data": {
            "next_step": "complete",
            "data": {
                "response": {
                    "status_code": response.status_code,
                    "content_type": response.headers.get("Content-Type"),
                    "body": response.text
                }
            }
        }
    })

    return response
