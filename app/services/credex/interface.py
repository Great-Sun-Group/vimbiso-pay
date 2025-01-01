from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple


class CredExServiceInterface(ABC):
    """Interface defining CredEx service operations"""

    @abstractmethod
    def login(self, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Authenticate user with the CredEx API

        Args:
            state_manager: State manager instance containing channel info and flow data

        Returns:
            Tuple of (success: bool, response: Dict[str, Any])
        """
        pass

    @abstractmethod
    def register_member(self, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Register a new member

        Args:
            state_manager: State manager instance containing member registration info

        Returns:
            Tuple of (success: bool, response: Dict[str, Any])
        """
        pass

    @abstractmethod
    def get_dashboard(self, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Fetch member's dashboard information

        Args:
            state_manager: State manager instance containing member info

        Returns:
            Tuple of (success: bool, dashboard_data: Dict[str, Any])
        """
        pass

    @abstractmethod
    def validate_account_handle(self, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Validate a CredEx handle

        Args:
            state_manager: State manager instance containing handle to validate

        Returns:
            Tuple of (success: bool, validation_data: Dict)
        """
        pass

    @abstractmethod
    def offer_credex(self, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Create a new CredEx offer

        Args:
            state_manager: State manager instance containing offer details

        Returns:
            Tuple of (success: bool, offer_result: Dict)
        """
        pass

    @abstractmethod
    def accept_credex(self, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Accept a CredEx offer

        Args:
            state_manager: State manager instance containing offer ID

        Returns:
            Tuple of (success: bool, acceptance_result: Dict)
        """
        pass

    @abstractmethod
    def accept_bulk_credex(self, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Accept multiple CredEx offers

        Args:
            state_manager: State manager instance containing list of offer IDs

        Returns:
            Tuple of (success: bool, acceptance_result: Dict)
        """
        pass

    @abstractmethod
    def decline_credex(self, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Decline a CredEx offer

        Args:
            state_manager: State manager instance containing offer ID

        Returns:
            Tuple of (success: bool, message: str)
        """
        pass

    @abstractmethod
    def cancel_credex(self, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Cancel a CredEx offer

        Args:
            state_manager: State manager instance containing offer ID

        Returns:
            Tuple of (success: bool, message: str)
        """
        pass

    @abstractmethod
    def get_credex(self, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Get details of a specific CredEx offer

        Args:
            state_manager: State manager instance containing offer ID

        Returns:
            Tuple of (success: bool, offer_details: Dict)
        """
        pass

    @abstractmethod
    def get_ledger(self, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Get member's ledger information

        Args:
            state_manager: State manager instance containing member ID

        Returns:
            Tuple of (success: bool, ledger_data: Dict)
        """
        pass

    @abstractmethod
    def refresh_member_info(self, state_manager: Any) -> Optional[str]:
        """Refresh member information

        Args:
            state_manager: State manager instance containing member info

        Returns:
            Optional error message if refresh fails
        """
        pass

    @abstractmethod
    def get_member_accounts(self, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Get available accounts for a member

        Args:
            state_manager: State manager instance containing member ID

        Returns:
            Tuple[bool, Dict[str, Any]]: (success, accounts_data) where accounts_data contains
            a list of accounts with their details including ID, name, type, and denomination
        """
        pass


class CredExRecurringInterface(ABC):
    """Interface defining recurring payment operations"""

    @abstractmethod
    def create_recurring(self, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Create a recurring payment

        Args:
            state_manager: State manager instance containing:
                - sourceAccountID: ID of the source account
                - templateType: Type of recurring payment template
                - payFrequency: Payment frequency in days
                - startDate: Start date for recurring payment
                - memberTier: Target member tier (for subscriptions)
                - securedCredex: Whether credex is secured
                - amount: Payment amount
                - denomination: Payment denomination

        Returns:
            Tuple[bool, Dict[str, Any]]: Success flag and response data
        """
        pass

    @abstractmethod
    def accept_recurring(self, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Accept a recurring payment

        Args:
            state_manager: State manager instance containing payment ID

        Returns:
            Tuple[bool, Dict[str, Any]]: Success flag and response data
        """
        pass

    @abstractmethod
    def cancel_recurring(self, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Cancel a recurring payment

        Args:
            state_manager: State manager instance containing payment ID

        Returns:
            Tuple[bool, Dict[str, Any]]: Success flag and response data
        """
        pass

    @abstractmethod
    def get_recurring(self, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Get details of a recurring payment

        Args:
            state_manager: State manager instance containing payment ID

        Returns:
            Tuple[bool, Dict[str, Any]]: Success flag and response data
        """
        pass
