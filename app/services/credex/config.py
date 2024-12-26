from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin

from decouple import config


@dataclass
class CredExConfig:
    """Configuration for CredEx service"""
    base_url: str
    client_api_key: str
    default_headers: dict

    @classmethod
    def from_env(cls) -> "CredExConfig":
        """Create configuration from environment variables"""
        base_url = config("MYCREDEX_APP_URL")
        if not base_url:
            raise ValueError("MYCREDEX_APP_URL environment variable is not set")

        client_api_key = config("CLIENT_API_KEY")
        if not client_api_key:
            raise ValueError("CLIENT_API_KEY environment variable is not set")

        return cls(
            base_url=base_url,
            client_api_key=client_api_key,
            default_headers={
                "Content-Type": "application/json",
                "x-client-api-key": client_api_key,
            }
        )

    def get_url(self, endpoint: str) -> str:
        """Get full URL for an endpoint"""
        return urljoin(self.base_url, endpoint)

    def get_headers(self, jwt_token: Optional[str] = None) -> dict:
        """Get headers with optional JWT token"""
        headers = self.default_headers.copy()
        if jwt_token:
            # Ensure token format is correct
            if not jwt_token.startswith("Bearer "):
                jwt_token = f"Bearer {jwt_token}"
            headers["Authorization"] = jwt_token
        return headers


# API Endpoints
class CredExEndpoints:
    """CredEx API endpoints with logical grouping"""

    ENDPOINTS = {
        'auth': {
            'login': {'path': 'login', 'requires_auth': False},
            'register': {'path': 'onboardMember', 'requires_auth': False}
        },
        'member': {
            'validate_handle': {'path': 'getAccountByHandle'},
            'get_dashboard': {'path': 'getDashboard'}
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
        """Get endpoint path for a group and action"""
        if group in cls.ENDPOINTS and action in cls.ENDPOINTS[group]:
            return cls.ENDPOINTS[group][action]['path']
        raise ValueError(f"Invalid endpoint: {group}/{action}")

    @classmethod
    def requires_auth(cls, group: str, action: str) -> bool:
        """Check if endpoint requires authentication"""
        if group in cls.ENDPOINTS and action in cls.ENDPOINTS[group]:
            return cls.ENDPOINTS[group][action].get('requires_auth', True)
        raise ValueError(f"Invalid endpoint: {group}/{action}")
