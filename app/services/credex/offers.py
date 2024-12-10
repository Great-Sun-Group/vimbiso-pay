import logging
from typing import Any, Dict, List, Tuple

from core.transactions.exceptions import TransactionError
from .base import BaseCredExService
from .config import CredExEndpoints

logger = logging.getLogger(__name__)


class CredExOffersService(BaseCredExService):
    """Service for CredEx offer operations"""

    def offer_credex(self, offer_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Create a new CredEx offer"""
        if not offer_data:
            return False, {"error": "Offer data is required"}

        try:
            # Remove any full_name field if present as it's not needed
            offer_data.pop("full_name", None)

            response = self._make_request(
                CredExEndpoints.CREATE_CREDEX,
                payload=offer_data
            )

            data = self._validate_response(response)
            if data.get("data", {}).get("action", {}).get("type") == "CREDEX_CREATED":
                logger.info("CredEx offer created successfully")
                return True, data
            else:
                logger.error("CredEx offer creation failed")
                return False, {"error": data.get("error", "Failed to create offer")}

        except TransactionError as e:
            logger.warning(f"Transaction error creating offer: {str(e)}")
            return False, {"error": str(e)}
        except Exception as e:
            logger.exception(f"CredEx offer creation failed: {str(e)}")
            return False, {"error": "An unexpected error occurred. Please try again."}

    def accept_credex(self, offer_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Accept a CredEx offer"""
        if not offer_id:
            return False, {"error": "Offer ID is required"}

        try:
            response = self._make_request(
                CredExEndpoints.ACCEPT_CREDEX,
                payload={"offerId": offer_id}
            )

            data = self._validate_response(response)
            if data.get("data", {}).get("action", {}).get("type") == "CREDEX_ACCEPTED":
                logger.info("CredEx offer accepted successfully")
                return True, data
            else:
                logger.error("CredEx offer acceptance failed")
                return False, {"error": data.get("error", "Failed to accept offer")}

        except TransactionError as e:
            logger.warning(f"Transaction error accepting offer: {str(e)}")
            return False, {"error": str(e)}
        except Exception as e:
            logger.exception(f"CredEx offer acceptance failed: {str(e)}")
            return False, {"error": "An unexpected error occurred. Please try again."}

    def accept_bulk_credex(self, offer_ids: List[str]) -> Tuple[bool, Dict[str, Any]]:
        """Accept multiple CredEx offers"""
        if not offer_ids:
            return False, {"error": "Offer IDs are required"}

        try:
            response = self._make_request(
                CredExEndpoints.ACCEPT_BULK_CREDEX,
                payload={"offerIds": offer_ids}
            )

            data = self._validate_response(response)
            if data.get("summary", {}).get("accepted"):
                logger.info("Bulk CredEx offers accepted successfully")
                return True, data
            else:
                logger.error("Bulk CredEx offer acceptance failed")
                return False, {"error": data.get("error", "Failed to accept offers")}

        except TransactionError as e:
            logger.warning(f"Transaction error accepting bulk offers: {str(e)}")
            return False, {"error": str(e)}
        except Exception as e:
            logger.exception(f"Bulk CredEx offer acceptance failed: {str(e)}")
            return False, {"error": "An unexpected error occurred. Please try again."}

    def decline_credex(self, offer_id: str) -> Tuple[bool, str]:
        """Decline a CredEx offer"""
        if not offer_id:
            return False, "Offer ID is required"

        try:
            response = self._make_request(
                CredExEndpoints.DECLINE_CREDEX,
                payload={"offerId": offer_id}
            )

            data = self._validate_response(response)
            if data.get("status") == "success":
                logger.info("CredEx offer declined successfully")
                return True, "Decline successful"
            else:
                logger.error("CredEx offer decline failed")
                return False, data.get("error", "Failed to decline offer")

        except TransactionError as e:
            logger.warning(f"Transaction error declining offer: {str(e)}")
            return False, str(e)
        except Exception as e:
            logger.exception(f"CredEx offer decline failed: {str(e)}")
            return False, "An unexpected error occurred. Please try again."

    def cancel_credex(self, offer_id: str) -> Tuple[bool, str]:
        """Cancel a CredEx offer"""
        if not offer_id:
            return False, "Offer ID is required"

        try:
            response = self._make_request(
                CredExEndpoints.CANCEL_CREDEX,
                payload={"offerId": offer_id}
            )

            data = self._validate_response(response)
            if data.get("message") == "Credex cancelled successfully":
                logger.info("CredEx offer cancelled successfully")
                return True, "Credex cancelled successfully"
            else:
                logger.error("CredEx offer cancellation failed")
                return False, data.get("error", "Failed to cancel offer")

        except TransactionError as e:
            logger.warning(f"Transaction error cancelling offer: {str(e)}")
            return False, str(e)
        except Exception as e:
            logger.exception(f"CredEx offer cancellation failed: {str(e)}")
            return False, "An unexpected error occurred. Please try again."

    def get_credex(self, offer_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Get details of a specific CredEx offer"""
        if not offer_id:
            return False, {"message": "Offer ID is required"}

        try:
            response = self._make_request(
                CredExEndpoints.GET_CREDEX,
                payload={"offerId": offer_id}
            )

            data = self._validate_response(response)
            if response.status_code == 200:
                logger.info("CredEx offer details fetched successfully")
                return True, data
            else:
                logger.error("CredEx offer details fetch failed")
                return False, {"message": data.get("message", "Failed to fetch offer details")}

        except TransactionError as e:
            logger.warning(f"Transaction error fetching offer: {str(e)}")
            return False, {"message": str(e)}
        except Exception as e:
            logger.exception(f"CredEx offer details fetch failed: {str(e)}")
            return False, {"message": "An unexpected error occurred. Please try again."}

    def get_ledger(self, member_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Get member's ledger information"""
        if not member_id:
            return False, {"message": "Member ID is required"}

        try:
            response = self._make_request(
                CredExEndpoints.GET_LEDGER,
                payload={"memberId": member_id}
            )

            data = self._validate_response(response)
            if response.status_code == 200:
                logger.info("Ledger fetched successfully")
                return True, data
            else:
                logger.error("Ledger fetch failed")
                return False, {"message": data.get("message", "Failed to fetch ledger")}

        except TransactionError as e:
            logger.warning(f"Transaction error fetching ledger: {str(e)}")
            return False, {"message": str(e)}
        except Exception as e:
            logger.exception(f"Ledger fetch failed: {str(e)}")
            return False, {"message": "An unexpected error occurred. Please try again."}
