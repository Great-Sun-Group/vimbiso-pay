from .screens import ACCOUNT_SELECTION, AGENTS, BALANCE, HOME_1, HOME_2, UNSERCURED_BALANCES
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

        self.service.refresh(reset=True)
        current_state = self.service.current_state

        pending = ''
        pending_in = 0
        if current_state['member']['defaultAccountData']['pendingInData']:
            pending_in = len(current_state['member']['defaultAccountData']['pendingInData'])
            pending = f"    Pending Offers ({pending_in})"

        pending_out = 0
        if current_state['member']['defaultAccountData']['pendingOutData']:
            pending_out = len(current_state['member']['defaultAccountData']['pendingOutData'])

        secured = ""
        for item in current_state['member']['defaultAccountData']['balanceData']['securedNetBalancesByDenom']:
            secured += f" *{item}* \n"

        balances = ""
        balance_lists = current_state['member']['defaultAccountData']['balanceData']['securedNetBalancesByDenom']
        for bal in balance_lists:
            balances += f"- {bal}\n"

        isOwnedAccount = current_state['member']['defaultAccountData'].get('isOwnedAccount')
        memberTier = current_state['member']['memberDashboard'].get('memberTier')

        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self.user.mobile_number,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {
                    "text": (HOME_2 if isOwnedAccount else HOME_1).format(
                        account=current_state['member']['defaultAccountData']['accountName'],
                        balance=BALANCE.format(
                            securedNetBalancesByDenom=balances if balances else "    $0.00\n",
                            unsecured_balance=UNSERCURED_BALANCES.format(
                                totalPayables=current_state['member']['defaultAccountData']['balanceData'][
                                    'unsecuredBalancesInDefaultDenom']['totalPayables'],
                                totalReceivables=current_state['member']['defaultAccountData']['balanceData'][
                                    'unsecuredBalancesInDefaultDenom']['totalReceivables'],
                                netPayRec=current_state['member']['defaultAccountData']['balanceData'][
                                    'unsecuredBalancesInDefaultDenom']['netPayRec'],
                            ) if memberTier > 2 else f"Free tier remaining daily spend limit\n    *{current_state['member']['memberDashboard'].get('remainingAvailableUSD', 0)} USD*\n{pending}",
                            netCredexAssetsInDefaultDenom=current_state['member']['defaultAccountData']['balanceData'][
                                'netCredexAssetsInDefaultDenom']
                        ),
                        handle=current_state['member']['defaultAccountData']['accountHandle'],
                    )
                },
                "action":
                    {
                        "button": "🕹️ Options",
                        "sections": [
                            {
                                "title": "Options",
                                "rows":
                                    [
                                        {
                                            "id": "handle_action_offer_credex",
                                            "title": f"💸 Offer Secured Credex",
                                        },
                                        {
                                            "id": "handle_action_pending_offers_in",
                                            "title": f"📥 Pending Offers ({pending_in})"
                                        },
                                        {
                                            "id": "handle_action_pending_offers_out",
                                            "title": f"📤 Review Outgoing ({pending_out})"
                                        },
                                        {
                                            "id": "handle_action_transactions",
                                            "title": f"📒 Review Transactions",
                                        }
                                    ] if not isOwnedAccount else [
                                    {
                                        "id": "handle_action_offer_credex",
                                        "title": f"💸 Offer Secured Credex",
                                    },
                                    {
                                        "id": "handle_action_pending_offers_in",
                                        "title": f"📥 Pending Offers ({pending_in})"
                                    },
                                    {
                                        "id": "handle_action_pending_offers_out",
                                        "title": f"📤 Review Outgoing ({pending_out})"
                                    },
                                    {
                                        "id": "handle_action_transactions",
                                        "title": f"📒 Review Transactions",
                                    },
                                    {
                                        "id": "handle_action_authorize_member",
                                        "title": f"👥 Manage Members"
                                    }, {
                                        "id": "handle_action_notifications",
                                        "title": f"🛎️ Notifications"
                                    },
                                    {
                                        "id": "handle_action_switch_account",
                                        "title": f"🏡 Member Dashboard",
                                    }
                                ]
                            }
                        ]
                    }
            }
        }


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
        state = self.service.state
        current_state = self.service.current_state

        if not current_state.get('member'):
            response = self.service.refresh(reset=True)
            if response and state.stage:
                return response

        if state.option in ["select_account_to_use","handle_action_confirm_offer_credex"] and f"{self.body}".lower() not in GREETINGS:
            options = {}
            count = 1
            for acc in current_state['member']['accountDashboards']:
                options[str(count)] = int(count) - 1
                options[acc.get('accountHandle')] = int(count) - 1
                count += 1

            print("OPTIONS : ", options, " SELECTED - ", self.body)
            if f"{self.body}".lower() in GREETINGS:
                self.body = '1'
            if options.get(self.body) is not None:
                # print("OPTIONS : ", options)
                current_state['member']['defaultAccountData'] = current_state['member']['accountDashboards'][
                    options.get(self.body)]
                state.update_state(
                    state=current_state,
                    stage='handle_action_menu',
                    update_from="handle_action_menu",
                    option="handle_action_menu"
                )
                self.body = "Hi"
                self.message['message'] = "Hi"
                return self.handle_action_menu
            else:
                if str(self.body).isdigit():
                    if self.body in [str(len(current_state['member']['accountDashboards']) + 1),
                                     "handle_action_offer_credex"]:
                        return self.handle_action_offer_credex
                    elif self.body in [str(len(current_state['member']['accountDashboards']) + 2),
                                       "handle_action_create_business_account"]:
                        return self.handle_action_create_business_account
                    elif self.body in [str(len(current_state['member']['accountDashboards']) + 3),
                                       "handle_action_find_agent"]:
                        return self.wrap_text(AGENTS)

        accounts = []
        count = 1
        account_string = f""
        for account in current_state['member']['accountDashboards']:
            account_string += f" *{count}.* 👤 _{account.get('accountName')}_\n"
            accounts.append(
                {
                    "id": account.get('accountHandle'),
                    "title": f"👤 {account.get('accountName').replace('Personal', '')}"[:21] + "..." if len(
                        f"👤 {account.get('accountName').replace('Personal', '')}") > 24 else f"👤 {account.get('accountName').replace('Personal', '')}"
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
            "to": self.user.mobile_number,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {
                    "text": ACCOUNT_SELECTION.format(
                        greeting=get_greeting(name=current_state['member']['memberDashboard']['firstname']),
                        accounts=account_string)
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