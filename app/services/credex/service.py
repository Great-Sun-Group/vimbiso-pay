import logging
from typing import Any, Dict, List, Optional, Tuple

from .auth import CredExAuthService
from .config import CredExConfig
from .interface import CredExServiceInterface
from .member import CredExMemberService
from .offers import CredExOffersService
from .recurring import CredExRecurringService

logger = logging.getLogger(__name__)


class CredExService(CredExServiceInterface):
    """Main CredEx service that combines all operations"""

    def __init__(self, config: Optional[CredExConfig] = None, user: Any = None):
        """Initialize the CredEx service with all sub-services

        Args:
            config: Service configuration. If not provided, loads from environment.
            user: Dictionary containing state data
        """
        self.config = config or CredExConfig.from_env()
        self._jwt_token = None
        self.user = user  # Store user instance from parent
        self._parent_service = None  # Will be set by parent service

        # Log initialization
        logger.debug("Initializing CredEx service:")
        logger.debug(f"- Has user: {bool(user)}")
        if user and isinstance(user, dict) and 'state' in user:
            logger.debug("- User has state: True")
            logger.debug(f"- User state: {user['state']}")
        else:
            logger.debug("- User has state: False")
            logger.debug("- User state: None")

        # Initialize sub-services with parent reference
        self._auth = CredExAuthService(config=self.config)
        self._auth._parent_service = self
        self._auth._jwt_token = self._jwt_token

        self._member = CredExMemberService(config=self.config)
        self._member._parent_service = self
        self._member._jwt_token = self._jwt_token

        self._offers = CredExOffersService(config=self.config)
        self._offers._parent_service = self
        self._offers._jwt_token = self._jwt_token

        self._recurring = CredExRecurringService(config=self.config)
        self._recurring._parent_service = self
        self._recurring._jwt_token = self._jwt_token

        # Get token from user state if available
        if user and isinstance(user, dict) and 'state' in user:
            state_data = user['state']
            if isinstance(state_data, dict) and 'jwt_token' in state_data:
                token = state_data['jwt_token']
                if token:
                    logger.debug("Setting token from user state")
                    self.jwt_token = token

    def login(self, phone: str) -> Tuple[bool, str]:
        """Authenticate user with the CredEx API"""
        success, msg = self._auth.login(phone)
        if success:
            # Get token from auth service
            token = self._auth.jwt_token
            # Update token in state and propagate to services
            if self.user and isinstance(self.user, dict) and 'state' in self.user and token:
                self.user['state']['jwt_token'] = token
                self.jwt_token = token
        return success, msg

    def register_member(self, member_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Register a new member"""
        success, msg = self._auth.register_member(member_data)
        if success:
            # Get token from auth service
            token = self._auth.jwt_token
            # Update token in state and propagate to services
            if self.user and isinstance(self.user, dict) and 'state' in self.user and token:
                self.user['state']['jwt_token'] = token
                self.jwt_token = token
        return success, msg

    def get_dashboard(self, phone: str) -> Tuple[bool, Dict[str, Any]]:
        """Fetch member's dashboard information"""
        return self._member.get_dashboard(phone)

    def validate_handle(self, handle: str) -> Tuple[bool, Dict[str, Any]]:
        """Validate a CredEx handle"""
        return self._member.validate_handle(handle)

    def offer_credex(self, offer_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Create a new CredEx offer"""
        return self._offers.offer_credex(offer_data)

    def confirm_credex(self, credex_id: str, issuer_account_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Confirm a CredEx offer"""
        return self._offers.confirm_credex(credex_id, issuer_account_id)

    def accept_credex(self, offer_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Accept a CredEx offer"""
        return self._offers.accept_credex(offer_id)

    def accept_bulk_credex(self, offer_ids: List[str]) -> Tuple[bool, Dict[str, Any]]:
        """Accept multiple CredEx offers"""
        return self._offers.accept_bulk_credex(offer_ids)

    def decline_credex(self, offer_id: str) -> Tuple[bool, str]:
        """Decline a CredEx offer"""
        return self._offers.decline_credex(offer_id)

    def cancel_credex(self, offer_id: str) -> Tuple[bool, str]:
        """Cancel a CredEx offer"""
        return self._offers.cancel_credex(offer_id)

    def get_credex(self, offer_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Get details of a specific CredEx offer"""
        return self._offers.get_credex(offer_id)

    def get_ledger(self, member_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Get member's ledger information"""
        return self._offers.get_ledger(member_id)

    def refresh_member_info(
        self, phone: str, reset: bool = True, silent: bool = True, init: bool = False
    ) -> Optional[str]:
        """Refresh member information"""
        return self._member.refresh_member_info(phone, reset, silent, init)

    def get_member_accounts(self, member_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Get available accounts for a member"""
        return self._member.get_member_accounts(member_id)

    def list_transactions(
        self,
        filters: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """List transactions matching the given criteria

        Args:
            filters: Dictionary containing filter criteria:
                - member_id: ID of the member
                - account_id: Optional account ID to filter by
                - status: Optional status to filter by
                - start_date: Optional start date for filtering
                - end_date: Optional end date for filtering

        Returns:
            Tuple of (success, response_data)
        """
        return self._offers.list_transactions(filters)

    @property
    def jwt_token(self) -> Optional[str]:
        """Get the current JWT token"""
        return self._jwt_token

    @jwt_token.setter
    def jwt_token(self, value: str):
        """Set the JWT token"""
        # Set token directly without triggering state update
        self._jwt_token = value
        # Propagate to sub-services
        if hasattr(self, '_auth'):
            self._auth._jwt_token = value
        if hasattr(self, '_member'):
            self._member._jwt_token = value
        if hasattr(self, '_offers'):
            self._offers._jwt_token = value
        if hasattr(self, '_recurring'):
            self._recurring._jwt_token = value
