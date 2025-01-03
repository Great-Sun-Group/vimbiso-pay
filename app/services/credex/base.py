"""Base CredEx functionality using pure functions"""
from typing import Any, Dict

import requests
from core.utils.error_handler import ErrorHandler
from datetime import datetime

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
            # Update state with auth request
            state_manager.update_state({
                "flow_data": {
                    "type": "auth_request",
                    "data": {
                        "endpoint": f"{method}_{path}"
                    }
                }
            })

            # Let StateManager validate auth through update
            try:
                channel_id = state_manager.get_channel_id()
                headers["Authorization"] = f"Bearer {state_manager.get_flow_data().get('auth', {}).get('token')}"
            except Exception as e:
                return ErrorHandler.handle_system_error(
                    code="AUTH_REQUIRED",
                    service="credex",
                    action=f"{method}_{path}",
                    message=str(e)
                )

        # For auth endpoints, get channel info through state manager
        if group == 'auth' and action == 'login':
            try:
                channel_id = state_manager.get_channel_id()
                payload = {"phone": channel_id}
            except Exception as e:
                return ErrorHandler.handle_system_error(
                    code="CHANNEL_REQUIRED",
                    service="credex",
                    action="login",
                    message=str(e)
                )

        # Get current flow state for validation tracking
        flow_state = state_manager.get_flow_state() or {}
        current_validation = flow_state.get("validation", {})
        current_step_index = flow_state.get("step_index", 0)
        total_steps = flow_state.get("total_steps", 1)

        # Create standardized validation state
        validation_state = {
            "in_progress": True,
            "attempts": current_validation.get("attempts", 0) + 1,
            "last_attempt": {
                "group": group,
                "action": action,
                "payload": payload,
                "timestamp": datetime.utcnow().isoformat()
            },
            "operation": "api_request",
            "component": "credex",
            "timestamp": datetime.utcnow().isoformat()
        }

        # Update flow state with validation tracking
        state_manager.update_state({
            "flow_data": {
                "flow_type": flow_state.get("flow_type"),
                "step": flow_state.get("step"),
                "step_index": current_step_index,
                "total_steps": total_steps,
                "handler_type": "credex",
                "active_component": {
                    "type": "api_request",
                    "validation": validation_state
                },
                "data": {
                    **flow_state.get("data", {}),
                    "request": {
                        "group": group,
                        "action": action,
                        "payload": payload,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            }
        })

        try:
            # Make request
            response = requests.request(method, url, headers=headers, json=payload)

            # Handle API errors with validation tracking
            if not response.ok:
                validation_state.update({
                    "in_progress": False,
                    "error": {
                        "code": "API_ERROR",
                        "status_code": response.status_code,
                        "message": f"API request failed: {response.status_code}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                })

                return ErrorHandler.handle_system_error(
                    code="API_ERROR",
                    service="credex",
                    action=f"{method}_{path}",
                    message=f"API request failed: {response.status_code}",
                    details={
                        "status_code": response.status_code,
                        "response": response.json() if response.headers.get("content-type") == "application/json" else response.text
                    },
                    validation_state=validation_state
                )

            # Update validation state for success
            validation_state.update({
                "in_progress": False,
                "error": None,
                "timestamp": datetime.utcnow().isoformat()
            })

            # Update flow state with success
            state_manager.update_state({
                "flow_data": {
                    "active_component": {
                        "type": "api_request",
                        "validation": validation_state
                    }
                }
            })

            # Return response data with validation
            response_data = response.json()
            response_data["_validation"] = validation_state
            return response_data

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
