import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from .base import BaseAccountService
from .exceptions import (
    AccountError,
    AccountNotFoundError,
    AccountMemberNotFoundError,
    AccountInviteError,
)
from .types import (
    Account,
    AccountMember,
    AccountInvite,
    AccountRole,
    AccountSettings,
    AccountType,
    AccountStatus,
    AccountUpdateResult,
    AccountMemberResult,
    AccountInviteResult,
)

logger = logging.getLogger(__name__)


class CredexAccountService(BaseAccountService):
    """CredEx-specific account service implementation"""

    def __init__(self, api_client):
        """Initialize with CredEx API client"""
        self.api_client = api_client

    def get_account(self, account_id: str) -> Account:
        """Get account information"""
        try:
            response = self.api_client.get_account(account_id)

            if not response.get("success"):
                raise AccountNotFoundError(
                    response.get("error", "Account not found")
                )

            return self._create_account_from_response(response["data"])
        except Exception as e:
            logger.error(f"Failed to get CredEx account: {str(e)}")
            raise AccountNotFoundError(str(e))

    def list_accounts(
        self,
        member_id: Optional[str] = None,
        account_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Account]:
        """List accounts matching criteria"""
        try:
            filters = {
                "member_id": member_id,
                "type": account_type,
                "status": status
            }
            response = self.api_client.list_accounts(filters)

            if not response.get("success"):
                raise AccountError(
                    response.get("error", "Failed to list accounts")
                )

            return [
                self._create_account_from_response(data)
                for data in response.get("data", {}).get("accounts", [])
            ]
        except Exception as e:
            logger.error(f"Failed to list CredEx accounts: {str(e)}")
            return []

    def get_member(self, account_id: str, member_id: str) -> AccountMember:
        """Get member information"""
        try:
            response = self.api_client.get_account_member(account_id, member_id)

            if not response.get("success"):
                raise AccountMemberNotFoundError(
                    response.get("error", "Member not found")
                )

            return self._create_member_from_response(response["data"])
        except Exception as e:
            logger.error(f"Failed to get CredEx account member: {str(e)}")
            raise AccountMemberNotFoundError(str(e))

    def list_members(
        self,
        account_id: str,
        role: Optional[AccountRole] = None
    ) -> List[AccountMember]:
        """List members in an account"""
        try:
            filters = {"role": role.value if role else None}
            response = self.api_client.list_account_members(account_id, filters)

            if not response.get("success"):
                raise AccountError(
                    response.get("error", "Failed to list members")
                )

            return [
                self._create_member_from_response(data)
                for data in response.get("data", {}).get("members", [])
            ]
        except Exception as e:
            logger.error(f"Failed to list CredEx account members: {str(e)}")
            return []

    def get_invite(self, invite_id: str) -> AccountInvite:
        """Get invite information"""
        try:
            response = self.api_client.get_account_invite(invite_id)

            if not response.get("success"):
                raise AccountInviteError(
                    response.get("error", "Invite not found")
                )

            return self._create_invite_from_response(response["data"])
        except Exception as e:
            logger.error(f"Failed to get CredEx account invite: {str(e)}")
            raise AccountInviteError(str(e))

    def list_invites(
        self,
        account_id: Optional[str] = None,
        member_id: Optional[str] = None
    ) -> List[AccountInvite]:
        """List invites matching criteria"""
        try:
            filters = {
                "account_id": account_id,
                "member_id": member_id
            }
            response = self.api_client.list_account_invites(filters)

            if not response.get("success"):
                raise AccountError(
                    response.get("error", "Failed to list invites")
                )

            return [
                self._create_invite_from_response(data)
                for data in response.get("data", {}).get("invites", [])
            ]
        except Exception as e:
            logger.error(f"Failed to list CredEx account invites: {str(e)}")
            return []

    def _create_account_internal(
        self,
        name: str,
        owner_id: str,
        account_type: AccountType,
        settings: AccountSettings,
        metadata: Dict[str, Any]
    ) -> AccountUpdateResult:
        """Create a new CredEx account"""
        try:
            payload = {
                "name": name,
                "owner_id": owner_id,
                "type": account_type.value,
                "settings": {
                    "default_denomination": settings.default_denomination,
                    "allow_unsecured_credex": settings.allow_unsecured_credex,
                    "require_2fa": settings.require_2fa,
                    "auto_approve_members": settings.auto_approve_members,
                    "notification_preferences": settings.notification_preferences,
                    "metadata": settings.metadata,
                },
                "metadata": metadata,
            }
            response = self.api_client.create_account(payload)

            if not response.get("success"):
                raise AccountError(response.get("error", "Failed to create account"))

            return AccountUpdateResult(
                success=True,
                account=self._create_account_from_response(response["data"])
            )
        except Exception as e:
            logger.error(f"Failed to create CredEx account: {str(e)}")
            raise AccountError(str(e))

    def _update_account_internal(
        self,
        account_id: str,
        updates: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> AccountUpdateResult:
        """Update a CredEx account"""
        try:
            payload = {**updates, "metadata": metadata}
            response = self.api_client.update_account(account_id, payload)

            if not response.get("success"):
                raise AccountError(response.get("error", "Failed to update account"))

            return AccountUpdateResult(
                success=True,
                account=self._create_account_from_response(response["data"])
            )
        except Exception as e:
            logger.error(f"Failed to update CredEx account: {str(e)}")
            raise AccountError(str(e))

    def _delete_account_internal(
        self,
        account_id: str
    ) -> AccountUpdateResult:
        """Delete a CredEx account"""
        try:
            response = self.api_client.delete_account(account_id)

            if not response.get("success"):
                raise AccountError(response.get("error", "Failed to delete account"))

            return AccountUpdateResult(success=True)
        except Exception as e:
            logger.error(f"Failed to delete CredEx account: {str(e)}")
            raise AccountError(str(e))

    def _add_member_internal(
        self,
        account_id: str,
        member_id: str,
        role: AccountRole,
        metadata: Dict[str, Any]
    ) -> AccountMemberResult:
        """Add member to CredEx account"""
        try:
            payload = {
                "member_id": member_id,
                "role": role.value,
                "metadata": metadata,
            }
            response = self.api_client.add_account_member(account_id, payload)

            if not response.get("success"):
                raise AccountError(response.get("error", "Failed to add member"))

            return AccountMemberResult(
                success=True,
                member=self._create_member_from_response(response["data"])
            )
        except Exception as e:
            logger.error(f"Failed to add CredEx account member: {str(e)}")
            raise AccountError(str(e))

    def _remove_member_internal(
        self,
        account_id: str,
        member_id: str
    ) -> AccountMemberResult:
        """Remove member from CredEx account"""
        try:
            response = self.api_client.remove_account_member(account_id, member_id)

            if not response.get("success"):
                raise AccountError(response.get("error", "Failed to remove member"))

            return AccountMemberResult(success=True)
        except Exception as e:
            logger.error(f"Failed to remove CredEx account member: {str(e)}")
            raise AccountError(str(e))

    def _update_member_role_internal(
        self,
        account_id: str,
        member_id: str,
        new_role: AccountRole
    ) -> AccountMemberResult:
        """Update CredEx account member role"""
        try:
            payload = {"role": new_role.value}
            response = self.api_client.update_account_member(
                account_id, member_id, payload
            )

            if not response.get("success"):
                raise AccountError(response.get("error", "Failed to update member role"))

            return AccountMemberResult(
                success=True,
                member=self._create_member_from_response(response["data"])
            )
        except Exception as e:
            logger.error(f"Failed to update CredEx account member role: {str(e)}")
            raise AccountError(str(e))

    def _create_invite_internal(
        self,
        account_id: str,
        inviter_id: str,
        invitee_handle: str,
        role: AccountRole,
        metadata: Dict[str, Any]
    ) -> AccountInviteResult:
        """Create CredEx account invite"""
        try:
            payload = {
                "inviter_id": inviter_id,
                "invitee_handle": invitee_handle,
                "role": role.value,
                "metadata": metadata,
                "expires_at": int((datetime.now() + timedelta(days=7)).timestamp() * 1000)
            }
            response = self.api_client.create_account_invite(account_id, payload)

            if not response.get("success"):
                raise AccountError(response.get("error", "Failed to create invite"))

            return AccountInviteResult(
                success=True,
                invite=self._create_invite_from_response(response["data"])
            )
        except Exception as e:
            logger.error(f"Failed to create CredEx account invite: {str(e)}")
            raise AccountError(str(e))

    def _accept_invite_internal(
        self,
        invite_id: str,
        member_id: str
    ) -> AccountInviteResult:
        """Accept CredEx account invite"""
        try:
            response = self.api_client.accept_account_invite(invite_id, member_id)

            if not response.get("success"):
                raise AccountError(response.get("error", "Failed to accept invite"))

            return AccountInviteResult(
                success=True,
                invite=self._create_invite_from_response(response["data"])
            )
        except Exception as e:
            logger.error(f"Failed to accept CredEx account invite: {str(e)}")
            raise AccountError(str(e))

    def _reject_invite_internal(
        self,
        invite_id: str,
        member_id: str
    ) -> AccountInviteResult:
        """Reject CredEx account invite"""
        try:
            response = self.api_client.reject_account_invite(invite_id, member_id)

            if not response.get("success"):
                raise AccountError(response.get("error", "Failed to reject invite"))

            return AccountInviteResult(
                success=True,
                invite=self._create_invite_from_response(response["data"])
            )
        except Exception as e:
            logger.error(f"Failed to reject CredEx account invite: {str(e)}")
            raise AccountError(str(e))

    def _update_settings_internal(
        self,
        account_id: str,
        settings: AccountSettings
    ) -> AccountUpdateResult:
        """Update CredEx account settings"""
        try:
            payload = {
                "settings": {
                    "default_denomination": settings.default_denomination,
                    "allow_unsecured_credex": settings.allow_unsecured_credex,
                    "require_2fa": settings.require_2fa,
                    "auto_approve_members": settings.auto_approve_members,
                    "notification_preferences": settings.notification_preferences,
                    "metadata": settings.metadata,
                }
            }
            response = self.api_client.update_account_settings(account_id, payload)

            if not response.get("success"):
                raise AccountError(response.get("error", "Failed to update settings"))

            return AccountUpdateResult(
                success=True,
                account=self._create_account_from_response(response["data"])
            )
        except Exception as e:
            logger.error(f"Failed to update CredEx account settings: {str(e)}")
            raise AccountError(str(e))

    def _create_account_from_response(self, data: Dict[str, Any]) -> Account:
        """Create account object from API response"""
        return Account(
            id=data["accountID"],
            name=data["accountName"],
            type=AccountType(data["type"]),
            status=AccountStatus(data["status"]),
            owner_id=data["ownerID"],
            settings=AccountSettings(
                default_denomination=data["settings"]["defaultDenom"],
                allow_unsecured_credex=data["settings"].get("allowUnsecuredCredex", False),
                require_2fa=data["settings"].get("require2FA", False),
                auto_approve_members=data["settings"].get("autoApproveMembers", False),
                notification_preferences=data["settings"].get("notificationPreferences", {}),
                metadata=data["settings"].get("metadata", {})
            ),
            members=self.list_members(data["accountID"]),
            created_at=datetime.fromtimestamp(int(data["createdAt"]) / 1000),
            updated_at=datetime.fromtimestamp(int(data["updatedAt"]) / 1000),
            metadata=data.get("metadata", {})
        )

    def _create_member_from_response(self, data: Dict[str, Any]) -> AccountMember:
        """Create member object from API response"""
        return AccountMember(
            member_id=data["memberID"],
            role=AccountRole(data["role"]),
            name=data["name"],
            handle=data.get("handle"),
            email=data.get("email"),
            phone=data.get("phone"),
            joined_at=datetime.fromtimestamp(int(data["joinedAt"]) / 1000)
            if data.get("joinedAt") else None,
            metadata=data.get("metadata", {})
        )

    def _create_invite_from_response(self, data: Dict[str, Any]) -> AccountInvite:
        """Create invite object from API response"""
        return AccountInvite(
            id=data["inviteID"],
            account_id=data["accountID"],
            inviter_id=data["inviterID"],
            invitee_handle=data["inviteeHandle"],
            role=AccountRole(data["role"]),
            created_at=datetime.fromtimestamp(int(data["createdAt"]) / 1000),
            expires_at=datetime.fromtimestamp(int(data["expiresAt"]) / 1000),
            accepted_at=datetime.fromtimestamp(int(data["acceptedAt"]) / 1000)
            if data.get("acceptedAt") else None,
            rejected_at=datetime.fromtimestamp(int(data["rejectedAt"]) / 1000)
            if data.get("rejectedAt") else None,
            metadata=data.get("metadata", {})
        )
