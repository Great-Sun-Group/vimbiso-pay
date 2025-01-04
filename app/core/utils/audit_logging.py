"""Audit logging with proper error handling and boundaries"""
import logging
import os
from typing import Any, Dict, Optional

from .exceptions import SystemException

# Configure the logger
logger = logging.getLogger("audit")
logger.setLevel(logging.INFO)

try:
    # Ensure log directory exists
    log_dir = os.path.join(os.path.dirname(__file__), '../../data/logs')
    os.makedirs(log_dir, exist_ok=True)

    # Create a file handler with proper path
    handler = logging.FileHandler(os.path.join(log_dir, "audit.log"))
    handler.setLevel(logging.INFO)

    # Create a logging format
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(handler)

except Exception as e:
    raise SystemException(
        message=f"Failed to initialize audit logging: {str(e)}",
        code="AUDIT_INIT_ERROR",
        service="audit_logging",
        action="initialize"
    )


def log_auth_event(
    event_type: str,
    user: str,
    status: str,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Log an authentication event with proper error handling

    Args:
        event_type: Type of the event (e.g., 'login', 'logout', 'password_change')
        user: User associated with the event
        status: Status of the event (e.g., 'success', 'failure')
        details: Additional details about the event

    Raises:
        SystemException: If logging fails
    """
    try:
        message = f"Auth event: {event_type} - User: {user} - Status: {status}"
        if details:
            message += f" - Details: {details}"
        logger.info(message)
    except Exception as e:
        raise SystemException(
            message=f"Failed to log auth event: {str(e)}",
            code="AUDIT_LOG_ERROR",
            service="audit_logging",
            action="log_auth"
        )


def log_authorization_event(
    user: str,
    resource: str,
    action: str,
    status: str,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Log an authorization event with proper error handling

    Args:
        user: User attempting the action
        resource: Resource being accessed
        action: Action being performed
        status: Status of the authorization (e.g., 'granted', 'denied')
        details: Additional details about the event

    Raises:
        SystemException: If logging fails
    """
    try:
        message = f"Authorization event: User: {user} - Resource: {resource} - Action: {action} - Status: {status}"
        if details:
            message += f" - Details: {details}"
        logger.info(message)
    except Exception as e:
        raise SystemException(
            message=f"Failed to log authorization event: {str(e)}",
            code="AUDIT_LOG_ERROR",
            service="audit_logging",
            action="log_authorization"
        )
