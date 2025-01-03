"""Error type definitions and constants

This module defines the core error types and structures used by the error handling system.
All error types follow a simple, flat structure with clear boundaries.

Error Context:
- Standardized error context structure
- Used for passing error information
- Maintains clear error boundaries
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, Optional


@dataclass
class ValidationResult:
    """Result of UI/component validation

    Attributes:
        valid: Whether validation passed
        error: Optional error details if validation failed
        value: Optional transformed value if validation passed
    """
    valid: bool
    error: Optional[Dict] = None
    value: Optional[Any] = None

    @classmethod
    def success(cls, value: Any = None) -> 'ValidationResult':
        """Create successful validation result"""
        return cls(valid=True, value=value)

    @classmethod
    def failure(cls, message: str, field: str = "value", details: Optional[Dict] = None) -> 'ValidationResult':
        """Create validation error result"""
        return cls(
            valid=False,
            error={
                "type": "validation",
                "field": field,
                "message": message,
                **({"details": details} if details else {})
            }
        )


@dataclass
class ErrorContext:
    """Standardized error context structure

    Used for passing error information between layers while maintaining
    clear error boundaries and consistent error handling patterns.

    Attributes:
        error_type: Type of error (component, flow, system, state)
        message: User-facing or system message
        details: Error-specific context details
    """
    error_type: str
    message: str
    details: Optional[Dict] = None


class ErrorType(Enum):
    """Core error types with clear boundaries"""
    COMPONENT = auto()  # Component validation errors
    FLOW = auto()      # Flow business logic errors
    SYSTEM = auto()    # System technical errors


@dataclass
class ErrorResponse:
    """Standard error response structure"""
    type: str           # Error type (component, flow, system)
    message: str        # User-facing message
    details: Dict       # Error-specific details


# Component error codes
COMPONENT_ERRORS = {
    "INVALID_AMOUNT": "invalid_amount",
    "INVALID_FORMAT": "invalid_format",
    "INVALID_HANDLE": "invalid_handle",
    "MISSING_HANDLE": "missing_handle",
    "INVALID_SELECTION": "invalid_selection",
    "INVALID_CONFIRM": "invalid_confirm"
}

# Flow error codes
FLOW_ERRORS = {
    "INVALID_STEP": "invalid_step",
    "INVALID_ACTION": "invalid_action",
    "MISSING_DATA": "missing_data",
    "INVALID_STATE": "invalid_state"
}

# System error codes
SYSTEM_ERRORS = {
    "SERVICE_ERROR": "service_error",
    "CONFIG_ERROR": "config_error",
    "API_ERROR": "api_error",
    "UNKNOWN_ERROR": "unknown_error"
}

# HTTP status code mappings
ERROR_STATUS_CODES = {
    "component": 400,  # Bad Request
    "flow": 400,      # Bad Request
    "system": 500     # Internal Server Error
}
