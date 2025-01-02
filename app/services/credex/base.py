"""Base CredEx functionality using pure functions"""
from typing import Any, Dict

import requests
from core.utils.error_handler import ErrorHandler

from .config import CredExConfig, CredExEndpoints


def make_credex_request(
    group: str,
    action: str,
    payload: Dict[str, Any] = None,
    state_manager: Any = None,
    method: str = "POST"
) -> Dict[str, Any]:
    """Make an HTTP request to the CredEx API using endpoint groups"""
    try:
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
                return ErrorHandler.handle_system_error(
                    code="AUTH_REQUIRED",
                    service="credex",
                    action=f"{method}_{path}",
                    message="Authentication required for this endpoint"
                )
            headers["Authorization"] = f"Bearer {jwt_token}"

        # For auth endpoints, get channel info directly (SINGLE SOURCE OF TRUTH)
        if group == 'auth' and action == 'login':
            channel = state_manager.get("channel")
            if not channel or not channel.get("identifier"):
                return ErrorHandler.handle_system_error(
                    code="CHANNEL_REQUIRED",
                    service="credex",
                    action="login",
                    message="Channel identifier required for authentication"
                )
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
                return ErrorHandler.handle_system_error(
                    code="API_ERROR",
                    service="credex",
                    action=f"{method}_{path}",
                    message=f"API request failed: {response.status_code}",
                    details={
                        "status_code": response.status_code,
                        "response": response.json() if response.headers.get("content-type") == "application/json" else response.text
                    }
                )

            # Return response data
            return response.json()

        except requests.exceptions.RequestException as e:
            # Handle network errors
            return ErrorHandler.handle_system_error(
                code="CONNECTION_ERROR",
                service="credex",
                action=f"{method}_{path}",
                message=f"Connection error: {str(e)}",
                details={"url": url}
            )

    except Exception as e:
        # Handle unexpected errors
        return ErrorHandler.handle_system_error(
            code="REQUEST_ERROR",
            service="credex",
            action=f"{group}_{action}",
            message=str(e)
        )
