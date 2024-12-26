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
    """CredEx service with minimal state coupling"""

    def __init__(self, config: Optional[CredExConfig] = None, state_manager: Any = None):
        """Initialize CredEx service

        Args:
            config: Service configuration
            state_manager: State manager for token storage
        """
        # Share single config instance
        self.config = config or CredExConfig.from_env()
        self.state_manager = state_manager

        # Initialize services with shared config
        self.services = {
            'auth': CredExAuthService(config=self.config),
            'member': CredExMemberService(config=self.config),
            'offers': CredExOffersService(config=self.config),
            'recurring': CredExRecurringService(config=self.config)
        }

        # Initialize token if available
        if state_manager and (token := state_manager.jwt_token):
            self._set_token(token)

    def _set_token(self, token: str) -> None:
        """Set token in services and state"""
        # Update services
        for service in self.services.values():
            service._jwt_token = token
        # Update state if available
        if self.state_manager:
            self.state_manager.update_state({"jwt_token": token})

    def login(self, phone: str) -> Tuple[bool, str]:
        """Authenticate user"""
        success, msg = self.services['auth'].login(phone)
        if success and (token := self.services['auth']._jwt_token):
            self._set_token(token)
        return success, msg

    def register_member(self, member_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Register new member"""
        success, msg = self.services['auth'].register_member(member_data)
        if success and (token := self.services['auth']._jwt_token):
            self._set_token(token)
        return success, msg

    # Delegate other methods to appropriate services
    def get_dashboard(self, phone: str) -> Tuple[bool, Dict[str, Any]]:
        return self.services['member'].get_dashboard(phone)

    def validate_handle(self, handle: str) -> Tuple[bool, Dict[str, Any]]:
        return self.services['member'].validate_handle(handle)

    def offer_credex(self, offer_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        return self.services['offers'].offer_credex(offer_data)

    def confirm_credex(self, credex_id: str, issuer_account_id: str) -> Tuple[bool, Dict[str, Any]]:
        return self.services['offers'].confirm_credex(credex_id, issuer_account_id)

    def accept_credex(self, offer_id: str) -> Tuple[bool, Dict[str, Any]]:
        return self.services['offers'].accept_credex(offer_id)

    def accept_bulk_credex(self, offer_ids: List[str]) -> Tuple[bool, Dict[str, Any]]:
        return self.services['offers'].accept_bulk_credex(offer_ids)

    def decline_credex(self, offer_id: str) -> Tuple[bool, str]:
        return self.services['offers'].decline_credex(offer_id)

    def cancel_credex(self, offer_id: str) -> Tuple[bool, str]:
        return self.services['offers'].cancel_credex(offer_id)

    def get_credex(self, offer_id: str) -> Tuple[bool, Dict[str, Any]]:
        return self.services['offers'].get_credex(offer_id)

    def get_ledger(self, member_id: str) -> Tuple[bool, Dict[str, Any]]:
        return self.services['offers'].get_ledger(member_id)

    def refresh_member_info(
        self, phone: str, reset: bool = True, silent: bool = True, init: bool = False
    ) -> Optional[str]:
        return self.services['member'].refresh_member_info(phone, reset, silent, init)

    def get_member_accounts(self, member_id: str) -> Tuple[bool, Dict[str, Any]]:
        return self.services['member'].get_member_accounts(member_id)

    def list_transactions(self, filters: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        return self.services['offers'].list_transactions(filters)

    @property
    def jwt_token(self) -> Optional[str]:
        """Get JWT token from state manager"""
        return self.state_manager.jwt_token if self.state_manager else None
