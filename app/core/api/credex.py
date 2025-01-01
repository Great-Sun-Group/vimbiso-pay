"""CredEx operations using pure functions"""
import logging
from typing import Any, Dict, Tuple

from .base import (BASE_URL, get_headers, handle_error_response,
                   make_api_request)

logger = logging.getLogger(__name__)


def offer_credex(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Create a new CredEx offer through state validation"""
    logger.info("Attempting to offer CredEx")
    url = f"{BASE_URL}/createCredex"
    logger.info(f"Offer URL: {url}")

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

    try:
        response = make_api_request(url, headers, payload, state_manager=state_manager)
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
                return True, validated_response
            else:
                logger.error("Offer failed")
                return False, {"error": response_data.get("error")}

        else:
            return handle_error_response(
                "Offer",
                response,
                f"Offer failed: Unexpected error (status code: {response.status_code})"
            )

    except Exception as e:
        logger.exception(f"Error during offer: {str(e)}")
        return False, {"error": f"Offer failed: {str(e)}"}


def accept_credex(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Accept a CredEx offer through state validation"""
    logger.info("Attempting to accept CredEx")
    url = f"{BASE_URL}/acceptCredex"
    logger.info(f"Accept URL: {url}")

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

    try:
        response = make_api_request(url, headers, payload, state_manager=state_manager)
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
                return True, validated_response
            else:
                logger.error("Accept failed")
                return False, {"error": response_data.get("error")}

        else:
            return handle_error_response(
                "Accept",
                response,
                f"Accept failed: Unexpected error (status code: {response.status_code})"
            )

    except Exception as e:
        logger.exception(f"Error during accept: {str(e)}")
        return False, {"error": f"Accept failed: {str(e)}"}


def decline_credex(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Decline a CredEx offer through state validation"""
    logger.info("Attempting to decline CredEx")
    url = f"{BASE_URL}/declineCredex"
    logger.info(f"Decline URL: {url}")

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

    try:
        response = make_api_request(url, headers, payload, state_manager=state_manager)
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
                return True, validated_response
            else:
                logger.error("Decline failed")
                return False, {"error": response_data.get("error")}

        else:
            return handle_error_response(
                "Decline",
                response,
                f"Decline failed: Unexpected error (status code: {response.status_code})"
            )

    except Exception as e:
        logger.exception(f"Error during decline: {str(e)}")
        return False, {"error": f"Decline failed: {str(e)}"}


def cancel_credex(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Cancel a CredEx offer through state validation"""
    logger.info("Attempting to cancel CredEx")
    url = f"{BASE_URL}/cancelCredex"
    logger.info(f"Cancel URL: {url}")

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

    try:
        response = make_api_request(url, headers, payload, state_manager=state_manager)
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
                return True, validated_response
            else:
                logger.error("Cancel failed")
                return False, {"error": response_data.get("error")}

        else:
            return handle_error_response(
                "Cancel",
                response,
                f"Cancel failed: Unexpected error (status code: {response.status_code})"
            )

    except Exception as e:
        logger.exception(f"Error during cancel: {str(e)}")
        return False, {"error": f"Cancel failed: {str(e)}"}


def get_credex(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Get details of a specific CredEx through state validation"""
    logger.info("Fetching credex details")
    url = f"{BASE_URL}/getCredex"
    logger.info(f"Credex URL: {url}")

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

    try:
        response = make_api_request(url, headers, payload, state_manager=state_manager)
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
                return True, validated_response

        else:
            return handle_error_response(
                "Credex fetch",
                response,
                f"Credex fetch failed: Unexpected error (status code: {response.status_code})"
            )

    except Exception as e:
        logger.exception(f"Error during credex fetch: {str(e)}")
        return False, {"error": f"Credex fetch failed: {str(e)}"}


def accept_bulk_credex(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Accept multiple CredEx offers through state validation"""
    logger.info("Attempting to accept multiple CredEx offers")
    url = f"{BASE_URL}/acceptCredexBulk"
    logger.info(f"Accept URL: {url}")

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

    try:
        response = make_api_request(url, headers, payload, state_manager=state_manager)
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
                return True, validated_response
            else:
                logger.error("Bulk accept failed")
                return False, {"error": response_data.get("error")}

        else:
            return handle_error_response(
                "Bulk accept",
                response,
                f"Bulk accept failed: Unexpected error (status code: {response.status_code})"
            )

    except Exception as e:
        logger.exception(f"Error during bulk accept: {str(e)}")
        return False, {"error": f"Bulk accept failed: {str(e)}"}


def get_ledger(state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
    """Get user's CredEx ledger through state validation"""
    logger.info("Fetching CredEx ledger")
    url = f"{BASE_URL}/getLedger"
    logger.info(f"Ledger URL: {url}")

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

    try:
        response = make_api_request(url, headers, payload, state_manager=state_manager)
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
                return True, validated_response

        else:
            return handle_error_response(
                "Ledger fetch",
                response,
                f"Ledger fetch failed: Unexpected error (status code: {response.status_code})"
            )

    except Exception as e:
        logger.exception(f"Error during ledger fetch: {str(e)}")
        return False, {"error": f"Ledger fetch failed: {str(e)}"}
