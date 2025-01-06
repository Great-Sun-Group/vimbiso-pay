"""Custom JWT token validators to enhance security."""
from typing import Dict, Any

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication

from .exceptions import SystemException

User = get_user_model()


class EnhancedJWTAuthentication(JWTAuthentication):
    """Enhanced JWT authentication with additional security checks."""

    def get_user(self, validated_token: Dict[str, Any]) -> User:
        """
        Override get_user to add additional validation.
        Checks if user is active before allowing access.
        """
        user = super().get_user(validated_token)

        # Check if user is active
        if not user.is_active:
            raise SystemException(
                message='User account is disabled',
                code='USER_DISABLED',
                service='jwt_auth',
                action='validate_user'
            )

        return user


def validate_token_user(token: Dict[str, Any]) -> None:
    """Additional token validation to check user status.

    Args:
        token: JWT token payload to validate

    Raises:
        SystemException: If token validation fails
    """
    try:
        user_id = token.get('user_id')
        if not user_id:
            raise SystemException(
                message='Invalid token payload',
                code='INVALID_TOKEN',
                service='jwt_auth',
                action='validate_token'
            )

        user = User.objects.get(id=user_id)
        if not user.is_active:
            raise SystemException(
                message='User account is disabled',
                code='USER_DISABLED',
                service='jwt_auth',
                action='validate_token'
            )

    except User.DoesNotExist:
        raise SystemException(
            message='User not found',
            code='USER_NOT_FOUND',
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
