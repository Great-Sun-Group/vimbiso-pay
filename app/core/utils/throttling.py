from rest_framework.throttling import AnonRateThrottle

from .exceptions import SystemException


class HealthCheckRateThrottle(AnonRateThrottle):
    """Custom throttle for health check endpoint with higher rate limit

    Raises:
        SystemException: If rate limit exceeded
    """
    rate = '1000/minute'  # Allow up to 1000 requests per minute
    scope = 'health_check'

    def allow_request(self, request, view):
        """Check if request should be allowed

        Args:
            request: The request to check
            view: The view being accessed

        Raises:
            SystemException: If rate limit exceeded
        """
        try:
            allowed = super().allow_request(request, view)
            if not allowed:
                raise SystemException(
                    message="Rate limit exceeded",
                    code="RATE_LIMIT_EXCEEDED",
                    service="throttling",
                    action="health_check"
                )
            return allowed
        except Exception as e:
            if not isinstance(e, SystemException):
                raise SystemException(
                    message=f"Throttling error: {str(e)}",
                    code="THROTTLE_ERROR",
                    service="throttling",
                    action="health_check"
                )
            raise
