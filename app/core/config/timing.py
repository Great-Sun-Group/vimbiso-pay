"""Timing and TTL related constants"""

# Cache TTL
ACTIVITY_TTL = 300  # 5 minutes

# API Timeouts
API_TIMEOUT = 30  # seconds
API_RETRY_DELAY = 1  # seconds
MAX_API_RETRIES = 3

# Rate Limiting
RATE_LIMIT_WINDOW = 60  # 1 minute
MAX_REQUESTS_PER_WINDOW = 60
