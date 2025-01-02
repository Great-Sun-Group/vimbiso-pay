"""Centralized error handling with clear boundaries

This module provides the ONLY error handling for the entire system.
All errors are handled through the ErrorHandler class.

Error Types:
- component: Component-level validation errors
- flow: Flow-level business logic errors
- system: System-level technical errors

Each error type has a specific structure and boundary.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Central error handling with clear boundaries"""

    @classmethod
    def handle_error(
        cls,
        error_type: str,
        message: str,
        details: Optional[Dict] = None
    ) -> Dict:
        """Handle any error type with standard format"""
        error = {
            "type": error_type,
            "message": message,
            "details": details or {}
        }

        # Log error
        logger.error(
            f"Error handled: {error_type}",
            extra={
                "error": error,
                "details": details
            }
        )

        return {"error": error}

    @classmethod
    def handle_component_error(
        cls,
        component: str,
        field: str,
        value: Any,
        message: str
    ) -> Dict:
        """Handle component validation error"""
        return cls.handle_error(
            error_type="component",
            message=message,
            details={
                "component": component,
                "field": field,
                "value": value
            }
        )

    @classmethod
    def handle_flow_error(
        cls,
        step: str,
        action: str,
        data: Dict,
        message: str
    ) -> Dict:
        """Handle flow business logic error"""
        return cls.handle_error(
            error_type="flow",
            message=message,
            details={
                "step": step,
                "action": action,
                "data": data
            }
        )

    @classmethod
    def handle_system_error(
        cls,
        code: str,
        service: str,
        action: str,
        message: str
    ) -> Dict:
        """Handle system technical error"""
        return cls.handle_error(
            error_type="system",
            message=message,
            details={
                "code": code,
                "service": service,
                "action": action
            }
        )

    # Standard error messages
    MESSAGES = {
        "component": {
            "invalid_amount": "Amount must be positive",
            "invalid_format": "Invalid amount format",
            "invalid_handle": "Handle must be text",
            "missing_handle": "Handle required",
            "invalid_selection": "Invalid selection",
            "invalid_confirm": "Confirmation must be boolean"
        },
        "flow": {
            "invalid_step": "Invalid step in flow",
            "invalid_action": "Invalid action for step",
            "missing_data": "Required data missing",
            "invalid_state": "Invalid flow state"
        },
        "system": {
            "service_error": "Service unavailable",
            "config_error": "Configuration error",
            "api_error": "API error",
            "unknown_error": "Unknown error occurred"
        }
    }


def error_decorator(f):
    """Decorator for standardized error handling"""
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            return ErrorHandler.handle_system_error(
                code="RUNTIME_ERROR",
                service=f.__module__,
                action=f.__name__,
                message=str(e)
            )
    return wrapper
