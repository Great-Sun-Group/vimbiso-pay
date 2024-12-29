import logging
from dataclasses import dataclass
from typing import Dict, Optional
from urllib.parse import urljoin

from decouple import config

logger = logging.getLogger(__name__)


@dataclass
class CredExConfig:
    """Configuration enforcing SINGLE SOURCE OF TRUTH"""
    base_url: str
    client_api_key: str
    default_headers: Dict[str, str]

    def __post_init__(self):
        """Validate configuration after initialization"""
        if not isinstance(self.base_url, str):
            raise ValueError("base_url must be a string")
        if not self.base_url.strip():
            raise ValueError("base_url is required")
        if not isinstance(self.client_api_key, str):
            raise ValueError("client_api_key must be a string")
        if not self.client_api_key.strip():
            raise ValueError("client_api_key is required")
        if not isinstance(self.default_headers, dict):
            raise ValueError("default_headers must be a dictionary")

    @classmethod
    def from_env(cls) -> "CredExConfig":
        """Create configuration enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Get required environment variables
            base_url = config("MYCREDEX_APP_URL")
            if not base_url:
                raise ValueError("MYCREDEX_APP_URL environment variable is not set")
            if not isinstance(base_url, str):
                raise ValueError("MYCREDEX_APP_URL must be a string")

            client_api_key = config("CLIENT_API_KEY")
            if not client_api_key:
                raise ValueError("CLIENT_API_KEY environment variable is not set")
            if not isinstance(client_api_key, str):
                raise ValueError("CLIENT_API_KEY must be a string")

            # Create and validate headers
            default_headers = {
                "Content-Type": "application/json",
                "x-client-api-key": client_api_key,
            }

            # Create configuration
            logger.info("Creating CredEx configuration from environment")
            return cls(
                base_url=base_url,
                client_api_key=client_api_key,
                default_headers=default_headers
            )

        except ValueError as e:
            logger.error(f"Configuration error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected configuration error: {str(e)}")
            raise ValueError(f"Failed to create configuration: {str(e)}")

    def get_url(self, endpoint: str) -> str:
        """Get full URL enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate input
            if not isinstance(endpoint, str):
                raise ValueError("Endpoint must be a string")
            if not endpoint.strip():
                raise ValueError("Endpoint is required")

            # Create URL
            url = urljoin(self.base_url, endpoint)
            logger.debug(f"Created URL: {url}")
            return url

        except ValueError as e:
            logger.error(f"URL creation error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected URL creation error: {str(e)}")
            raise ValueError(f"Failed to create URL: {str(e)}")

    def get_headers(self, jwt_token: Optional[str] = None) -> Dict[str, str]:
        """Get headers enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Create copy of default headers
            headers = self.default_headers.copy()

            # Add JWT token if provided
            if jwt_token:
                # Validate token
                if not isinstance(jwt_token, str):
                    raise ValueError("JWT token must be a string")
                if not jwt_token.strip():
                    raise ValueError("JWT token cannot be empty")

                # Format token
                if not jwt_token.startswith("Bearer "):
                    jwt_token = f"Bearer {jwt_token}"

                headers["Authorization"] = jwt_token

            logger.debug("Created headers successfully")
            return headers

        except ValueError as e:
            logger.error(f"Headers creation error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected headers creation error: {str(e)}")
            raise ValueError(f"Failed to create headers: {str(e)}")


# API Endpoints
class CredExEndpoints:
    """CredEx API endpoints with logical grouping"""

    ENDPOINTS = {
        'auth': {
            'login': {'path': 'login', 'requires_auth': False},
            'register': {'path': 'onboardMember', 'requires_auth': False}
        },
        'member': {
            # placeholder until more member-level endpoints added
        },
        'account': {
            'validate_account_handle': {'path': 'getAccountByHandle'}
            # Dashboard and account data comes from login, onboard, and all responses where changes are made
        },
        'credex': {
            'create': {'path': 'createCredex'},
            'accept': {'path': 'acceptCredex'},
            'accept_bulk': {'path': 'acceptCredexBulk'},
            'decline': {'path': 'declineCredex'},
            'cancel': {'path': 'cancelCredex'},
            'get': {'path': 'getCredex'},
            'get_ledger': {'path': 'getLedger'}
        },
        'recurring': {
            'create': {'path': 'createRecurring'},
            'accept': {'path': 'acceptRecurring'},
            'cancel': {'path': 'cancelRecurring'},
            'get': {'path': 'getRecurring'}
        }
    }

    @classmethod
    def get_path(cls, group: str, action: str) -> str:
        """Get endpoint path enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate inputs
            if not isinstance(group, str):
                raise ValueError("Group must be a string")
            if not group.strip():
                raise ValueError("Group is required")
            if not isinstance(action, str):
                raise ValueError("Action must be a string")
            if not action.strip():
                raise ValueError("Action is required")

            # Validate endpoint exists
            if group not in cls.ENDPOINTS:
                raise ValueError(f"Invalid endpoint group: {group}")
            if action not in cls.ENDPOINTS[group]:
                raise ValueError(f"Invalid action '{action}' for group '{group}'")

            # Get path
            path = cls.ENDPOINTS[group][action]['path']
            logger.debug(f"Found path '{path}' for {group}/{action}")
            return path

        except ValueError as e:
            logger.error(f"Path lookup error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected path lookup error: {str(e)}")
            raise ValueError(f"Failed to get endpoint path: {str(e)}")

    @classmethod
    def requires_auth(cls, group: str, action: str) -> bool:
        """Check if endpoint requires authentication enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate inputs
            if not isinstance(group, str):
                raise ValueError("Group must be a string")
            if not group.strip():
                raise ValueError("Group is required")
            if not isinstance(action, str):
                raise ValueError("Action must be a string")
            if not action.strip():
                raise ValueError("Action is required")

            # Validate endpoint exists
            if group not in cls.ENDPOINTS:
                raise ValueError(f"Invalid endpoint group: {group}")
            if action not in cls.ENDPOINTS[group]:
                raise ValueError(f"Invalid action '{action}' for group '{group}'")

            # Get auth requirement
            requires_auth = cls.ENDPOINTS[group][action].get('requires_auth', True)
            logger.debug(f"Auth requirement for {group}/{action}: {requires_auth}")
            return requires_auth

        except ValueError as e:
            logger.error(f"Auth requirement lookup error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected auth requirement lookup error: {str(e)}")
            raise ValueError(f"Failed to check auth requirement: {str(e)}")
