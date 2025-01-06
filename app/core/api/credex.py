"""CredEx operations using pure functions"""
import logging
from typing import Any, Dict

from core.utils.error_handler import ErrorHandler
from .base import (BASE_URL, get_headers, handle_error_response,
                   make_api_request)

logger = logging.getLogger(__name__)


def validate_account_handle(handle: str, token: str) -> Dict[str, Any]:
    """Validate a member's account handle through state validation"""
    logger.info(f"Validating account handle: {handle}")
    url = f"{BASE_URL}/validateHandle"
    logger.info(f"Validation URL: {url}")

    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {"handle": handle}

        # Make request
        response = make_api_request(url, headers, payload)
        if isinstance(response, dict) and "error" in response:
            return response

        if response.status_code == 200:
            response_data = response.json()
            if response_data.get("status") == "success":
                logger.info("Handle validation successful")
                return {"success": True, "data": response_data}

            logger.error("Handle validation failed")
            return ErrorHandler.handle_system_error(
                code="VALIDATION_FAILED",
                service="credex",
                action="validate_handle",
                message=response_data.get("error", "Handle validation failed")
            )

        return handle_error_response(
            "Handle validation",
            response,
            f"Handle validation failed: Unexpected error (status code: {response.status_code})"
        )

    except Exception as e:
        logger.exception(f"Error during handle validation: {str(e)}")
        return ErrorHandler.handle_system_error(
            code="VALIDATION_ERROR",
            service="credex",
            action="validate_handle",
            message=f"Handle validation failed: {str(e)}"
        )


def offer_credex(state_manager: Any) -> Dict[str, Any]:
    """Create a new CredEx offer through state validation"""
    logger.info("Attempting to offer CredEx")
    url = f"{BASE_URL}/createCredex"
    logger.info(f"Offer URL: {url}")

    try:
        # Let StateManager validate API request
        state_manager.update_state({
            "api_request": {
                "type": "credex_offer",
                "url": url,
                "method": "POST"
            }
        })

        # Get validated request data
        headers = get_headers(state_manager)
        payload = state_manager.get_api_payload()

        # Make request
        response = make_api_request(url, headers, payload, state_manager=state_manager)
        if isinstance(response, dict) and "error" in response:
            return response

        if response.status_code == 200:
            response_data = response.json()

            # Let StateManager validate response
            state_manager.update_state({
                "api_response": {
                    "type": "credex_offer",
                    "data": response_data
                }
            })

            # Get validated response
            validated_response = state_manager.get_api_response()
            if validated_response.get("status") == "success":
                return {"success": True, "data": validated_response}

            logger.error("Offer failed")
            return ErrorHandler.handle_system_error(
                code="OFFER_FAILED",
                service="credex",
                action="create_offer",
                message=response_data.get("error", "Offer failed")
            )

        return handle_error_response(
            "Offer",
            response,
            f"Offer failed: Unexpected error (status code: {response.status_code})"
        )

    except Exception as e:
        logger.exception(f"Error during offer: {str(e)}")
        return ErrorHandler.handle_system_error(
            code="OFFER_ERROR",
            service="credex",
            action="create_offer",
            message=f"Offer failed: {str(e)}"
        )


def accept_credex(state_manager: Any) -> Dict[str, Any]:
    """Accept a CredEx offer through state validation"""
    logger.info("Attempting to accept CredEx")
    url = f"{BASE_URL}/acceptCredex"
    logger.info(f"Accept URL: {url}")

    try:
        # Let StateManager validate API request
        state_manager.update_state({
            "api_request": {
                "type": "credex_accept",
                "url": url,
                "method": "POST"
            }
        })

        # Get validated request data
        headers = get_headers(state_manager)
        payload = state_manager.get_api_payload()

        # Make request
        response = make_api_request(url, headers, payload, state_manager=state_manager)
        if isinstance(response, dict) and "error" in response:
            return response

        if response.status_code == 200:
            response_data = response.json()
            # Let StateManager validate response
            state_manager.update_state({
                "api_response": {
                    "type": "credex_accept",
                    "data": response_data
                }
            })

            # Get validated response
            validated_response = state_manager.get_api_response()
            if validated_response.get("status") == "success":
                logger.info("Accept successful")
                return {"success": True, "data": validated_response}

            logger.error("Accept failed")
            return ErrorHandler.handle_system_error(
                code="ACCEPT_FAILED",
                service="credex",
                action="accept_offer",
                message=response_data.get("error", "Accept failed")
            )

        return handle_error_response(
            "Accept",
            response,
            f"Accept failed: Unexpected error (status code: {response.status_code})"
        )

    except Exception as e:
        logger.exception(f"Error during accept: {str(e)}")
        return ErrorHandler.handle_system_error(
            code="ACCEPT_ERROR",
            service="credex",
            action="accept_offer",
            message=f"Accept failed: {str(e)}"
        )


