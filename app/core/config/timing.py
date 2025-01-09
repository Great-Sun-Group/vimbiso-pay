"""Timing constants for state and API management"""

# Activity timeout in seconds (5 minutes as per API spec)
ACTIVITY_TTL = 300

# API timeouts and retries
API_TIMEOUT = 30
API_RETRY_DELAY = 5
MAX_API_RETRIES = 3

# Flow timeouts and retries
FLOW_TIMEOUT = 600  # 10 minutes
MAX_FLOW_RETRIES = 3

# Rate limiting
RATE_LIMIT_WINDOW = 60  # 1 minute
MAX_REQUESTS_PER_WINDOW = 60

__all__ = [
    'ACTIVITY_TTL',
    'API_TIMEOUT',
    'API_RETRY_DELAY',
    'MAX_API_RETRIES',
    'FLOW_TIMEOUT',
    'MAX_FLOW_RETRIES',
    'RATE_LIMIT_WINDOW',
    'MAX_REQUESTS_PER_WINDOW'
]
