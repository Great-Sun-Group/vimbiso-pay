import logging
from typing import Any, Dict, List, Tuple

from .base import BaseCredExService
from .exceptions import ValidationError

logger = logging.getLogger(__name__)


class CredExOffersService(BaseCredExService):
    """Service for CredEx offer operations"""

    def _process_offer_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process offer data for API compatibility"""
        offer = data.copy()
        offer.pop("full_name", None)

        # Convert field names
        if "denomination" in offer:
            offer["Denomination"] = offer.pop("denomination")
        if "amount" in offer:
            offer["InitialAmount"] = offer.pop("amount")

        # Add required fields
        offer.update({
            "credexType": "PURCHASE",
            "OFFERSorREQUESTS": "OFFERS",
            "securedCredex": offer.get("securedCredex", True)
        })

        return offer

    def _check_success(self, data: Dict[str, Any], action_type: str) -> bool:
        """Check if response indicates success"""
        return (
            data.get("data", {}).get("action", {}).get("type") == action_type or
            data.get("message", "").lower().startswith(f"credex {action_type.split('_')[1].lower()} successfully")
        )

    def offer_credex(self, offer_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Create new CredEx offer"""
        if not offer_data:
            raise ValidationError("Offer data is required")

        try:
            processed_data = self._process_offer_data(offer_data)
            response = self._make_request('credex', 'create', payload=processed_data)
            data = response.json()

            if self._check_success(data, "CREDEX_CREATED"):
                if credex_id := data.get("data", {}).get("action", {}).get("id"):
                    data.setdefault("data", {}).setdefault("action", {}).update({
                        "credexID": credex_id,
                        "message": f"CredEx offer {credex_id} created successfully"
                    })
                    return True, data
            return False, {"message": "Failed to create offer"}

        except Exception as e:
            logger.error(f"Offer creation failed: {str(e)}")
            return False, {"message": str(e)}

    def confirm_credex(self, credex_id: str, issuer_account_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Confirm CredEx offer"""
        if not credex_id or not issuer_account_id:
            raise ValidationError("CredEx ID and Account ID are required")

        try:
            response = self._make_request(
                'credex', 'confirm',
                payload={"credexID": credex_id, "issuerAccountID": issuer_account_id}
            )
            data = response.json()

            if self._check_success(data, "CREDEX_ACCEPTED"):
                return True, data
            return False, {"message": "Failed to confirm offer"}

        except Exception as e:
            logger.error(f"Offer confirmation failed: {str(e)}")
            return False, {"message": str(e)}

    def accept_credex(self, credex_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Accept CredEx offer"""
        if not credex_id:
            raise ValidationError("CredEx ID is required")

        try:
            response = self._make_request(
                'credex', 'accept',
                payload={"credexID": credex_id}
            )
            data = response.json()

            if self._check_success(data, "CREDEX_ACCEPTED"):
                return True, data
            return False, {"message": "Failed to accept offer"}

        except Exception as e:
            logger.error(f"Offer acceptance failed: {str(e)}")
            return False, {"message": str(e)}

    def accept_bulk_credex(self, credex_ids: List[str]) -> Tuple[bool, Dict[str, Any]]:
        """Accept multiple CredEx offers"""
        if not credex_ids:
            raise ValidationError("CredEx IDs are required")

        try:
            response = self._make_request(
                'credex', 'accept_bulk',
                payload={"credexIDs": credex_ids}
            )
            data = response.json()

            if data.get("summary", {}).get("accepted"):
                return True, data
            return False, {"message": "Failed to accept offers"}

        except Exception as e:
            logger.error(f"Bulk acceptance failed: {str(e)}")
            return False, {"message": str(e)}

    def decline_credex(self, credex_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Decline CredEx offer"""
        if not credex_id:
            raise ValidationError("CredEx ID is required")

        try:
            response = self._make_request(
                'credex', 'decline',
                payload={"credexID": credex_id}
            )
            data = response.json()

            if self._check_success(data, "CREDEX_DECLINED"):
                return True, data
            return False, {"message": "Failed to decline offer"}

        except Exception as e:
            logger.error(f"Offer decline failed: {str(e)}")
            return False, {"message": str(e)}

    def cancel_credex(self, credex_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Cancel CredEx offer"""
        if not credex_id:
            raise ValidationError("CredEx ID is required")

        try:
            response = self._make_request(
                'credex', 'cancel',
                payload={"credexID": credex_id}
            )
            data = response.json()

            if self._check_success(data, "CREDEX_CANCELLED"):
                return True, data
            return False, {"message": "Failed to cancel offer"}

        except Exception as e:
            logger.error(f"Offer cancellation failed: {str(e)}")
            return False, {"message": str(e)}

    def get_credex(self, credex_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Get CredEx offer details"""
        if not credex_id:
            raise ValidationError("CredEx ID is required")

        try:
            response = self._make_request(
                'credex', 'get',
                payload={"credexID": credex_id}
            )
            data = response.json()

            if data.get("data"):
                return True, data
            return False, {"message": "Failed to get offer details"}

        except Exception as e:
            logger.error(f"Offer details fetch failed: {str(e)}")
            return False, {"message": str(e)}

    def get_ledger(self, member_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Get member ledger"""
        if not member_id:
            raise ValidationError("Member ID is required")

        try:
            response = self._make_request(
                'credex', 'get_ledger',
                payload={"memberId": member_id}
            )
            data = response.json()

            if data.get("data"):
                return True, data
            return False, {"message": "Failed to get ledger"}

        except Exception as e:
            logger.error(f"Ledger fetch failed: {str(e)}")
            return False, {"message": str(e)}
