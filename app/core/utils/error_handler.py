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
import traceback
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Central error handling with clear boundaries"""

    @classmethod
    def _create_error_response(
        cls,
        error_type: str,
        message: str,
        details: Dict,
        context: Optional[Dict] = None
    ) -> Dict:
        """Create standardized error response with context

        Args:
            error_type: Type of error (component, flow, system)
            message: Error message
            details: Error details
            context: Optional execution context

        Returns:
            Dict with standardized error structure
        """
        error = {
            "type": error_type,
            "message": message,
            "details": details,
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat()
        }

        # Log error with context
        logger.error(
            f"Error handled: {error_type}",
            extra={
                "error": error,
                "details": details,
                "context": context
            }
        )

        return {"error": error}

    @classmethod
    def handle_component_error(
        cls,
        component: str,
        field: str,
        value: Any,
        message: str,
        validation_state: Optional[Dict] = None
    ) -> Dict:
        """Handle component validation error with tracking

        Args:
            component: Component type
            field: Field with error
            value: Invalid value
            message: Error message
            validation_state: Optional validation state for tracking

        Returns:
            Dict with standardized error structure
        """
        details = {
            "component": component,
            "field": field,
            "value": str(value),
            "validation": validation_state or {}
        }

        # Add validation tracking if available
        if validation_state:
            details["validation"].update({
                "attempts": validation_state.get("attempts", 0),
                "last_attempt": validation_state.get("last_attempt")
            })

        return cls._create_error_response(
            error_type="component",
            message=message,
            details=details,
            context={
                "validation_state": validation_state
            }
        )

    @classmethod
    def handle_flow_error(
        cls,
        step: str,
        action: str,
        data: Dict,
        message: str,
        flow_state: Optional[Dict] = None
    ) -> Dict:
        """Handle flow business logic error with state tracking

        Args:
            step: Current flow step
            action: Action being performed
            data: Flow data
            message: Error message
            flow_state: Optional flow state for tracking

        Returns:
            Dict with standardized error structure
        """
        details = {
            "step": step,
            "action": action,
            "data": data
        }

        # Add flow tracking if available
        if flow_state:
            details.update({
                "step_index": flow_state.get("step_index"),
                "total_steps": flow_state.get("total_steps"),
                "handler_type": flow_state.get("handler_type")
            })

        return cls._create_error_response(
            error_type="flow",
            message=message,
            details=details,
            context={
                "flow_state": flow_state
            }
        )

    @classmethod
    def handle_system_error(
        cls,
        code: str,
        service: str,
        action: str,
        message: str,
        error: Optional[Exception] = None
    ) -> Dict:
        """Handle system technical error with error tracking

        Args:
            code: Error code
            service: Service name
            action: Action being performed
            message: Error message
            error: Optional exception for tracking

        Returns:
            Dict with standardized error structure
        """
        details = {
            "code": code,
            "service": service,
            "action": action
        }

        # Add error details if available
        if error:
            details.update({
                "error_type": error.__class__.__name__,
                "error_args": getattr(error, 'args', []),
                "error_message": str(error)
            })

        return cls._create_error_response(
            error_type="system",
            message=message,
            details=details,
            context={
                "exception": repr(error) if error else None,
                "traceback": traceback.format_exc() if error else None
            }
        )

    # Standard error messages with context
    MESSAGES = {
        "component": {
            "invalid_amount": {
                "message": "Amount must be positive",
                "details": {"validation": "amount_positive"}
            },
            "invalid_format": {
                "message": "Invalid amount format",
                "details": {"validation": "amount_format"}
            },
            "invalid_handle": {
                "message": "Handle must be text",
                "details": {"validation": "handle_type"}
            },
            "missing_handle": {
                "message": "Handle required",
                "details": {"validation": "handle_required"}
            },
            "invalid_selection": {
                "message": "Invalid selection",
                "details": {"validation": "selection_invalid"}
            },
            "invalid_confirm": {
                "message": "Confirmation must be boolean",
                "details": {"validation": "confirm_type"}
            }
        },
        "flow": {
            "invalid_step": {
                "message": "Invalid step in flow",
                "details": {"validation": "step_invalid"}
            },
            "invalid_action": {
                "message": "Invalid action for step",
                "details": {"validation": "action_invalid"}
            },
            "missing_data": {
                "message": "Required data missing",
                "details": {"validation": "data_missing"}
            },
            "invalid_state": {
                "message": "Invalid flow state",
                "details": {"validation": "state_invalid"}
            }
        },
        "system": {
            "service_error": {
                "message": "Service unavailable",
                "details": {"error": "service_unavailable"}
            },
            "config_error": {
                "message": "Configuration error",
                "details": {"error": "config_invalid"}
            },
            "api_error": {
                "message": "API error",
                "details": {"error": "api_error"}
            },
            "unknown_error": {
                "message": "Unknown error occurred",
                "details": {"error": "unknown"}
            }
        }
    }

    @classmethod
    def get_error_message(cls, error_type: str, error_key: str) -> Dict:
        """Get standardized error message with context

        Args:
            error_type: Type of error (component, flow, system)
            error_key: Key for error message

        Returns:
            Dict with message and details
        """
        try:
            return cls.MESSAGES[error_type][error_key]
        except KeyError:
            return cls.MESSAGES["system"]["unknown_error"]


def error_decorator(service: str):
    """Decorator for standardized error handling with context

    Args:
        service: Service name for error context

    Returns:
        Decorator function
    """
    def decorator(f):
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                # Return tuple format expected by service functions with context
                return False, ErrorHandler.handle_system_error(
                    code="REQUEST_ERROR",
                    service=service,
                    action=f.__name__,
                    message=str(e),
                    error=e
                )
        return wrapper
    return decorator