def decline_credex(state_manager: Any) -> Dict[str, Any]:
    """Decline a CredEx offer through state validation"""
    logger.info("Attempting to decline CredEx")
    url = f"{BASE_URL}/declineCredex"
    logger.info(f"Decline URL: {url}")

    try:
        # Let StateManager validate API request
        state_manager.update_state({
            "api_request": {
                "type": "credex_decline",
                "url": url,
                "method": "POST"
            }
        })

        # Get validated request data
        headers = get_headers(state_manager)
        payload = state_manager.get_api_payload()

        # Make request
        response = make_api_request(url, headers, payload, state_manager=state_manager)
        if isinstance(response, dict) and "error" in response:
            return response

        if response.status_code == 200:
            response_data = response.json()
            # Let StateManager validate response
            state_manager.update_state({
                "api_response": {
                    "type": "credex_decline",
                    "data": response_data
                }
            })

            # Get validated response
            validated_response = state_manager.get_api_response()
            if validated_response.get("status") == "success":
                logger.info("Decline successful")
                return {"success": True, "data": validated_response}

            logger.error("Decline failed")
            return ErrorHandler.handle_system_error(
                code="DECLINE_FAILED",
                service="credex",
                action="decline_offer",
                message=response_data.get("error", "Decline failed")
            )

        return handle_error_response(
            "Decline",
            response,
            f"Decline failed: Unexpected error (status code: {response.status_code})"
        )

    except Exception as e:
        logger.exception(f"Error during decline: {str(e)}")
        return ErrorHandler.handle_system_error(
            code="DECLINE_ERROR",
            service="credex",
            action="decline_offer",
            message=f"Decline failed: {str(e)}"
        )


def cancel_credex(state_manager: Any) -> Dict[str, Any]:
    """Cancel a CredEx offer through state validation"""
    logger.info("Attempting to cancel CredEx")
    url = f"{BASE_URL}/cancelCredex"
    logger.info(f"Cancel URL: {url}")

    try:
        # Let StateManager validate API request
        state_manager.update_state({
            "api_request": {
                "type": "credex_cancel",
                "url": url,
                "method": "POST"
            }
        })

        # Get validated request data
        headers = get_headers(state_manager)
        payload = state_manager.get_api_payload()

        # Make request
        response = make_api_request(url, headers, payload, state_manager=state_manager)
        if isinstance(response, dict) and "error" in response:
            return response

        if response.status_code == 200:
            response_data = response.json()
            # Let StateManager validate response
            state_manager.update_state({
                "api_response": {
                    "type": "credex_cancel",
                    "data": response_data
                }
            })

            # Get validated response
            validated_response = state_manager.get_api_response()
            if validated_response.get("status") == "success":
                logger.info("Cancel successful")
                return {"success": True, "data": validated_response}

            logger.error("Cancel failed")
            return ErrorHandler.handle_system_error(
                code="CANCEL_FAILED",
                service="credex",
                action="cancel_offer",
                message=response_data.get("error", "Cancel failed")
            )

        return handle_error_response(
            "Cancel",
            response,
            f"Cancel failed: Unexpected error (status code: {response.status_code})"
        )

    except Exception as e:
        logger.exception(f"Error during cancel: {str(e)}")
        return ErrorHandler.handle_system_error(
            code="CANCEL_ERROR",
            service="credex",
            action="cancel_offer",
            message=f"Cancel failed: {str(e)}"
        )


