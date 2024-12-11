import logging
from datetime import datetime
from typing import Dict, Any, Optional

from .exceptions import (
    AccountError,
    AccountValidationError,
    InvalidAccountTypeError,
    InvalidAccountStatusError,
    InvalidAccountRoleError,
    AccountMemberNotFoundError,
    AccountPermissionError,
    AccountInviteError,
    DuplicateAccountError,
    AccountSettingsError,
    AccountStateError,
)
from .interface import AccountServiceInterface
from .types import (
    Account,
    AccountMember,
    AccountRole,
    AccountSettings,
    AccountType,
    AccountStatus,
    AccountUpdateResult,
    AccountMemberResult,
    AccountInviteResult,
)

logger = logging.getLogger(__name__)


class BaseAccountService(AccountServiceInterface):
    """Base class implementing common account functionality"""

    def create_account(
        self,
        name: str,
        owner_id: str,
        account_type: str,
        settings: AccountSettings,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AccountUpdateResult:
        """Create a new account"""
        try:
            # Validate inputs
            if not name or not owner_id:
                raise AccountValidationError("Name and owner ID are required")

            try:
                account_type_enum = AccountType(account_type.lower())
            except ValueError:
                raise InvalidAccountTypeError(f"Invalid account type: {account_type}")

            if not self.validate_settings(None, settings):
                raise AccountSettingsError("Invalid account settings")

            # Create account
            return self._create_account_internal(
                name=name,
                owner_id=owner_id,
                account_type=account_type_enum,
                settings=settings,
                metadata=metadata or {}
            )
        except AccountError as e:
            logger.error(f"Failed to create account: {str(e)}")
            return AccountUpdateResult(success=False, error_message=str(e))
        except Exception as e:
            logger.error(f"Unexpected error creating account: {str(e)}")
            return AccountUpdateResult(success=False, error_message="Internal error")

    def update_account(
        self,
        account_id: str,
        updates: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> AccountUpdateResult:
        """Update an existing account"""
        try:
            # Validate account exists
            self.get_account(account_id)

            # Apply and validate updates
            for key, value in updates.items():
                if key == "type":
                    try:
                        AccountType(value.lower())
                    except ValueError:
                        raise InvalidAccountTypeError(f"Invalid account type: {value}")
                elif key == "status":
                    try:
                        AccountStatus(value.lower())
                    except ValueError:
                        raise InvalidAccountStatusError(f"Invalid account status: {value}")
                elif key == "settings":
                    if not self.validate_settings(account_id, value):
                        raise AccountSettingsError("Invalid account settings")

            # Update account
            return self._update_account_internal(
                account_id=account_id,
                updates=updates,
                metadata=metadata or {}
            )
        except AccountError as e:
            logger.error(f"Failed to update account: {str(e)}")
            return AccountUpdateResult(success=False, error_message=str(e))
        except Exception as e:
            logger.error(f"Unexpected error updating account: {str(e)}")
            return AccountUpdateResult(success=False, error_message="Internal error")

    def delete_account(self, account_id: str) -> AccountUpdateResult:
        """Delete an account"""
        try:
            # Validate account exists and check status
            account = self.get_account(account_id)
            if account.status == AccountStatus.CLOSED:
                raise AccountStateError("Account is already closed")

            # Delete account
            return self._delete_account_internal(account_id)
        except AccountError as e:
            logger.error(f"Failed to delete account: {str(e)}")
            return AccountUpdateResult(success=False, error_message=str(e))
        except Exception as e:
            logger.error(f"Unexpected error deleting account: {str(e)}")
            return AccountUpdateResult(success=False, error_message="Internal error")

    def add_member(
        self,
        account_id: str,
        member_id: str,
        role: AccountRole,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AccountMemberResult:
        """Add a member to an account"""
        try:
            # Validate account exists
            self.get_account(account_id)

            # Validate role
            if not isinstance(role, AccountRole):
                raise InvalidAccountRoleError(f"Invalid role: {role}")

            # Check member not already in account
            try:
                if self.get_member(account_id, member_id):
                    raise DuplicateAccountError("Member already exists in account")
            except AccountMemberNotFoundError:
                pass  # Expected - member should not exist

            # Add member
            return self._add_member_internal(
                account_id=account_id,
                member_id=member_id,
                role=role,
                metadata=metadata or {}
            )
        except AccountError as e:
            logger.error(f"Failed to add member: {str(e)}")
            return AccountMemberResult(success=False, error_message=str(e))
        except Exception as e:
            logger.error(f"Unexpected error adding member: {str(e)}")
            return AccountMemberResult(success=False, error_message="Internal error")

    def remove_member(
        self,
        account_id: str,
        member_id: str
    ) -> AccountMemberResult:
        """Remove a member from an account"""
        try:
            # Validate member exists
            self.get_member(account_id, member_id)

            # Check not removing owner
            account = self.get_account(account_id)
            if member_id == account.owner_id:
                raise AccountPermissionError("Cannot remove account owner")

            # Remove member
            return self._remove_member_internal(account_id, member_id)
        except AccountError as e:
            logger.error(f"Failed to remove member: {str(e)}")
            return AccountMemberResult(success=False, error_message=str(e))
        except Exception as e:
            logger.error(f"Unexpected error removing member: {str(e)}")
            return AccountMemberResult(success=False, error_message="Internal error")

    def update_member_role(
        self,
        account_id: str,
        member_id: str,
        new_role: AccountRole
    ) -> AccountMemberResult:
        """Update a member's role"""
        try:
            # Validate member exists
            self.get_member(account_id, member_id)

            # Validate role
            if not isinstance(new_role, AccountRole):
                raise InvalidAccountRoleError(f"Invalid role: {new_role}")

            # Check not changing owner's role
            account = self.get_account(account_id)
            if member_id == account.owner_id and new_role != AccountRole.OWNER:
                raise AccountPermissionError("Cannot change owner's role")

            # Update role
            return self._update_member_role_internal(account_id, member_id, new_role)
        except AccountError as e:
            logger.error(f"Failed to update member role: {str(e)}")
            return AccountMemberResult(success=False, error_message=str(e))
        except Exception as e:
            logger.error(f"Unexpected error updating member role: {str(e)}")
            return AccountMemberResult(success=False, error_message="Internal error")

    def create_invite(
        self,
        account_id: str,
        inviter_id: str,
        invitee_handle: str,
        role: AccountRole,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AccountInviteResult:
        """Create an account invite"""
        try:
            # Validate account exists
            self.get_account(account_id)

            # Validate inviter is member
            self.get_member(account_id, inviter_id)

            # Validate role
            if not isinstance(role, AccountRole):
                raise InvalidAccountRoleError(f"Invalid role: {role}")

            # Create invite
            return self._create_invite_internal(
                account_id=account_id,
                inviter_id=inviter_id,
                invitee_handle=invitee_handle,
                role=role,
                metadata=metadata or {}
            )
        except AccountError as e:
            logger.error(f"Failed to create invite: {str(e)}")
            return AccountInviteResult(success=False, error_message=str(e))
        except Exception as e:
            logger.error(f"Unexpected error creating invite: {str(e)}")
            return AccountInviteResult(success=False, error_message="Internal error")

    def accept_invite(
        self,
        invite_id: str,
        member_id: str
    ) -> AccountInviteResult:
        """Accept an account invite"""
        try:
            # Get and validate invite
            invite = self.get_invite(invite_id)
            if invite.accepted_at or invite.rejected_at:
                raise AccountInviteError("Invite already processed")
            if invite.expires_at < datetime.now():
                raise AccountInviteError("Invite expired")

            # Accept invite
            return self._accept_invite_internal(invite_id, member_id)
        except AccountError as e:
            logger.error(f"Failed to accept invite: {str(e)}")
            return AccountInviteResult(success=False, error_message=str(e))
        except Exception as e:
            logger.error(f"Unexpected error accepting invite: {str(e)}")
            return AccountInviteResult(success=False, error_message="Internal error")

    def reject_invite(
        self,
        invite_id: str,
        member_id: str
    ) -> AccountInviteResult:
        """Reject an account invite"""
        try:
            # Get and validate invite
            invite = self.get_invite(invite_id)
            if invite.accepted_at or invite.rejected_at:
                raise AccountInviteError("Invite already processed")

            # Reject invite
            return self._reject_invite_internal(invite_id, member_id)
        except AccountError as e:
            logger.error(f"Failed to reject invite: {str(e)}")
            return AccountInviteResult(success=False, error_message=str(e))
        except Exception as e:
            logger.error(f"Unexpected error rejecting invite: {str(e)}")
            return AccountInviteResult(success=False, error_message="Internal error")

    def update_settings(
        self,
        account_id: str,
        settings: AccountSettings
    ) -> AccountUpdateResult:
        """Update account settings"""
        try:
            # Validate account exists
            self.get_account(account_id)

            # Validate settings
            if not self.validate_settings(account_id, settings):
                raise AccountSettingsError("Invalid account settings")

            # Update settings
            return self._update_settings_internal(account_id, settings)
        except AccountError as e:
            logger.error(f"Failed to update settings: {str(e)}")
            return AccountUpdateResult(success=False, error_message=str(e))
        except Exception as e:
            logger.error(f"Unexpected error updating settings: {str(e)}")
            return AccountUpdateResult(success=False, error_message="Internal error")

    def validate_account(self, account: Account) -> bool:
        """Validate account information"""
        try:
            if not account.name or not account.owner_id:
                return False

            if not isinstance(account.type, AccountType):
                return False

            if not isinstance(account.status, AccountStatus):
                return False

            if not self.validate_settings(account.id, account.settings):
                return False

            return True
        except Exception as e:
            logger.error(f"Error validating account: {str(e)}")
            return False

    def validate_member(
        self,
        account_id: str,
        member: AccountMember
    ) -> bool:
        """Validate member information"""
        try:
            if not member.member_id:
                return False

            if not isinstance(member.role, AccountRole):
                return False

            if not member.name:
                return False

            return True
        except Exception as e:
            logger.error(f"Error validating member: {str(e)}")
            return False

    def validate_settings(
        self,
        account_id: str,
        settings: AccountSettings
    ) -> bool:
        """Validate account settings"""
        try:
            if not settings.default_denomination:
                return False

            return True
        except Exception as e:
            logger.error(f"Error validating settings: {str(e)}")
            return False

    # Abstract methods to be implemented by providers

    def _create_account_internal(
        self,
        name: str,
        owner_id: str,
        account_type: AccountType,
        settings: AccountSettings,
        metadata: Dict[str, Any]
    ) -> AccountUpdateResult:
        """Internal method to create account

        This should be implemented by specific provider implementations
        """
        raise NotImplementedError(
            "Account provider must implement _create_account_internal method"
        )

    def _update_account_internal(
        self,
        account_id: str,
        updates: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> AccountUpdateResult:
        """Internal method to update account

        This should be implemented by specific provider implementations
        """
        raise NotImplementedError(
            "Account provider must implement _update_account_internal method"
        )

    def _delete_account_internal(
        self,
        account_id: str
    ) -> AccountUpdateResult:
        """Internal method to delete account

        This should be implemented by specific provider implementations
        """
        raise NotImplementedError(
            "Account provider must implement _delete_account_internal method"
        )

    def _add_member_internal(
        self,
        account_id: str,
        member_id: str,
        role: AccountRole,
        metadata: Dict[str, Any]
    ) -> AccountMemberResult:
        """Internal method to add member

        This should be implemented by specific provider implementations
        """
        raise NotImplementedError(
            "Account provider must implement _add_member_internal method"
        )

    def _remove_member_internal(
        self,
        account_id: str,
        member_id: str
    ) -> AccountMemberResult:
        """Internal method to remove member

        This should be implemented by specific provider implementations
        """
        raise NotImplementedError(
            "Account provider must implement _remove_member_internal method"
        )

    def _update_member_role_internal(
        self,
        account_id: str,
        member_id: str,
        new_role: AccountRole
    ) -> AccountMemberResult:
        """Internal method to update member role

        This should be implemented by specific provider implementations
        """
        raise NotImplementedError(
            "Account provider must implement _update_member_role_internal method"
        )

    def _create_invite_internal(
        self,
        account_id: str,
        inviter_id: str,
        invitee_handle: str,
        role: AccountRole,
        metadata: Dict[str, Any]
    ) -> AccountInviteResult:
        """Internal method to create invite

        This should be implemented by specific provider implementations
        """
        raise NotImplementedError(
            "Account provider must implement _create_invite_internal method"
        )

    def _accept_invite_internal(
        self,
        invite_id: str,
        member_id: str
    ) -> AccountInviteResult:
        """Internal method to accept invite

        This should be implemented by specific provider implementations
        """
        raise NotImplementedError(
            "Account provider must implement _accept_invite_internal method"
        )

    def _reject_invite_internal(
        self,
        invite_id: str,
        member_id: str
    ) -> AccountInviteResult:
        """Internal method to reject invite

        This should be implemented by specific provider implementations
        """
        raise NotImplementedError(
            "Account provider must implement _reject_invite_internal method"
        )

    def _update_settings_internal(
        self,
        account_id: str,
        settings: AccountSettings
    ) -> AccountUpdateResult:
        """Internal method to update settings

        This should be implemented by specific provider implementations
        """
        raise NotImplementedError(
            "Account provider must implement _update_settings_internal method"
        )
