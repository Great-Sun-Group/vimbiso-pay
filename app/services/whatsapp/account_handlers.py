from typing import Dict, Any

from core.accounts import (
    AccountRole,
    AccountError,
    AccountMemberNotFoundError,
    create_account_service,
)
from .base_handler import BaseActionHandler
from .screens import (
    ADD_MEMBER,
    CONFIRM_AUTHORIZATION,
    AUTHORIZATION_SUCCESSFUL,
    DEAUTHORIZATION_SUCCESSFUL,
    AUTHORIZATION_FAILED,
    NOTIFICATIONS,
    NOTIFICATION,
)
from .types import WhatsAppMessage


class AccountActionHandler(BaseActionHandler):
    """Handler for account management actions"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.account_service = create_account_service(
            api_client=self.service.credex_service
        )

    def handle_action_authorize_member(self) -> WhatsAppMessage:
        """Handle member authorization flow"""
        user = self.service.user
        current_state = user.state.get_state(user)

        if not current_state.get("profile"):
            response = self.service.refresh(reset=True)
            if response:
                self.service.state.update_state(
                    self.service.current_state,
                    stage="handle_action_register",
                    update_from="handle_action_authorize_member",
                    option="handle_action_register",
                )
                return response

        selected_profile = current_state.get("current_account", {})
        if not selected_profile:
            selected_profile = current_state["profile"]["memberDashboard"]["accounts"][0]
            current_state["current_account"] = selected_profile
            self.service.state.update_state(
                state=current_state,
                stage="handle_action_authorize_member",
                update_from="handle_action_authorize_member",
                option="handle_action_authorize_member",
            )

        if user.state.option == "handle_action_confirm_authorization":
            return self._handle_authorization_confirmation(current_state)

        if self.service.message["type"] == "nfm_reply":
            return self._handle_authorization_form(current_state)

        return self.get_response_template(
            ADD_MEMBER.format(
                company=selected_profile.get("accountName", ""),
                message="",
            )
        )

    def handle_action_notifications(self) -> WhatsAppMessage:
        """Handle notification settings"""
        user = self.service.user
        current_state = user.state.get_state(user)

        if not current_state.get("profile"):
            response = self.service.refresh(reset=True)
            if response:
                self.service.state.update_state(
                    self.service.current_state,
                    stage="handle_action_register",
                    update_from="handle_action_notifications",
                    option="handle_action_register",
                )
                return response

        selected_profile = current_state.get("current_account", {})
        if not selected_profile:
            selected_profile = current_state["profile"]["memberDashboard"]["accounts"][0]
            current_state["current_account"] = selected_profile
            self.service.state.update_state(
                state=current_state,
                stage="handle_action_notifications",
                update_from="handle_action_notifications",
                option="handle_action_notifications",
            )

        if self.service.message["type"] == "nfm_reply":
            return self._handle_notification_update(current_state)

        return self._format_notification_menu(current_state)

    def _handle_authorization_confirmation(self, current_state: Dict[str, Any]) -> WhatsAppMessage:
        """Handle member authorization confirmation"""
        try:
            if self.service.body == "1":  # Authorize
                payload = current_state.get("authorization_payload", {})
                result = self.account_service.add_member(
                    account_id=payload["account_id"],
                    member_id=payload["member_id"],
                    role=AccountRole.MEMBER,
                    metadata={"authorized_by": self.service.user.mobile_number}
                )

                if result.success:
                    return self.get_response_template(
                        AUTHORIZATION_SUCCESSFUL.format(
                            member=payload.get("member_name"),
                            company=current_state.get("current_account", {}).get("accountName"),
                        )
                    )
                return self.get_response_template(
                    AUTHORIZATION_FAILED.format(message=result.error_message)
                )

            if self.service.body == "2":  # Cancel
                return self.get_response_template(
                    DEAUTHORIZATION_SUCCESSFUL.format(
                        member=current_state.get("authorization_payload", {}).get("member_name"),
                        company=current_state.get("current_account", {}).get("accountName"),
                    )
                )

            return self.handle_default_action()
        except AccountError as e:
            return self.get_response_template(
                AUTHORIZATION_FAILED.format(message=str(e))
            )

    def _handle_authorization_form(self, current_state: Dict[str, Any]) -> WhatsAppMessage:
        """Handle member authorization form submission"""
        try:
            member_handle = self.service.body.get("handle")
            success, member_data = self.service.credex_service.validate_handle(member_handle)

            if not success:
                return self.get_response_template(
                    AUTHORIZATION_FAILED.format(message="Invalid member handle")
                )

            # Check if member already exists in account
            account_id = current_state.get("current_account", {}).get("accountID")
            try:
                self.account_service.get_member(account_id, member_data["memberID"])
                return self.get_response_template(
                    AUTHORIZATION_FAILED.format(message="Member already exists in account")
                )
            except AccountMemberNotFoundError:
                pass  # Expected - member should not exist

            current_state["authorization_payload"] = {
                "member_id": member_data.get("memberID"),
                "member_name": member_data.get("accountName"),
                "account_id": account_id,
            }

            self.service.state.update_state(
                state=current_state,
                stage="handle_action_authorize_member",
                update_from="handle_action_authorize_member",
                option="handle_action_confirm_authorization",
            )

            return self.get_response_template(
                CONFIRM_AUTHORIZATION.format(
                    member=member_data.get("accountName"),
                    company=current_state.get("current_account", {}).get("accountName"),
                )
            )
        except AccountError as e:
            return self.get_response_template(
                AUTHORIZATION_FAILED.format(message=str(e))
            )

    def _handle_notification_update(self, current_state: Dict[str, Any]) -> WhatsAppMessage:
        """Handle notification settings update"""
        try:
            member_id = self.service.body.get("member_id")
            account_id = current_state.get("current_account", {}).get("accountID")

            # Get current member info
            member = self.account_service.get_member(account_id, member_id)

            # Update account settings
            account = self.account_service.get_account(account_id)
            settings = account.settings
            settings.notification_preferences["primary_recipient"] = member_id

            result = self.account_service.update_settings(account_id, settings)
            if result.success:
                return self.get_response_template(
                    NOTIFICATION.format(name=member.name)
                )

            return self.get_response_template(
                AUTHORIZATION_FAILED.format(message=result.error_message)
            )
        except AccountError as e:
            return self.get_response_template(
                AUTHORIZATION_FAILED.format(message=str(e))
            )

    def _format_notification_menu(self, current_state: Dict[str, Any]) -> WhatsAppMessage:
        """Format notification settings menu"""
        try:
            account_id = current_state.get("current_account", {}).get("accountID")
            account = self.account_service.get_account(account_id)

            # Get current notification recipient
            current_recipient_id = account.settings.notification_preferences.get(
                "primary_recipient"
            )
            try:
                current_recipient = self.account_service.get_member(
                    account_id, current_recipient_id
                ) if current_recipient_id else None
            except AccountMemberNotFoundError:
                current_recipient = None

            # Get other members
            members = []
            for member in self.account_service.list_members(account_id):
                if not current_recipient or member.member_id != current_recipient.member_id:
                    members.append(f"- *{member.name}*")

            return self.get_response_template(
                NOTIFICATIONS.format(
                    name=current_recipient.name if current_recipient else "Not set",
                    members="\n".join(members),
                )
            )
        except AccountError as e:
            return self.get_response_template(
                AUTHORIZATION_FAILED.format(message=str(e))
            )
