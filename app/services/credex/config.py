import os
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin


@dataclass
class CredExConfig:
    """Configuration for CredEx service"""
    base_url: str
    client_api_key: str
    default_headers: dict

    @classmethod
    def from_env(cls) -> "CredExConfig":
        """Create configuration from environment variables"""
        base_url = os.getenv("MYCREDEX_APP_URL")
        if not base_url:
            raise ValueError("MYCREDEX_APP_URL environment variable is not set")

        client_api_key = os.getenv("CLIENT_API_KEY")
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
            headers["Authorization"] = f"Bearer {jwt_token}"
        return headers


# API Endpoints
class CredExEndpoints:
    """CredEx API endpoints"""
    LOGIN = "login"
    REGISTER = "onboardMember"
    DASHBOARD = "getMemberDashboardByPhone"
    VALIDATE_HANDLE = "getAccountByHandle"
    CREATE_CREDEX = "createCredex"
    ACCEPT_CREDEX = "acceptCredex"
    ACCEPT_BULK_CREDEX = "acceptCredexBulk"
    DECLINE_CREDEX = "declineCredex"
    CANCEL_CREDEX = "cancelCredex"
    GET_CREDEX = "getCredex"
    GET_LEDGER = "getLedger"
