"""Custom JWT token validators to enhance security."""
from typing import Dict, Any

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

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
            raise InvalidToken('User account is disabled')

        return user


def validate_token_user(token: Dict[str, Any]) -> None:
    """
    Additional token validation to check user status.
    Use this in views or middleware for extra security.
    """
    try:
        user_id = token.get('user_id')
        if not user_id:
            raise InvalidToken('Invalid token payload')

        user = User.objects.get(id=user_id)
        if not user.is_active:
            raise InvalidToken('User account is disabled')

    except User.DoesNotExist:
        raise InvalidToken('User not found')
    except Exception as e:
        raise InvalidToken(f'Token validation failed: {str(e)}')
