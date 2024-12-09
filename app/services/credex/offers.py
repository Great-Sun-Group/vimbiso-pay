import logging
from typing import Any, Dict, List, Tuple

from .base import BaseCredExService
from .config import CredExEndpoints
from .exceptions import (
    InvalidCredExOfferError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class CredExOffersService(BaseCredExService):
    """Service for CredEx offer operations"""

    def offer_credex(self, offer_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Create a new CredEx offer"""
        if not offer_data:
            raise ValidationError("Offer data is required")

        try:
            # Remove any full_name field if present as it's not needed
            offer_data.pop("full_name", None)

            response = self._make_request(
                CredExEndpoints.CREATE_CREDEX,
                payload=offer_data
            )

            data = self._validate_response(response, {
                400: "Invalid offer data",
                401: "Unauthorized offer attempt"
            })

            if response.status_code == 200:
                if data.get("data", {}).get("action", {}).get("type") == "CREDEX_CREATED":
                    logger.info("CredEx offer created successfully")
                    return True, data
                else:
                    logger.error("CredEx offer creation failed")
                    raise InvalidCredExOfferError(data.get("error", "Failed to create offer"))
            else:
                error_msg = data.get("error", "Failed to create offer")
                logger.error(f"CredEx offer creation failed: {error_msg}")
                return False, {"error": error_msg}

        except InvalidCredExOfferError as e:
            logger.warning(f"Invalid CredEx offer: {str(e)}")
            return False, {"error": str(e)}
        except Exception as e:
            logger.exception(f"CredEx offer creation failed: {str(e)}")
            return False, {"error": f"Failed to create offer: {str(e)}"}

    def accept_credex(self, offer_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Accept a CredEx offer"""
        if not offer_id:
            raise ValidationError("Offer ID is required")

        try:
            response = self._make_request(
                CredExEndpoints.ACCEPT_CREDEX,
                payload={"offerId": offer_id}
            )

            data = self._validate_response(response, {
                400: "Invalid offer acceptance",
                401: "Unauthorized acceptance attempt"
            })

            if response.status_code == 200:
                if data.get("data", {}).get("action", {}).get("type") == "CREDEX_ACCEPTED":
                    logger.info("CredEx offer accepted successfully")
                    return True, data
                else:
                    logger.error("CredEx offer acceptance failed")
                    return False, {"error": data.get("error", "Failed to accept offer")}
            else:
                error_msg = data.get("error", "Failed to accept offer")
                logger.error(f"CredEx offer acceptance failed: {error_msg}")
                return False, {"error": error_msg}

        except Exception as e:
            logger.exception(f"CredEx offer acceptance failed: {str(e)}")
            return False, {"error": f"Failed to accept offer: {str(e)}"}

    def accept_bulk_credex(self, offer_ids: List[str]) -> Tuple[bool, Dict[str, Any]]:
        """Accept multiple CredEx offers"""
        if not offer_ids:
            raise ValidationError("Offer IDs are required")

        try:
            response = self._make_request(
                CredExEndpoints.ACCEPT_BULK_CREDEX,
                payload={"offerIds": offer_ids}
            )

            data = self._validate_response(response, {
                400: "Invalid bulk acceptance request",
                401: "Unauthorized bulk acceptance attempt"
            })

            if response.status_code == 200:
                if data.get("summary", {}).get("accepted"):
                    logger.info("Bulk CredEx offers accepted successfully")
                    return True, data
                else:
                    logger.error("Bulk CredEx offer acceptance failed")
                    return False, {"error": data.get("error", "Failed to accept offers")}
            else:
                error_msg = data.get("message", "Failed to accept offers")
                logger.error(f"Bulk CredEx offer acceptance failed: {error_msg}")
                return False, {"error": error_msg}

        except Exception as e:
            logger.exception(f"Bulk CredEx offer acceptance failed: {str(e)}")
            return False, {"error": f"Failed to accept offers: {str(e)}"}

    def decline_credex(self, offer_id: str) -> Tuple[bool, str]:
        """Decline a CredEx offer"""
        if not offer_id:
            raise ValidationError("Offer ID is required")

        try:
            response = self._make_request(
                CredExEndpoints.DECLINE_CREDEX,
                payload={"offerId": offer_id}
            )

            data = self._validate_response(response, {
                400: "Invalid decline request",
                401: "Unauthorized decline attempt"
            })

            if response.status_code == 200:
                if data.get("status") == "success":
                    logger.info("CredEx offer declined successfully")
                    return True, "Decline successful"
                else:
                    logger.error("CredEx offer decline failed")
                    return False, data.get("error", "Failed to decline offer")
            else:
                error_msg = data.get("message", "Failed to decline offer")
                logger.error(f"CredEx offer decline failed: {error_msg}")
                return False, error_msg

        except Exception as e:
            logger.exception(f"CredEx offer decline failed: {str(e)}")
            return False, f"Failed to decline offer: {str(e)}"

    def cancel_credex(self, offer_id: str) -> Tuple[bool, str]:
        """Cancel a CredEx offer"""
        if not offer_id:
            raise ValidationError("Offer ID is required")

        try:
            response = self._make_request(
                CredExEndpoints.CANCEL_CREDEX,
                payload={"offerId": offer_id}
            )

            data = self._validate_response(response, {
                400: "Invalid cancellation request",
                401: "Unauthorized cancellation attempt"
            })

            if response.status_code == 200:
                if data.get("message") == "Credex cancelled successfully":
                    logger.info("CredEx offer cancelled successfully")
                    return True, "Credex cancelled successfully"
                else:
                    logger.error("CredEx offer cancellation failed")
                    return False, data.get("error", "Failed to cancel offer")
            else:
                error_msg = data.get("message", "Failed to cancel offer")
                logger.error(f"CredEx offer cancellation failed: {error_msg}")
                return False, error_msg

        except Exception as e:
            logger.exception(f"CredEx offer cancellation failed: {str(e)}")
            return False, f"Failed to cancel offer: {str(e)}"

    def get_credex(self, offer_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Get details of a specific CredEx offer"""
        if not offer_id:
            raise ValidationError("Offer ID is required")

        try:
            response = self._make_request(
                CredExEndpoints.GET_CREDEX,
                payload={"offerId": offer_id}
            )

            data = self._validate_response(response, {
                400: "Invalid request",
                401: "Unauthorized access",
                404: "Offer not found"
            })

            if response.status_code == 200:
                logger.info("CredEx offer details fetched successfully")
                return True, data
            else:
                error_msg = data.get("message", "Failed to fetch offer details")
                logger.error(f"CredEx offer details fetch failed: {error_msg}")
                return False, {"message": error_msg}

        except Exception as e:
            logger.exception(f"CredEx offer details fetch failed: {str(e)}")
            return False, {"message": f"Failed to fetch offer details: {str(e)}"}

    def get_ledger(self, member_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Get member's ledger information"""
        if not member_id:
            raise ValidationError("Member ID is required")

        try:
            response = self._make_request(
                CredExEndpoints.GET_LEDGER,
                payload={"memberId": member_id}
            )

            data = self._validate_response(response, {
                400: "Invalid request",
                401: "Unauthorized access",
                404: "Ledger not found"
            })

            if response.status_code == 200:
                logger.info("Ledger fetched successfully")
                return True, data
            else:
                error_msg = data.get("message", "Failed to fetch ledger")
                logger.error(f"Ledger fetch failed: {error_msg}")
                return False, {"message": error_msg}

        except Exception as e:
            logger.exception(f"Ledger fetch failed: {str(e)}")
            return False, {"message": f"Failed to fetch ledger: {str(e)}"}
