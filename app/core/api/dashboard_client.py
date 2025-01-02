"""Dashboard-related API operations"""
import logging
from typing import Dict, Any

from core.utils.exceptions import ServiceException
from decouple import config

from .base import BASE_URL, make_api_request

logger = logging.getLogger(__name__)


def get_dashboard(phone_number: str, jwt_token: str) -> Dict[str, Any]:
    """Fetch member dashboard from CredEx API

    Args:
        phone_number: Member's phone number
        jwt_token: JWT auth token

    Returns:
        Dashboard response data

    Raises:
        ServiceException: If API call fails
    """
    logger.info("Fetching dashboard")
    url = f"{BASE_URL}/getMemberDashboardByPhone"

    try:
        response = make_api_request(
            url=url,
            headers={
                "Content-Type": "application/json",
                "x-client-api-key": config("CLIENT_API_KEY"),
                "Authorization": f"Bearer {jwt_token}"
            },
            payload={"phone": phone_number}
        )

        if response.status_code == 200:
            return response.json()

        raise ServiceException(
            message=f"Dashboard fetch failed: {response.status_code}",
            code="API_ERROR",
            service="dashboard",
            action="get_dashboard"
        )

    except Exception as e:
        logger.exception("Error during dashboard fetch")
        raise ServiceException(
            message="Dashboard fetch failed",
            code="API_ERROR",
            service="dashboard",
            action="get_dashboard"
        ) from e


def validate_account_handle(handle: str, jwt_token: str) -> Dict[str, Any]:
    """Validate handle through CredEx API

    Args:
        handle: Account handle to validate
        jwt_token: JWT auth token

    Returns:
        Validation response data

    Raises:
        ServiceException: If API call fails
    """
    logger.info("Validating handle: %s", handle)
    url = f"{BASE_URL}/getAccountByHandle"

    try:
        response = make_api_request(
            url=url,
            headers={
                "Content-Type": "application/json",
                "x-client-api-key": config("CLIENT_API_KEY"),
                "Authorization": f"Bearer {jwt_token}"
            },
            payload={"accountHandle": handle.lower()},
            method="POST"
        )

        if response.status_code == 200:
            response_data = response.json()
            if not response_data.get("Error"):
                logger.info("Handle validation successful")
                return response_data

            logger.error("Handle validation failed")
            raise ServiceException(
                message="Invalid handle",
                code="INVALID_HANDLE",
                service="dashboard",
                action="validate_handle"
            )

        raise ServiceException(
            message=f"Handle validation failed: {response.status_code}",
            code="API_ERROR",
            service="dashboard",
            action="validate_handle"
        )

    except Exception as e:
        logger.exception("Error during handle validation")
        raise ServiceException(
            message="Handle validation failed",
            code="API_ERROR",
            service="dashboard",
            action="validate_handle"
        ) from e


def get_ledger(payload: Dict[str, Any], jwt_token: str) -> Dict[str, Any]:
    """Fetch ledger from CredEx API

    Args:
        payload: Ledger request payload
        jwt_token: JWT auth token

    Returns:
        Ledger response data

    Raises:
        ServiceException: If API call fails
    """
    logger.info("Fetching ledger")
    url = f"{BASE_URL}/getLedger"

    try:
        response = make_api_request(
            url=url,
            headers={
                "Content-Type": "application/json",
                "x-client-api-key": config("CLIENT_API_KEY"),
                "Authorization": f"Bearer {jwt_token}"
            },
            payload=payload
        )

        if response.status_code == 200:
            return response.json()

        raise ServiceException(
            message=f"Ledger fetch failed: {response.status_code}",
            code="API_ERROR",
            service="dashboard",
            action="get_ledger"
        )

    except Exception as e:
        logger.exception("Error during ledger fetch")
        raise ServiceException(
            message="Ledger fetch failed",
            code="API_ERROR",
            service="dashboard",
            action="get_ledger"
        ) from e
