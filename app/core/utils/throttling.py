from rest_framework.throttling import AnonRateThrottle


class HealthCheckRateThrottle(AnonRateThrottle):
    """Custom throttle for health check endpoint with higher rate limit"""
    rate = '1000/minute'  # Allow up to 1000 requests per minute
    scope = 'health_check'
