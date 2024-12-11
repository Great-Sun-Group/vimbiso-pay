from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from .types import (
    Account,
    AccountMember,
    AccountInvite,
    AccountRole,
    AccountSettings,
    AccountUpdateResult,
    AccountMemberResult,
    AccountInviteResult,
)


class AccountServiceInterface(ABC):
    """Interface defining account service operations"""

    @abstractmethod
    def create_account(
        self,
        name: str,
        owner_id: str,
        account_type: str,
        settings: AccountSettings,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AccountUpdateResult:
        """Create a new account

        Args:
            name: Name of the account
            owner_id: ID of the account owner
            account_type: Type of account to create
            settings: Account settings
            metadata: Optional additional data

        Returns:
            Result of account creation
        """
        pass

    @abstractmethod
    def update_account(
        self,
        account_id: str,
        updates: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> AccountUpdateResult:
        """Update an existing account

        Args:
            account_id: ID of account to update
            updates: Fields to update
            metadata: Optional additional data

        Returns:
            Result of account update
        """
        pass

    @abstractmethod
    def delete_account(self, account_id: str) -> AccountUpdateResult:
        """Delete an account

        Args:
            account_id: ID of account to delete

        Returns:
            Result of account deletion
        """
        pass

    @abstractmethod
    def get_account(self, account_id: str) -> Account:
        """Get account information

        Args:
            account_id: ID of account to retrieve

        Returns:
            Account information

        Raises:
            AccountNotFoundError: If account doesn't exist
        """
        pass

    @abstractmethod
    def list_accounts(
        self,
        member_id: Optional[str] = None,
        account_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Account]:
        """List accounts matching criteria

        Args:
            member_id: Optional member ID to filter by
            account_type: Optional account type to filter by
            status: Optional status to filter by

        Returns:
            List of matching accounts
        """
        pass

    @abstractmethod
    def add_member(
        self,
        account_id: str,
        member_id: str,
        role: AccountRole,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AccountMemberResult:
        """Add a member to an account

        Args:
            account_id: ID of the account
            member_id: ID of the member to add
            role: Role to assign to member
            metadata: Optional additional data

        Returns:
            Result of member addition
        """
        pass

    @abstractmethod
    def remove_member(
        self,
        account_id: str,
        member_id: str
    ) -> AccountMemberResult:
        """Remove a member from an account

        Args:
            account_id: ID of the account
            member_id: ID of the member to remove

        Returns:
            Result of member removal
        """
        pass

    @abstractmethod
    def update_member_role(
        self,
        account_id: str,
        member_id: str,
        new_role: AccountRole
    ) -> AccountMemberResult:
        """Update a member's role in an account

        Args:
            account_id: ID of the account
            member_id: ID of the member
            new_role: New role to assign

        Returns:
            Result of role update
        """
        pass

    @abstractmethod
    def get_member(
        self,
        account_id: str,
        member_id: str
    ) -> AccountMember:
        """Get member information

        Args:
            account_id: ID of the account
            member_id: ID of the member

        Returns:
            Member information

        Raises:
            AccountMemberNotFoundError: If member doesn't exist
        """
        pass

    @abstractmethod
    def list_members(
        self,
        account_id: str,
        role: Optional[AccountRole] = None
    ) -> List[AccountMember]:
        """List members in an account

        Args:
            account_id: ID of the account
            role: Optional role to filter by

        Returns:
            List of matching members
        """
        pass

    @abstractmethod
    def create_invite(
        self,
        account_id: str,
        inviter_id: str,
        invitee_handle: str,
        role: AccountRole,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AccountInviteResult:
        """Create an account invite

        Args:
            account_id: ID of the account
            inviter_id: ID of the member creating invite
            invitee_handle: Handle of user to invite
            role: Role to assign if accepted
            metadata: Optional additional data

        Returns:
            Result of invite creation
        """
        pass

    @abstractmethod
    def accept_invite(
        self,
        invite_id: str,
        member_id: str
    ) -> AccountInviteResult:
        """Accept an account invite

        Args:
            invite_id: ID of the invite
            member_id: ID of accepting member

        Returns:
            Result of invite acceptance
        """
        pass

    @abstractmethod
    def reject_invite(
        self,
        invite_id: str,
        member_id: str
    ) -> AccountInviteResult:
        """Reject an account invite

        Args:
            invite_id: ID of the invite
            member_id: ID of rejecting member

        Returns:
            Result of invite rejection
        """
        pass

    @abstractmethod
    def get_invite(self, invite_id: str) -> AccountInvite:
        """Get invite information

        Args:
            invite_id: ID of invite to retrieve

        Returns:
            Invite information

        Raises:
            AccountInviteError: If invite doesn't exist
        """
        pass

    @abstractmethod
    def list_invites(
        self,
        account_id: Optional[str] = None,
        member_id: Optional[str] = None
    ) -> List[AccountInvite]:
        """List invites matching criteria

        Args:
            account_id: Optional account ID to filter by
            member_id: Optional member ID to filter by

        Returns:
            List of matching invites
        """
        pass

    @abstractmethod
    def update_settings(
        self,
        account_id: str,
        settings: AccountSettings
    ) -> AccountUpdateResult:
        """Update account settings

        Args:
            account_id: ID of the account
            settings: New settings

        Returns:
            Result of settings update
        """
        pass

    @abstractmethod
    def validate_account(self, account: Account) -> bool:
        """Validate account information

        Args:
            account: Account to validate

        Returns:
            True if valid, False otherwise
        """
        pass

    @abstractmethod
    def validate_member(
        self,
        account_id: str,
        member: AccountMember
    ) -> bool:
        """Validate member information

        Args:
            account_id: ID of the account
            member: Member to validate

        Returns:
            True if valid, False otherwise
        """
        pass

    @abstractmethod
    def validate_settings(
        self,
        account_id: str,
        settings: AccountSettings
    ) -> bool:
        """Validate account settings

        Args:
            account_id: ID of the account
            settings: Settings to validate

        Returns:
            True if valid, False otherwise
        """
        pass
