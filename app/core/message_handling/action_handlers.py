from ..utils.utils import wrap_text, CredexWhatsappService, get_greeting
from ..config.constants import *
import requests
import json
from decouple import config
from serializers.company import CompanyDetailsSerializer
from serializers.members import MemberDetailsSerializer

class ActionHandler:
    def __init__(self, service):
        self.service = service

    def handle_greeting(self):
        print("Handling greeting")
        self.service.refresh(reset=True)
        current_state = self.service.current_state
        
        if current_state.get('member', {}).get('memberDashboard', {}).get('memberTier'):
            if current_state.get('member', {}).get('memberDashboard', {}).get('memberTier') <= 2:
                current_state['member']['defaultAccountData'] = current_state['member']['accountDashboards'][-1]
                self.service.state.update_state(
                    state=current_state,
                    stage='handle_action_menu',
                    update_from="handle_greeting",
                    option="handle_action_menu"
                )
                return self.handle_action_menu()
        return self.handle_action_select_profile()

    def handle_action_register(self):
        message = ""
        if self.service.message['type'] == "nfm_reply":
            payload = {
                "first_name": self.service.body.get('firstName'),
                "last_name": self.service.body.get('lastName'),
                "phone_number": self.service.message['from']
            }
            serializer = MemberDetailsSerializer(data=payload)
            if serializer.is_valid():
                # Implementation for valid serializer
                pass
            else:
                # Handle invalid serializer
                pass
        
        # Rest of the implementation

    def handle_action_menu(self):
        # Implementation for handling menu actions
        pass

    def handle_action_transactions(self):
        # Implementation for handling transactions
        pass

    def handle_action_pending_offers_in(self):
        # Implementation for handling incoming pending offers
        pass

    def handle_action_pending_offers_out(self):
        # Implementation for handling outgoing pending offers
        pass

    def handle_action_accept_offer(self):
        # Implementation for accepting an offer
        pass

    def handle_action_decline_offer(self):
        # Implementation for declining an offer
        pass

    def handle_action_cancel_offer(self):
        # Implementation for cancelling an offer
        pass

    def handle_action_create_business_account(self):
        # Implementation for creating a business account
        pass

    def handle_action_authorize_member(self):
        # Implementation for authorizing a member
        pass

    def handle_action_select_profile(self):
        print("Handling select profile")
        state = self.service.state
        current_state = self.service.current_state

        if not current_state.get('member'):
            response = self.service.refresh()
            if response and state.stage:
                return response
        
        accounts = []
        count = 1
        account_string = ""
        for account in current_state['member']['accountDashboards']:
            account_string += f" *{count}.* 👤 _{account.get('accountName')}_\n"
            accounts.append(
                {
                    "id": account.get('accountHandle'),
                    "title": f"👤 {account.get('accountName').replace('Personal', '')}"[:21] + "..." if len(f"👤 {account.get('accountName').replace('Personal', '')}") > 24 else f"👤 {account.get('accountName').replace('Personal', '')}"
                }
            )

            if count > 7:
                count += 1
                break
            count += 1

        account_string += f" *{count}.* 💸 _Make Credex Offer_\n"
        accounts.append(
            {
                "id": "handle_action_offer_credex",
                "title": f"💸 Offer Credex"
            }
        )
        count += 1
        account_string += f" *{count}.* 💼 _Create Another Account_\n"
        accounts.append(
            {
                "id": "handle_action_create_business_account",
                "title": f"💼 Create Account"
            }
        )
        count += 1

        account_string += f" *{count}.* 🏦 _Cash In/Out with VimbisoPay_\n"
        accounts.append(
            {
                "id": "handle_action_find_agent",
                "title": f"🏦 Cash In/Out"
            }
        )

        state.update_state(
            state=current_state,
            stage='handle_action_select_profile',
            update_from="handle_action_select_profile",
            option="select_account_to_use"
        )

        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self.service.user.mobile_number,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {
                    "text": ACCOUNT_SELECTION.format(greeting=get_greeting(name=current_state['member']['memberDashboard']['firstname']), accounts=account_string)
                },
                "action":
                    {
                        "button": "🕹️ Options",
                        "sections": [
                            {
                                "title": "Options",
                                "rows": accounts
                            }
                        ]
                    }
            }
        }

    def handle_default_action(self):
        # Implementation for handling default or unknown actions
        return wrap_text(INVALID_ACTION, self.service.user.mobile_number)

    # Add other action handling methods as needed