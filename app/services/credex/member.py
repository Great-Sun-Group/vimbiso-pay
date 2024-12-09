import logging
from typing import Any, Dict, Optional, Tuple

from .base import BaseCredExService
from .config import CredExEndpoints
from .exceptions import (
    InvalidHandleError,
    MemberNotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class CredExMemberService(BaseCredExService):
    """Service for CredEx member operations"""

    def get_dashboard(self, phone: str) -> Tuple[bool, Dict[str, Any]]:
        """Fetch member's dashboard information"""
        if not phone:
            raise ValidationError("Phone number is required")

        try:
            response = self._make_request(
                CredExEndpoints.DASHBOARD,
                payload={"phone": phone}
            )

            data = self._validate_response(response, {
                400: "Invalid request",
                401: "Unauthorized access",
                404: "Member not found"
            })

            if response.status_code == 200:
                logger.info("Dashboard fetched successfully")
                return True, data
            else:
                error_msg = data.get("message", "Failed to fetch dashboard")
                logger.error(f"Dashboard fetch failed: {error_msg}")
                if "Member not found" in error_msg:
                    raise MemberNotFoundError(error_msg)
                return False, {"message": error_msg}

        except MemberNotFoundError as e:
            logger.warning(f"Member not found: {str(e)}")
            return False, {"message": str(e)}
        except Exception as e:
            logger.exception(f"Dashboard fetch failed: {str(e)}")
            return False, {"message": f"Failed to fetch dashboard: {str(e)}"}

    def validate_handle(self, handle: str) -> Tuple[bool, Dict[str, Any]]:
        """Validate a CredEx handle"""
        if not handle:
            raise ValidationError("Handle is required")

        try:
            response = self._make_request(
                CredExEndpoints.VALIDATE_HANDLE,
                payload={"accountHandle": handle.lower()}
            )

            data = self._validate_response(response, {
                400: "Invalid handle format",
                404: "Handle not found"
            })

            if response.status_code == 200:
                if not data.get("Error"):
                    logger.info("Handle validation successful")
                    return True, data
                else:
                    logger.error("Handle validation failed")
                    raise InvalidHandleError(data.get("Error", "Invalid handle"))
            else:
                error_msg = data.get("message", "Handle validation failed")
                logger.error(f"Handle validation failed: {error_msg}")
                return False, {"message": error_msg}

        except InvalidHandleError as e:
            logger.warning(f"Invalid handle: {str(e)}")
            return False, {"message": str(e)}
        except Exception as e:
            logger.exception(f"Handle validation failed: {str(e)}")
            return False, {"message": f"Failed to validate handle: {str(e)}"}

    def refresh_member_info(
        self, phone: str, reset: bool = True, silent: bool = True, init: bool = False
    ) -> Optional[str]:
        """Refresh member information"""
        if not phone:
            raise ValidationError("Phone number is required")

        try:
            success, data = self.get_dashboard(phone)
            if not success:
                error_msg = data.get("message", "Failed to refresh member info")
                logger.error(f"Member info refresh failed: {error_msg}")
                return error_msg

            logger.info("Member info refreshed successfully")
            return None

        except Exception as e:
            logger.exception("Unexpected error refreshing member info")
            return f"Failed to refresh member info: {str(e)}"
