"""Custom JWT token validators to enhance security."""
from typing import Dict, Any
from datetime import datetime

from .exceptions import SystemException


def validate_token(token: Dict[str, Any]) -> None:
    """Validate JWT token payload.

    Args:
        token: JWT token payload to validate

    Raises:
        SystemException: If token validation fails
    """
    try:
        # Check required fields
        member_id = token.get('memberID')
        if not member_id:
            raise SystemException(
                message='Invalid token payload: missing memberID',
                code='INVALID_TOKEN',
                service='jwt_auth',
                action='validate_token'
            )

        # Check token expiry
        expiry = token.get('absoluteExpiry')
        if not expiry or datetime.fromtimestamp(expiry) < datetime.now():
            raise SystemException(
                message='Token has expired',
                code='TOKEN_EXPIRED',
                service='jwt_auth',
                action='validate_token'
            )

    except Exception as e:
        raise SystemException(
            message=f'Token validation failed: {str(e)}',
            code='TOKEN_VALIDATION_ERROR',
            service='jwt_auth',
            action='validate_token'
        )