def get_credex(state_manager: Any) -> Dict[str, Any]:
    """Get details of a specific CredEx through state validation"""
    logger.info("Fetching credex details")
    url = f"{BASE_URL}/getCredex"
    logger.info(f"Credex URL: {url}")

    try:
        # Let StateManager validate API request
        state_manager.update_state({
            "api_request": {
                "type": "credex_get",
                "url": url,
                "method": "GET"
            }
        })

        # Get validated request data
        headers = get_headers(state_manager)
        payload = state_manager.get_api_payload()

        # Make request
        response = make_api_request(url, headers, payload, state_manager=state_manager)
        if isinstance(response, dict) and "error" in response:
            return response

        if response.status_code == 200:
            response_data = response.json()
            # Let StateManager validate response
            state_manager.update_state({
                "api_response": {
                    "type": "credex_get",
                    "data": response_data
                }
            })

            # Get validated response
            validated_response = state_manager.get_api_response()
            if validated_response.get("status") == "success":
                logger.info("Credex fetched successfully")
                return {"success": True, "data": validated_response}

        return handle_error_response(
            "Credex fetch",
            response,
            f"Credex fetch failed: Unexpected error (status code: {response.status_code})"
        )

    except Exception as e:
        logger.exception(f"Error during credex fetch: {str(e)}")
        return ErrorHandler.handle_system_error(
            code="GET_ERROR",
            service="credex",
            action="get_offer",
            message=f"Credex fetch failed: {str(e)}"
        )


def accept_bulk_credex(state_manager: Any) -> Dict[str, Any]:
    """Accept multiple CredEx offers through state validation"""
    logger.info("Attempting to accept multiple CredEx offers")
    url = f"{BASE_URL}/acceptCredexBulk"
    logger.info(f"Accept URL: {url}")

    try:
        # Let StateManager validate API request
        state_manager.update_state({
            "api_request": {
                "type": "credex_bulk_accept",
                "url": url,
                "method": "POST"
            }
        })

        # Get validated request data
        headers = get_headers(state_manager)
        payload = state_manager.get_api_payload()

        # Make request
        response = make_api_request(url, headers, payload, state_manager=state_manager)
        if isinstance(response, dict) and "error" in response:
            return response

        if response.status_code == 200:
            response_data = response.json()
            # Let StateManager validate response
            state_manager.update_state({
                "api_response": {
                    "type": "credex_bulk_accept",
                    "data": response_data
                }
            })

            # Get validated response
            validated_response = state_manager.get_api_response()
            if validated_response.get("status") == "success":
                logger.info("Bulk accept successful")
                return {"success": True, "data": validated_response}

            logger.error("Bulk accept failed")
            return ErrorHandler.handle_system_error(
                code="BULK_ACCEPT_FAILED",
                service="credex",
                action="bulk_accept",
                message=response_data.get("error", "Bulk accept failed")
            )

        return handle_error_response(
            "Bulk accept",
            response,
            f"Bulk accept failed: Unexpected error (status code: {response.status_code})"
        )

    except Exception as e:
        logger.exception(f"Error during bulk accept: {str(e)}")
        return ErrorHandler.handle_system_error(
            code="BULK_ACCEPT_ERROR",
            service="credex",
            action="bulk_accept",
            message=f"Bulk accept failed: {str(e)}"
        )


def get_ledger(state_manager: Any) -> Dict[str, Any]:
    """Get user's CredEx ledger through state validation"""
    logger.info("Fetching CredEx ledger")
    url = f"{BASE_URL}/getLedger"
    logger.info(f"Ledger URL: {url}")

    try:
        # Let StateManager validate API request
        state_manager.update_state({
            "api_request": {
                "type": "credex_ledger",
                "url": url,
                "method": "GET"
            }
        })

        # Get validated request data
        headers = get_headers(state_manager)
        payload = state_manager.get_api_payload()

        # Make request
        response = make_api_request(url, headers, payload, state_manager=state_manager)
        if isinstance(response, dict) and "error" in response:
            return response

        if response.status_code == 200:
            response_data = response.json()
            # Let StateManager validate response
            state_manager.update_state({
                "api_response": {
                    "type": "credex_ledger",
                    "data": response_data
                }
            })

            # Get validated response
            validated_response = state_manager.get_api_response()
            if validated_response.get("status") == "success":
                logger.info("Ledger fetched successfully")
                return {"success": True, "data": validated_response}

        return handle_error_response(
            "Ledger fetch",
            response,
            f"Ledger fetch failed: Unexpected error (status code: {response.status_code})"
        )

    except Exception as e:
        logger.exception(f"Error during ledger fetch: {str(e)}")
        return ErrorHandler.handle_system_error(
            code="LEDGER_ERROR",
            service="credex",
            action="get_ledger",
            message=f"Ledger fetch failed: {str(e)}"
        )
