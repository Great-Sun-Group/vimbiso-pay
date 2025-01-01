"""Error types and context for state management"""
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ErrorContext:
    """Error context for state updates

    Required for ALL errors to ensure consistent handling.
    Components should NOT create error messages directly.

    Fields:
        error_type: Type of error (must be one of: flow, state, input, api, system)
        message: Clear user-facing message
        step_id: Only required for flow errors, should be None for other types
        details: Additional context (required for debugging)

    Rules:
        1. error_type must be one of the standard types
        2. step_id is ONLY required when error_type is "flow"
        3. For all other error types, step_id must be None
        4. details must include relevant debugging information
        5. message must be user-friendly and actionable
    """

    # Standard error types
    VALID_ERROR_TYPES = {"flow", "state", "input", "api", "system"}
    error_type: str
    message: str
    step_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate error context requirements"""
        # Validate error type
        if self.error_type not in self.VALID_ERROR_TYPES:
            raise ValueError(f"error_type must be one of: {', '.join(self.VALID_ERROR_TYPES)}")

        # Validate step_id requirements
        if self.error_type == "flow" and not self.step_id:
            raise ValueError("step_id is required for flow errors")
        if self.error_type != "flow" and self.step_id:
            raise ValueError("step_id should only be set for flow errors")

        # Validate message
        if not self.message or not isinstance(self.message, str):
            raise ValueError("message must be a non-empty string")

        # Validate details
        if not self.details:
            raise ValueError("details are required for debugging context")
        if not isinstance(self.details, dict):
            raise ValueError("details must be a dictionary")
