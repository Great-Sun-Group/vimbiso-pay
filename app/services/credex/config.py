"""CredEx configuration using environment variables"""
from dataclasses import dataclass
from typing import Dict
from urllib.parse import urljoin

from decouple import config
from core.utils.error_handler import error_decorator
from core.utils.exceptions import ConfigurationException


@dataclass
class CredExConfig:
    """Configuration for CredEx API access"""
    base_url: str
    client_api_key: str
    default_headers: Dict[str, str]

    @classmethod
    @error_decorator
    def from_env(cls) -> "CredExConfig":
        """Create configuration from environment variables"""
        # Get required environment variables
        base_url = config("MYCREDEX_APP_URL")
        if not base_url:
            raise ConfigurationException(
                "MYCREDEX_APP_URL environment variable is not set",
                "missing"
            )

        client_api_key = config("CLIENT_API_KEY")
        if not client_api_key:
            raise ConfigurationException(
                "CLIENT_API_KEY environment variable is not set",
                "missing"
            )

        # Create and validate headers
        default_headers = {
            "Content-Type": "application/json",
            "x-client-api-key": client_api_key,
        }

        return cls(
            base_url=base_url,
            client_api_key=client_api_key,
            default_headers=default_headers
        )

    @error_decorator
    def get_url(self, endpoint: str) -> str:
        """Get full URL for endpoint"""
        if not endpoint:
            raise ConfigurationException(
                "Endpoint is required",
                "validation"
            )

        return urljoin(self.base_url, endpoint)

    @error_decorator
    def get_headers(self) -> Dict[str, str]:
        """Get default headers"""
        return self.default_headers.copy()


class CredExEndpoints:
    """CredEx API endpoint definitions"""

    ENDPOINTS = {
        'auth': {
            'login': {'path': 'login', 'requires_auth': False},
            'register': {'path': 'onboardMember', 'requires_auth': False}
        },
        'member': {
            # placeholder for future endpoints
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
    @error_decorator
    def get_path(cls, group: str, action: str) -> str:
        """Get endpoint path"""
        if not group or not action:
            raise ConfigurationException(
                "Group and action are required",
                "validation"
            )

        if group not in cls.ENDPOINTS:
            raise ConfigurationException(
                f"Invalid endpoint group: {group}",
                "validation"
            )
        if action not in cls.ENDPOINTS[group]:
            raise ConfigurationException(
                f"Invalid action '{action}' for group '{group}'",
                "validation"
            )

        return cls.ENDPOINTS[group][action]['path']

    @classmethod
    @error_decorator
    def requires_auth(cls, group: str, action: str) -> bool:
        """Check if endpoint requires authentication"""
        if not group or not action:
            raise ConfigurationException(
                "Group and action are required",
                "validation"
            )

        if group not in cls.ENDPOINTS:
            raise ConfigurationException(
                f"Invalid endpoint group: {group}",
                "validation"
            )
        if action not in cls.ENDPOINTS[group]:
            raise ConfigurationException(
                f"Invalid action '{action}' for group '{group}'",
                "validation"
            )

        return cls.ENDPOINTS[group][action].get('requires_auth', True)
