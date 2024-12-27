"""CredEx service with strict state management"""
import logging
from typing import Any, Dict, List, Optional, Tuple, Callable

from .auth import CredExAuthService
from .config import CredExConfig
from .interface import CredExServiceInterface
from .member import CredExMemberService
from .offers import CredExOffersService
from .recurring import CredExRecurringService

logger = logging.getLogger(__name__)


class CredExService(CredExServiceInterface):
    """CredEx service with minimal state coupling"""

    def __init__(
        self,
        config: Optional[CredExConfig] = None,
        get_token: Optional[Callable[[], Optional[str]]] = None,
        get_member_id: Optional[Callable[[], Optional[str]]] = None,
        get_channel: Optional[Callable[[], Optional[Dict[str, Any]]]] = None,
        on_token_update: Optional[Callable[[str], None]] = None
    ):
        """Initialize CredEx service

        Args:
            config: Service configuration
            get_token: Function to get JWT token
            get_member_id: Function to get member ID
            get_channel: Function to get channel info
            on_token_update: Callback for token updates
        """
        # Share single config instance
        self.config = config or CredExConfig.from_env()

        # Store state access functions
        self._get_token = get_token
        self._get_member_id = get_member_id
        self._get_channel = get_channel
        self._on_token_update = on_token_update

        # Initialize services with shared config
        self.services = {
            'auth': CredExAuthService(config=self.config),
            'member': CredExMemberService(config=self.config),
            'offers': CredExOffersService(config=self.config),
            'recurring': CredExRecurringService(config=self.config)
        }

        # Initialize token if available
        if get_token and (token := get_token()):
            self._set_token(token)

    def _set_token(self, token: str) -> None:
        """Set token in services enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate input
            if not token:
                raise ValueError("Token is required")

            # Validate services
            if not self.services:
                raise ValueError("No services initialized")

            # Update services
            for service_name, service in self.services.items():
                if not service:
                    raise ValueError(f"Service {service_name} not initialized")
                service._jwt_token = token

            # Notify token update if callback provided
            if self._on_token_update:
                self._on_token_update(token)

            logger.info("Token updated successfully")

        except ValueError as e:
            logger.error(f"Token update error: {str(e)}")
            raise

    def update_token(self, token: str) -> None:
        """Update token enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate input
            if not token:
                raise ValueError("Token is required")

            # Update token
            self._set_token(token)

            logger.info("Token updated from external source")

        except ValueError as e:
            logger.error(f"External token update error: {str(e)}")
            raise

    def login(self, phone: str) -> Tuple[bool, str]:
        """Authenticate user enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate input
            if not phone:
                raise ValueError("Phone number is required")

            # Validate services
            if 'auth' not in self.services or not self.services['auth']:
                raise ValueError("Auth service not initialized")

            # Attempt login
            success, msg = self.services['auth'].login(phone)

            # Update token if successful
            if success:
                token = self.services['auth']._jwt_token
                if not token:
                    raise ValueError("No token received from auth service")
                self._set_token(token)
                logger.info(f"Login successful for phone {phone}")
            else:
                logger.warning(f"Login failed for phone {phone}: {msg}")

            return success, msg

        except ValueError as e:
            logger.error(f"Login error: {str(e)}")
            return False, str(e)

    def register_member(self, member_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Register new member enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate input
            if not isinstance(member_data, dict):
                raise ValueError("Member data must be a dictionary")
            if not member_data:
                raise ValueError("Member data is required")

            # Validate services
            if 'auth' not in self.services or not self.services['auth']:
                raise ValueError("Auth service not initialized")

            # Attempt registration
            success, msg = self.services['auth'].register_member(member_data)

            # Update token if successful
            if success:
                token = self.services['auth']._jwt_token
                if not token:
                    raise ValueError("No token received from auth service")
                self._set_token(token)
                logger.info("Member registration successful")
            else:
                logger.warning(f"Member registration failed: {msg}")

            return success, msg

        except ValueError as e:
            logger.error(f"Registration error: {str(e)}")
            return False, str(e)

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
        """Get JWT token enforcing SINGLE SOURCE OF TRUTH"""
        try:
            if not self._get_token:
                logger.warning("No token getter function provided")
                return None

            token = self._get_token()
            if not token:
                logger.debug("No token available")
                return None

            return token

        except Exception as e:
            logger.error(f"Token access error: {str(e)}")
            return None

    @property
    def member_id(self) -> Optional[str]:
        """Get member ID enforcing SINGLE SOURCE OF TRUTH"""
        try:
            if not self._get_member_id:
                logger.warning("No member ID getter function provided")
                return None

            member_id = self._get_member_id()
            if not member_id:
                logger.debug("No member ID available")
                return None

            return member_id

        except Exception as e:
            logger.error(f"Member ID access error: {str(e)}")
            return None

    @property
    def channel(self) -> Optional[Dict[str, Any]]:
        """Get channel info enforcing SINGLE SOURCE OF TRUTH"""
        try:
            if not self._get_channel:
                logger.warning("No channel getter function provided")
                return None

            channel = self._get_channel()
            if not channel:
                logger.debug("No channel info available")
                return None

            if not isinstance(channel, dict):
                raise ValueError("Invalid channel info format")

            return channel

        except Exception as e:
            logger.error(f"Channel info access error: {str(e)}")
            return None

    def validate_initialization(self) -> Optional[str]:
        """Validate service initialization enforcing SINGLE SOURCE OF TRUTH

        Returns:
            Optional[str]: Error message if validation fails
        """
        try:
            # Validate config
            if not self.config:
                return "Service configuration not initialized"

            # Validate services
            if not self.services:
                return "No services initialized"

            # Validate each service
            for service_name, service in self.services.items():
                if not service:
                    return f"Service {service_name} not initialized"

            # Validate state access functions
            if not self._get_token:
                logger.warning("No token getter function provided")
            if not self._get_member_id:
                logger.warning("No member ID getter function provided")
            if not self._get_channel:
                logger.warning("No channel getter function provided")

            logger.info("Service initialization validated successfully")
            return None

        except Exception as e:
            error_msg = f"Service validation error: {str(e)}"
            logger.error(error_msg)
            return error_msg
