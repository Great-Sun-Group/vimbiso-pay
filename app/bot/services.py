from bot.utils import CredexWhatsappService, convert_timestamp_to_date
from bot.serializers.company import CompanyDetailsSerializer
from bot.serializers.offers import OfferCredexSerializer
from bot.serializers.members import MemberDetailsSerializer
from bot.screens import *
from bot.constants import *
import requests, json
from decouple import config
from bot.models import Message
from django.core.cache import cache
from datetime import datetime



class CredexBotService:
    def __init__(self, payload, methods: dict = dict, user: object = None) -> None:
        self.message = payload
        self.user = user
        self.body = self.message['message']

        # Load
        state = self.user.state
        current_state = state.get_state(self.user)
        if not isinstance(current_state, dict):
            current_state = current_state.state

        self.current_state = current_state
        try:
            self.response = self.handle()
            # print(self.response)
        except Exception as e:
            print("ERROR : ", e)

    def handle(self):
        """ THIS METHOD HANDLES ALL REQUESTS DIRECTING THEM WHERE THEY NEED TO GO"""
        state = self.user.state
        current_state = state.get_state(self.user)
        if not isinstance(current_state, dict):
            current_state = current_state.state

        # IF THERE IS NO MEMBER DETAILS IN STATE THE REFRESH MEMBER/FETCH INFO
        if not current_state.get('member'):
            response = self.refresh(reset=True, silent=True, init=True)
            # print(">>>>>>>>>>> ", self.body)
            if response and state.stage == "handle_action_register" and self.message['type'] != 'nfm_reply':
                return self.handle_action_register
            
        if "=>" in f"{self.body}" or "->" in f"{self.body}":
            state.update_state(
                state=current_state,
                stage="handle_action_offer_credex",
                update_from="handle_action_offer_credex",
                option="handle_action_offer_credex"
            )
            return self.handle_action_offer_credex

        # OVERRIDE FLOW IF USER WANTS TO ACCEPT, DECLINE OR CANCEL CREDEXES AND ROUTE TO THE APPROPRIATE METHOD
        if f"{self.body}".startswith("accept_") or f"{self.body}".startswith("cancel_") or f"{self.body}".startswith(
                "decline_") or f"{self.body}" == "AcceptAllIncomingOffers" or self.body == "View Pending":
            
            if f"{self.body}".startswith("accept_"):
                return self.handle_action_accept_offer
            elif self.body == "View Pending":
                self.body = "handle_action_pending_offers_in"
                return self.handle_action_pending_offers_in
            elif f"{self.body}".startswith("decline_"):
                return self.handle_action_decline_offer
            elif f"{self.body}".startswith("cancel_"):
                return self.handle_action_cancel_offer
            elif f"{self.body}" == "AcceptAllIncomingOffers":
                return self.handle_action_accept_all_incoming_offers

        # IF PROMPT IS IN GREETINGS THEN CLEAR CACHE AND FETCH MENU
        if f"{self.body}".lower() in GREETINGS and f"{self.body}".lower() not in ["y", "yes", "retry", "n", "no"]:
            # print("5")
            self.user.state.reset_state()
            state = self.user.state
            current_state = state.get_state(self.user)
            # print("6")
            if not isinstance(current_state, dict):
                current_state = current_state.state
            current_state = {"state": {}, 'member': {}}
            # print("7")
            self.body = "Hi"
            self.message['message'] = "Hi"
            self.refresh(reset=True)
            current_state = state.get_state(self.user)
            # print("6")
            if not isinstance(current_state, dict):
                current_state = current_state.state

            if current_state.get('member', {}).get('memberDashboard', {}).get('memberTier'):
                if current_state.get('member', {}).get('memberDashboard', {}).get('memberTier') <= 2: 
                    current_state['member']['defaultAccountData'] = current_state['member']['accountDashboards'][-1]#
                    state.update_state(
                        state=current_state,
                        stage='handle_action_menu',
                        update_from="handle_action_menu",
                        option="handle_action_menu"
                    )
                    return self.handle_action_menu
            return self.handle_action_select_profile

            # IF USER IS AT MENU STAGE FIND THE NEXT ROUTE BASED ON MESSAGE
        if self.user.state.stage == "handle_action_menu":
            isOwnedAccount = current_state.get('member', {}).get('defaultAccountData', {}).get('isOwnedAccount')
            selected_action = (MENU_OPTIONS_2 if isOwnedAccount else MENU_OPTIONS_1).get(f"{self.body}".lower())
            if not selected_action:
                return {
                    "messaging_product": "whatsapp",
                    "preview_url": False,
                    "recipient_type": "individual",
                    "to": self.user.mobile_number,
                    "type": "text",
                    "text": {
                        "body": INVALID_ACTION
                    }
                }
            self.body = selected_action

        if f"{self.body}".startswith("handle_action_"):
            state = self.user.state
            if state:
                current_state = state.get_state(self.user)
                if not isinstance(current_state, dict):
                    current_state = current_state.state
                state.update_state(state=current_state, update_from="handle_action_", stage=self.body)

            self.user.state.reset_state()
            return getattr(self, self.body)
        else:
            state = self.user.state
            return getattr(self, state.stage)

    def refresh(self, reset=True, silent=True, init=False):
        """THIS METHOD REFRESHES MEMBER INFO BY MAKING AN API CALL TO CREDEX CALL"""
        state = self.user.state
        current_state = state.get_state(self.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        # print("HIT CORE ")
        url = f"{config('CREDEX')}/getMemberDashboardByPhone"

        payload = json.dumps({
            "phone": self.message['from']
        })
        headers = {
            'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
            'Content-Type': 'application/json',
            'whatsappBotAPIkey': config('WHATSAPP_BOT_API_KEY')
        }
        if reset and silent == False or init:
            # current_state['sent'] = True
            if state.stage != "handle_action_register" and not cache.get(f"{self.user.mobile_number}_interracted"):
                CredexWhatsappService(payload={
                    "messaging_product": "whatsapp",
                    "preview_url": False,
                    "recipient_type": "individual",
                    "to": self.user.mobile_number,
                    "type": "text",
                    "text": {
                        "body": DELAY
                    }
                }).send_message()
                cache.set(f"{self.user.mobile_number}_interracted", True, 60*15)

            message =  Message.objects.all().first()
            if message:
                CredexWhatsappService(payload={
                    "messaging_product": "whatsapp",
                    "preview_url": False,
                    "recipient_type": "individual",
                    "to": self.user.mobile_number,
                    "type": "text",
                    "text": {
                        "body": message.messsage
                    }
                }).send_message()
       
        response = requests.request("GET", url, headers=headers, data=payload)
        # print(response.content)
        if response.status_code == 200:
            default = {}
            if reset == False:
                default = current_state.get('member', {}).pop('defaultAccountData', {})
            try:
                current_state['member'] = response.json()
                current_state['member']['accountDashboards'][-1]["isOwnedAccount"] = False
            except Exception as e:
                pass
            if default:
                for acc in current_state['member']['accountDashboards']:
                    if acc.get('accountID') == default.get('accountID'):
                        default['pendingInData'] = acc['pendingInData']
                        default['pendingOutData'] = acc['pendingOutData']
                        default['balanceData'] = acc['balanceData']
                        current_state['member']['defaultAccountData'] = default
                        break
            else:
                current_state['member']['defaultAccountData'] = {}
            
            state.update_state(
                state=current_state,
                stage='handle_action_select_profile',
                update_from="handle_action_select_profile",
                option="select_account_to_use"
            )


            if current_state.get('member', {}).get('memberDashboard', {}).get('memberTier') :
                if current_state.get('member', {}).get('memberDashboard', {}).get('memberTier', 1) <= 2:
                    current_state['member']['defaultAccountData'] = current_state['member']['accountDashboards'][-1]
                    state.update_state(
                        state=current_state,
                        stage='handle_action_menu',
                        update_from="handle_action_menu",
                        option="handle_action_menu"
                    )
                    return self.handle_action_menu
            
            self.body = "Hi"
            return self.handle_action_select_profile
        else:
            state.update_state(
                state=current_state,
                stage='handle_action_register',
                update_from="refresh",
                option="handle_action_register"
            )
            return self.wrap_text(REGISTER.format(message=response.json().get('message')), extra_rows=[{"id": '1', "title": "Become a member"}], include_menu=False)
            
    @property
    def handle_action_switch_account(self):
        state = self.user.state
        current_state = state.get_state(self.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        self.body = "Hi"
        self.message['message'] = "Hi"
        self.refresh(reset=True)
        current_state = state.get_state(self.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        # print("Straight out of refres",  current_state.get('member', {}) )

        if current_state.get('member', {}).get('memberDashboard', {}).get('memberTier'):
            if current_state.get('member', {}).get('memberDashboard', {}).get('memberTier', 1) <= 2:
                current_state['member']['defaultAccountData'] = current_state['member']['accountDashboards'][-1]
                state.update_state(
                    state=current_state,
                    stage='handle_action_menu',
                    update_from="handle_action_menu",
                    option="handle_action_menu"
                )
                return self.handle_action_menu
            
        return self.handle_action_select_profile

    @property
    def handle_action_register(self):
        """HANDLING CLIENT REGISTRATIONS"""
        message = ""
        if self.message['type'] == "nfm_reply":
            payload = {
                "first_name": self.body.get('firstName'),
                "last_name": self.body.get('lastName'),
                "phone_number": self.message['from']

            }
            message = ""
            serializer = MemberDetailsSerializer(data=payload)
            if serializer.is_valid():
                url = f"{config('CREDEX')}/onboardMember"
                headers = {
                    'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
                    'Content-Type': 'application/json',
                    'whatsappBotAPIkey': config('WHATSAPP_BOT_API_KEY'),
                }
                response = requests.request("POST", url, headers=headers, json=serializer.validated_data)
                # print('SERVER RESPONSE : ', response.content)
                if response.status_code == 200:
                    CredexWhatsappService(payload={
                        "messaging_product": "whatsapp",
                        "preview_url": False,
                        "recipient_type": "individual",
                        "to": self.user.mobile_number,
                        "type": "text",
                        "text": {
                            "body": REGISTRATION_COMPLETE.format(firstName=serializer.validated_data.get('firstname'))
                        }
                    }).send_message()
                    return self.handle_action_switch_account
                    
                else:
                    try:
                        if "Internal Server Error" in response.json().get('error', ''):
                            message = "Failed to perform action"
                        else:
                            message = response.json().get('message', '')
                        return {
                            "messaging_product": "whatsapp",
                            "to": self.user.mobile_number,
                            "recipient_type": "individual",
                            "type": "interactive",
                            "interactive": {
                                "type": "flow",
                                "body": {
                                    "text": REGISTER_FORM.format(message=self.format_synopsis(message))
                                },
                                "action": {
                                    "name": "flow",
                                    "parameters": {
                                        "flow_message_version": "3",
                                        "flow_action": "navigate",
                                        "flow_token": "not-used",
                                        "flow_id": "3686836301579704",
                                        "flow_cta": "Become a member",
                                        "flow_action_payload": {
                                            "screen": "MEMBER_SIGNUP"
                                        }
                                    }
                                }
                            }
                        }

                    except Exception as e:
                        pass
                    # print(response.content)

        if self.body == "1":
            return {
                "messaging_product": "whatsapp",
                "to": self.user.mobile_number,
                "recipient_type": "individual",
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "body": {
                        "text": REGISTER_FORM.format(message=self.format_synopsis(message))
                    },
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_action": "navigate",
                            "flow_token": "not-used",
                            "flow_id": "3686836301579704",
                            "flow_cta": "Become a member",
                            "flow_action_payload": {
                                "screen": "MEMBER_SIGNUP"
                            }
                        }
                    }
                }
            }

        if self.body == "2":
            return self.wrap_text(MORE_ABOUT_CREDEX, extra_rows=[{"id": '1', "title": "Become a member"}], include_menu=False)

        return self.wrap_text(REGISTER.format(message=message), extra_rows=[{"id": '1', "title": "Become a member"}], include_menu=False)


    @property
    def handle_action_create_business_account(self):
        """HANDLING BUSINESS REGISTRATIONS"""

        state = self.user.state
        current_state = state.get_state(self.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        message = ""
        if self.message['type'] == "nfm_reply":
            payload = {
                "ownerID": current_state['member']['memberDashboard']['memberID'],
                "companyname": self.body.get('firstName'),
                "defaultDenom": self.body.get('currency'),
                "handle": self.body.get('email')
            }
            serializer = CompanyDetailsSerializer(data=payload)

            if serializer.is_valid():
                url = f"{config('CREDEX')}/createAccount"
                headers = {
                    'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
                    'Content-Type': 'application/json',
                    'whatsappBotAPIkey': config('WHATSAPP_BOT_API_KEY'),
                }
                response = requests.request("POST", url, headers=headers, json=serializer.validated_data)
                # print(response.content, response.status_code)
                if response.status_code == 200:
                    self.refresh()
                    return self.wrap_text(
                        ACCOUNT_REGISTRATION_COMPLETE.format(
                            first_name=f"{self.body.get('firstName')}"
                        ),
                        x_is_menu=True, back_is_cancel=False, navigate_is='🏡 Menu'
                    )
                else:
                    try:
                        if "Internal Server Error" in response.json().get('error', ""):
                            message = "Failed to perform action"
                        else:
                            message = response.json().get('message') 

                    except Exception as e:
                        pass
            else:
                print(serializer.errors)
        state.update_state(
            state=current_state,
            stage='handle_action_create_business_account',
            update_from="handle_action_create_business_account",
            option="handle_action_create_business_account"
        )
        return  {
                "messaging_product": "whatsapp",
                "to": self.user.mobile_number,
                "recipient_type": "individual",
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "body": {
                        "text": COMPANY_REGISTRATION.format(message=self.format_synopsis(message))
                    },
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_action": "navigate",
                            "flow_token": "not-used",
                            "flow_id": "1048499583563106",
                            "flow_cta": "Create Account",
                            "flow_action_payload": {
                                "screen": "OPEN_ACCOUNT"
                            }
                        }
                    }
                }
            
            }

    @property
    def handle_action_menu(self):
        """HANDLES MENU STAGE GIVING THE USER THE MAIN MENU"""

        state = self.user.state
        current_state = state.get_state(self.user)

        # print("STATE : ", state.stage, state.option)

        if not isinstance(current_state, dict):
            current_state = current_state.state


        if not current_state.get('member'):
            self.refresh(reset=True)
            state = self.user.state
            current_state = state.get_state(self.user)

            if not isinstance(current_state, dict):
                current_state = current_state.state
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
                    "text": (HOME_2 if isOwnedAccount  else HOME_1).format(
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
                            )  if memberTier > 2 else f"Free tier remaining daily spend limit\n    *{current_state['member']['memberDashboard'].get('remainingAvailableUSD', 0)} USD*\n{pending}",
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
                                        },{
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
    
    @property
    def handle_action_notifications(self):
        state = self.user.state
        current_state = state.get_state(self.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        if self.body == 'handle_action_notifications':
            menu_string = ""
            rows = [
            ]
            count = 1

            for user in current_state.get('member', {}).get('defaultAccountData', {}).get('authFor', []):
                menu_string += f"{count}. {user.get('firstname')} {user.get('lastname')}\n"
                rows.append({
                    "id": count,
                    "title": f"{user.get('firstname')} {user.get('lastname')}"
                })
                count += 1
            
            rows.append(
                {
                    "id": "X",
                    "title": "🏡 Menu"
                }
            )
            
            state.update_state(
                state=current_state,
                stage='handle_action_notifications',
                update_from="handle_action_notifications",
                option="select_option"
            )
            return self.wrap_text(NOTIFICATIONS.format(name=f"{current_state.get('member', {}).get('defaultAccountData', {}).get('sendOffersToFirstname')} {current_state.get('member', {}).get('defaultAccountData', {}).get('sendOffersToLastname')}", members=menu_string),  extra_rows=rows)
        elif state.option == 'select_option':
            if self.body.isdigit():
                if int(self.body) in range(1, len(current_state.get('member', {}).get('defaultAccountData', {}).get('authFor', []))+1):
                    # print("Assign > ", current_state.get('member', {}).get('defaultAccountData', {}).get('authFor', [])[int(self.body)-1])
                    url = f"{config('CREDEX')}/updateSendOffersTo"
                    payload = json.dumps({
                        "humanIDtoSendOffers": current_state.get('member', {}).get('defaultAccountData', {}).get('authFor', [])[int(self.body)-1]['memberID'],
                        "memberIDtoSendOffers": current_state.get('member', {}).get('defaultAccountData', {}).get('authFor', [])[int(self.body)-1]['memberID'],
                        "accountID": current_state['member'].get('defaultAccountData', {}).get('accountID'),
                        "ownerID": current_state['member']['memberDashboard'].get('memberID')
                    })

                    headers = {
                        'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
                        'Content-Type': 'application/json',
                        'whatsappBotAPIkey': config('WHATSAPP_BOT_API_KEY'),
                    }
                    response = requests.request("POST", url, headers=headers, data=payload)
                    if response.status_code == 200:
                        data = response.json()
                        # print(data)
                        if data:
                            self.refresh(reset=True, silent=True)
                            menu_string = ""
                            rows = [
                            ]
                            count = 1
                            for user in current_state.get('member', {}).get('defaultAccountData', {}).get('authFor', []):
                                menu_string += f"{count}. {user.get('firstname')} {user.get('lastname')}\n"
                                rows.append({
                                    "id": count,
                                    "title": f"{user.get('firstname')} {user.get('lastname')}"
                                })
                                count += 1
                            
                            rows.append(
                                {
                                    "id": "X",
                                    "title": "🏡 Menu"
                                }
                            )
                            return self.wrap_text(NOTIFICATION.format(name=f"{current_state.get('member', {}).get('defaultAccountData', {}).get('authFor', [])[int(self.body)-1].get('firstname')} {current_state.get('member', {}).get('defaultAccountData', {}).get('authFor', [])[int(self.body)-1].get('lastname')}"))

                        else:
                            return self.wrap_text(INVALID_ACTION)

            return {
                "messaging_product": "whatsapp",
                "preview_url": False,
                "recipient_type": "individual",
                "to": self.user.mobile_number,
                "type": "text",
                "text": {
                    "body": INVALID_ACTION
                }
            }


        menu_string = ""
        rows = [
        ]
        count = 1
        for user in current_state.get('member', {}).get('defaultAccountData', {}).get('authFor', []):
            menu_string += f"{count}. {user.get('firstname')} {user.get('lastname')}\n"
            rows.append({
                "id": count,
                "title": f"{user.get('firstname')} {user.get('lastname')}"
            })
            count += 1
        
        rows.append(
            {
                "id": "X",
                "title": "🏡 Menu"
            }
        )
        state.update_state(
            state=current_state,
            stage='handle_action_notifications',
            update_from="handle_action_notifications",
            option="handle_action_notifications"
        )
        return self.wrap_text(NOTIFICATIONS.format(name=f"{current_state.get('member', {}).get('defaultAccountData', {}).get('sendOffersToFirstname')} {current_state.get('member', {}).get('defaultAccountData', {}).get('sendOffersToLastname')}", members=menu_string),  extra_rows=rows)


    @property
    def handle_action_select_profile(self):
        """HANDLES MENU STAGE GIVING THE USER THE MAIN MENU"""
        state = self.user.state
        current_state = state.get_state(self.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        if not current_state.get('member'):
            response = self.refresh()
            if response and state.stage:
                return response
            
        if state.option in ["select_account_to_use", "handle_action_confirm_offer_credex"] and f"{self.body}".lower() not in GREETINGS:
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
                current_state['member']['defaultAccountData'] = current_state['member']['accountDashboards'][options.get(self.body)]
                state.update_state(
                    state=current_state,
                    stage='handle_action_menu',
                    update_from="handle_action_menu",
                    option="handle_action_menu"
                )
                # print("SAVED : ", current_state['member']['accountDashboards'][options.get(self.body)])
                self.body = "Hi"
                self.message['message'] = "Hi"
                return self.handle_action_menu
            else:
                if str(self.body).isdigit():
                    if self.body in [str(len(current_state['member']['accountDashboards']) + 1),"handle_action_offer_credex"]:
                        return self.handle_action_offer_credex
                    elif self.body in [str(len(current_state['member']['accountDashboards']) + 2),"handle_action_create_business_account"]:
                        return self.handle_action_create_business_account
                    elif self.body in [str(len(current_state['member']['accountDashboards']) + 3),"handle_action_find_agent"]:
                        return self.wrap_text(AGENTS)
        
        accounts = []
        count = 1
        account_string = f""
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
            "to": self.user.mobile_number,
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
    
    @property
    def handle_action_find_agent(self):
        return self.wrap_text(AGENTS)

    @property
    def handle_action_transactions(self):
        """THIS METHOD FETCHES AND DISPLAYS TRANSACTIONS WITH PAGINATION"""
        state = self.user.state
        current_state = state.get_state(self.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        if not current_state.get('member'):
            self.refresh()

        page_number = current_state.get('page_number', 0)

        if self.body in ['Next', 'next', 'handle_action_transactions']:
            page_number += 1
        elif self.body in ['Prev', 'prev'] and page_number > 1:
            page_number -= 1
        else:
            if self.body.isdigit():
                if 0 < int(self.body) <= len(current_state.get('current_page', [])):
                    # print(current_state['current_page'][int(self.body) - 1])
                    self.body = current_state['current_page'][int(self.body) - 1]['id']
                
            url = f"{config('CREDEX')}/getCredex"

            payload = json.dumps({
                "credexID": self.body,
                "accountID": current_state['member']['defaultAccountData'].get('accountID'),
            })
            headers = {
                        'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
                        'Content-Type': 'application/json',
                        'whatsappBotAPIkey': config('WHATSAPP_BOT_API_KEY'),
                    }

            response = requests.request("GET", url, headers=headers, data=payload)
            if response.status_code == 200:
                credex = response.json()
                if credex:
                    return {
                        "messaging_product": "whatsapp",
                        "recipient_type": "individual",
                        "to": self.user.mobile_number,
                        "type": "interactive",
                        "interactive": {
                            "type": "list",
                            "body": {
                                "text": CREDEX.format(
                                    formattedOutstandingAmount=credex['credexData'].get('formattedOutstandingAmount'),
                                    formattedInitialAmount=credex['credexData'].get('formattedInitialAmount'),
                                    counterpartyDisplayname=credex['credexData'].get('counterpartyAccountName'),
                                    date=credex['credexData'].get('dateTime') if credex['credexData'].get(
                                        'dateTime') else 'N/A',
                                    type=credex['credexData'].get('transactionType')
                                )
                            },
                            "action":
                                {
                                    "button": "🕹️ Menu",
                                    "sections": [
                                        {
                                            "title": "Options",
                                            "rows": [
                                                {
                                                    "id": "X",
                                                    "title": "🏡 Menu"
                                                }
                                            ]
                                        }
                                    ]
                                }
                        }
                    }

            menu_string = "*Empty*\n\n🪹 No transaction(s) found!\n\n"
            rows = [
                {
                    "id": "X",
                    "title": "🏡 Menu"
                }
            ]
            return self.wrap_text(message=menu_string, extra_rows=rows)

        url = f"{config('CREDEX')}/getLedger"

        payload = json.dumps({
            "accountID": current_state['member']['defaultAccountData'].get('accountID'),
            "numRows": 8,
            "startRow": (page_number * 7) - 7
        })
        headers = {
            'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
            'Content-Type': 'application/json',
            'whatsappBotAPIkey': config('WHATSAPP_BOT_API_KEY'),
        }

        response = requests.request("GET", url, headers=headers, data=payload)
        if response.status_code == 200:
            transactions = response.json()
            has_next = True if len(transactions) > 7 else False
            rows = []
            menu_string = f"> *💳 TRANSACTIONS*\n\n*PAGE #{page_number}*\n\n"
            count = 1
            for txn in transactions:
                if 'Next' in txn.get('formattedInitialAmount'):
                    continue

                menu_string += f"{count}. {txn.get('formattedInitialAmount')} {'to ' if '-' in txn.get('formattedInitialAmount') else 'from '}{txn.get('counterpartyAccountName')}\n\n"
                rows.append({
                    "id": txn.get('credexID'),
                    "title": f"{txn.get('formattedInitialAmount').replace('-', '')} {'DEBIT ' if '-' in txn.get('formattedInitialAmount') else 'CREDIT '}",
                    "description": f"{txn.get('formattedInitialAmount')} {'to ' if '-' in txn.get('formattedInitialAmount') else 'from '}{txn.get('counterpartyAccountName')}"
                })
                count += 1
            current_state['page_number'] = page_number
            current_state['current_page'] = rows
            state.update_state(
                state=current_state,
                stage='handle_action_transactions',
                update_from="handle_action_transactions",
                option="handle_action_transactions"
            )
            if page_number > 1:
                rows.append(
                    {
                        "id": "Prev",
                        "title": "< Prev",
                        "description": "< Prev"
                    }
                )

            if has_next:
                rows.append(
                    {
                        "id": "Next",
                        "title": "Next >",
                        "description": "Next >"
                    }
                )

            if len(rows):
                return {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": self.user.mobile_number,
                    "type": "interactive",
                    "interactive": {
                        "type": "list",
                        "body": {
                            "text": menu_string + f"Send *'Menu'* to go back to Menu"
                        },
                        "action":
                            {
                                "button": "🕹️ Options",
                                "sections": [
                                    {
                                        "title": "Options",
                                        "rows": rows
                                    }
                                ]
                            }
                    }
                }
            menu_string = "*Empty*\n\n🪹 No transactions found!\n\n"
            rows = [
                {
                    "id": "X",
                    "title": "🏡 Menu"
                }
            ]
            return self.wrap_text(message=menu_string, extra_rows=rows)
        else:
            menu_string = "*Empty*\n\n🪹 No transactions found!\n\n"
            rows = [
                {
                    "id": "X",
                    "title": "🏡 Menu"
                }
            ]
            return self.wrap_text(message=menu_string, extra_rows=rows)

    @property
    def handle_action_accept_offer(self):
        """THIS METHOD HANDLES ACCEPTING A SINGLE OFFER"""
        state = self.user.state
        current_state = state.get_state(self.user)
        if not isinstance(current_state, dict):
            current_state = current_state.state
        payload = json.dumps({
            "signerID": current_state['member']['memberDashboard'].get('memberID'),
            "credexID": self.body.split("_")[-1]
        })
        headers = {
            'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
            'Content-Type': 'application/json',
            'whatsappBotAPIkey': config('WHATSAPP_BOT_API_KEY'),
        }
        response = requests.request("PUT", f"{config('CREDEX')}/acceptCredex", headers=headers, data=payload)
        if response.status_code == 200:
            try:
                self.refresh(reset=False)
            except Exception as e:
                print("ERROR FETCHING ", e)
            
            return self.wrap_text("> *🥳 Success*\n\nYou have accepted the selected offer", x_is_menu=True,
                                  back_is_cancel=False)
        return self.wrap_text("> *😞 Failed*\n\n Failed to accept the selected offer", x_is_menu=True, back_is_cancel=False)

    @property
    def handle_action_decline_offer(self):
        """THIS METHOD HANDLES DECLINING AN OFFER"""
        state = self.user.state
        current_state = state.get_state(self.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        payload = json.dumps({
            "credexID": self.body.split("_")[-1]
        })
        headers = {
            'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
            'Content-Type': 'application/json',
            'whatsappBotAPIkey': config('WHATSAPP_BOT_API_KEY'),
        }
        response = requests.request("PUT", f"{config('CREDEX')}/declineCredex", headers=headers, data=payload)
        if response.status_code == 200:
            self.refresh(reset=False)
            return self.wrap_text("> *🥳 Success*\n\n You have declined the selected offer", x_is_menu=True,
                                  back_is_cancel=False)
        return self.wrap_text("> *😞 Failed*\n\n Failed to decline the selected offer", x_is_menu=True, back_is_cancel=False)

    @property
    def handle_action_cancel_offer(self):
        """THIS METHOD HANDLES CANCELLING A SINGLE OFFER"""
        state = self.user.state
        current_state = state.get_state(self.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        payload = json.dumps({
            "credexID": self.body.split("_")[-1]
        })
        headers = {
            'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
            'Content-Type': 'application/json',
            'whatsappBotAPIkey': config('WHATSAPP_BOT_API_KEY'),
        }
        response = requests.request("PUT", f"{config('CREDEX')}/cancelCredex", headers=headers, data=payload)
        # print(response.content, response.status_code)
        if response.status_code == 200:
            self.refresh(reset=False)
            return self.wrap_text("> *🥳 Success*\n\n You have cancelled the selected offer", x_is_menu=True,
                                  back_is_cancel=False)
        return self.wrap_text("> *😞 Failed*\n\n Failed to cancel the selected offer", x_is_menu=True, back_is_cancel=False)

    @property
    def handle_action_accept_all_incoming_offers(self):
        """THIS METHOD HANDLES ACCEPTING ALL INCOMING OFFERS"""
        state = self.user.state
        current_state = state.get_state(self.user)

        data = current_state['member'].get('defaultAccountData', {}).get('pendingInData') if current_state[
                'member'].get('defaultAccountData', {}).get('pendingInData') else []

        payload = json.dumps({"signerID": current_state['member']['memberDashboard'].get('memberID'),"credexIDs":[i.get('credexID') for i in data]})
        headers = {
            'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
            'Content-Type': 'application/json',
            'whatsappBotAPIkey': config('WHATSAPP_BOT_API_KEY'),
        }
        response = requests.request("PUT", f"{config('CREDEX')}/acceptCredexBulk", headers=headers, data=payload)
        print(response.content)
        if response.status_code == 200:
            self.refresh(reset=True)
            return self.wrap_text("> *🥳 Success*\n\n You have accepted all pending offers!", x_is_menu=True, back_is_cancel=False)
        return self.wrap_text("> *😞 Failed*\n\n Failed to accept all pending offers!", x_is_menu=True, back_is_cancel=False)

    @property
    def handle_action_pending_offers_in(self):
        """THIS METHOD HANDLES DISPLAYING INCOMING OFFERS"""
        state = self.user.state
        current_state = state.get_state(self.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state
        if state.option == "handle_action_display_offers":
            # data = current_state.get('pending') if current_state.get('pending') else []
            data = current_state['member'].get('defaultAccountData', {}).get('pendingInData') if current_state[
                'member'].get('defaultAccountData', {}).get('pendingInData') else []
            # print(data)
            if self.body in [str(i) for i in range(1, len(data) + 1)] or self.message['type'] == 'interactive':
                if data:
                    item = None
                    if self.body.isdigit():
                        item = data[int(self.body) - 1]
                    else:
                        for row in data:
                            if row.get('credexID') == self.body:
                                item = row
                                break

                    return {
                        "messaging_product": "whatsapp",
                        "recipient_type": "individual",
                        "to": self.user.mobile_number,
                        "type": "interactive",
                        "interactive": {
                            "type": "button",
                            "body": {
                                "text": ACCEPT_CREDEX.format(amount=item.get('formattedInitialAmount'),
                                                             party=item.get('counterpartyAccountName'),
                                                             type='Secured' if item.get('secured') else 'Unsecured')
                            },
                            "action": {
                                "buttons": [
                                    {
                                        "type": "reply",
                                        "reply": {
                                            "id": f"decline_{item.get('credexID')}",
                                            "title": "❌ Decline"
                                        }
                                    },
                                    {
                                        "type": "reply",
                                        "reply": {
                                            "id": f"accept_{item.get('credexID')}",
                                            "title": "✅ Accept"
                                        }
                                    }
                                ]
                            }
                        }
                    }

        if self.body == 'handle_action_pending_offers_in':
            rows = []
            menu_string = "> *📥 Pending Incoming*\n"
            count = 1
            data = current_state['member'].get('defaultAccountData', {}).get('pendingInData') if current_state[
                'member'].get('defaultAccountData', {}).get('pendingInData') else []
            print(data)
            for item in data[:10]:
                # due =  '' if 'Invalid date' == item.get('dueDate') else '\n        Due ' + item.get('dueDate')

                menu_string += f"\n{count}. *{item.get('formattedInitialAmount')}* from {item.get('counterpartyAccountName')}"
                print(menu_string)
                rows.append(
                    {
                        "id": item.get('credexID'),
                        "title": f"{item.get('formattedInitialAmount')}",
                        "description": f"from {item.get('counterpartyAccountName')}"
                    }
                )
                count += 1
            # current_state['pending'] = rows
            state.update_state(
                state=current_state,
                stage='handle_action_pending_offers_in',
                update_from="handle_action_pending_offers_in",
                option="handle_action_display_offers"
            )
            if not rows:
                menu_string = "*Empty*\n\n🪹 No pending offers to display!\n\n"
                rows = [
                    {
                        "id": "X",
                        "title": "🏡 Menu"
                    }
                ]
                return self.wrap_text(message=menu_string, extra_rows=rows)

            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self.user.mobile_number,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "body": {
                        "text": menu_string
                    },
                    "action":
                        {
                            "button": "✅ Accept All",
                            "sections": [
                                {
                                    "title": "Options",
                                    "rows": [
                                        {
                                            "id": "AcceptAllIncomingOffers",
                                            "title": "✅ Accept All"
                                        }
                                    ]
                                }
                            ]
                        }
                }
            }
        else:
            print("Outt >> 4", self.body, state.option)

    @property
    def handle_action_pending_offers_out(self):
        """THIS METHOD HANDLES DISPLAYING OUTGOING OFFERS"""
        state = self.user.state
        current_state = state.get_state(self.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        if state.option == "handle_action_display_offers":
            data = current_state['member'].get('defaultAccountData', {}).get('pendingOutData') if current_state[
                'member'].get('defaultAccountData', {}).get('pendingOutData') else []
            if self.body in [str(i) for i in range(1, len(data) + 1)] or self.message['type'] == 'interactive':
                if data:
                    item = None
                    if self.body.isdigit():
                        item = data[int(self.body) - 1]
                    else:
                        for row in data:
                            if row.get('credexID') == self.body:
                                item = row
                                break

                    return {
                        "messaging_product": "whatsapp",
                        "recipient_type": "individual",
                        "to": self.user.mobile_number,
                        "type": "interactive",
                        "interactive": {
                            "type": "button",
                            "body": {
                                "text": OUTGOING_CREDEX.format(amount=item.get('formattedInitialAmount'),
                                                               party=item.get('counterpartyAccountName'),
                                                               type='Secured' if item.get('secured') else 'Unsecured')
                            },
                            "action": {
                                "buttons": [
                                    {
                                        "type": "reply",
                                        "reply": {
                                            "id": f"cancel_{item.get('credexID')}",
                                            "title": "❌ Cancel"
                                        }
                                    }
                                ]
                            }
                        }
                    }

        if self.body == 'handle_action_pending_offers_out':
            rows = []
            menu_string = "> *📤 Pending Outgoing*\n\n*Offers*\n"
            count = 1
            data = current_state['member'].get('defaultAccountData', {}).get('pendingOutData') if current_state['member'].get('defaultAccountData', {}).get('pendingOutData') else []
            for item in data[:10]:
                counterparty = item.get('counterpartyAccountName')
                # due = '' if 'Invalid date' == item.get('dueDate') else ' Due ' + item.get('dueDate')
                menu_string += f"{count}. {item.get('formattedInitialAmount')} offered to\n        {counterparty}\n"
                rows.append(
                    {
                        "id": item.get('credexID'),
                        "title": f"{item.get('formattedInitialAmount')}",
                        "description": f"to {item.get('counterpartyAccountName')}"
                    }
                )
                count += 1

            state.update_state(
                state=current_state,
                stage='handle_action_pending_offers_out',
                update_from="handle_action_pending_offers_out",
                option="handle_action_display_offers"
            )

            if not rows:
                menu_string = "*Empty*\n\n🪹 No pending offers to display!\n\n"
                rows = [
                    {
                        "id": "X",
                        "title": "🏡 Menu"
                    }
                ]
                return self.wrap_text(message=menu_string, extra_rows=rows)

            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self.user.mobile_number,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "body": {
                        "text": menu_string
                    },
                    "action":
                        {
                            "button": "🕹️ Options",
                            "sections": [
                                {
                                    "title": "Options",
                                    "rows": rows
                                }
                            ]
                        }
                }
            }

        else:
            # TODO : HANDLE DISPLAY TXN
            pass

    @property
    def handle_action_offer_credex(self):
        """THIS METHOD HANDLES OFFERING CREDEX LOGIC"""
        state = self.user.state
        current_state = state.get_state(self.user)
        message = ''

        if not isinstance(current_state, dict):
            current_state = current_state.state

        if not current_state.get('member'):
            self.refresh()

        if not  current_state.get('member', {}).get('defaultAccountData', {}):
            for account in current_state['member']['accountDashboards']:
                if current_state['member']['memberDashboard']['accountIDS'][-1] == account.get('accountID'):
                    current_state['member']['defaultAccountData'] = account
                    break

                

        payload = {}
        if "=>" in f"{self.body}" or "->" f"{self.body}" or self.message['type'] == "nfm_reply":

            if not isinstance(current_state, dict):
                current_state = current_state.state
                
            if self.message['type'] == "nfm_reply":
                from datetime import datetime, timedelta
                payload = {
                    "authorizer_member_id": current_state['member']['memberDashboard'].get('memberID'),
                    "issuer_member_id": current_state['member']['defaultAccountData'].get('accountID') if current_state.get('member', {}).get('defaultAccountData', {}) else current_state['member']['memberDashboard']['accountIDS'][-1],
                    "handle": self.body.get('handle'),
                    "amount": self.body.get('amount'),
                    "dueDate": self.body.get('due_date') if self.body.get('due_date') else (datetime.now() + timedelta(weeks=4)).timestamp() * 1000,
                    "currency": self.body.get('currency'),
                    "securedCredex": True #if self.body.get('secured') else False,
                }

            if "=>" in f"{self.body}" or "->" f"{self.body}":
                if "=>" in f"{self.body}":
                    amount, user = f"{self.body}".split('=>')
                    if "=" in user:
                        user, _ = user.split("=")
                    from datetime import datetime
                    payload = {
                        "authorizer_member_id": current_state['member']['memberDashboard'].get('memberID'),
                        "issuer_member_id": current_state['member']['defaultAccountData'].get('accountID') if current_state.get('member', {}).get('defaultAccountData', {}) else current_state['member']['memberDashboard']['accountIDS'][-1],
                        "handle": user,
                        "amount": amount,
                        "dueDate": (datetime.now()).timestamp() * 1000,
                        "currency": current_state['member']['defaultAccountData']['defaultDenom'] if current_state.get('member', {}).get('defaultAccountData', {}) else current_state['member']['memberDashboard'].get('defaultDenom'),
                        "securedCredex": True
                    }

            if "->" in f"{self.body}":
                if '=' in f"{self.body}":
                    amount, user_date = f"{self.body}".split('->')
                    user, date = user_date.split('=')

                    try:
                        from datetime import datetime
                        # Try to parse the date string with the specified format
                        datetime.strptime(date, '%Y-%m-%d')

                    except ValueError:
                        # If a ValueError is raised, the date string is not in the correct format
                        return self.wrap_text(OFFER_CREDEX.format(message='*Invalid Due Date❗*'), x_is_menu=True)
                else:
                    amount, user = f"{self.body}".split('->')
                    date = None

                from datetime import datetime, timedelta
                payload = {
                    "authorizer_member_id": current_state['member']['memberDashboard'].get('memberID'),
                    "issuer_member_id": current_state['member']['defaultAccountData'].get('accountID') if current_state.get('member', {}).get('defaultAccountData', {}) else current_state['member']['memberDashboard']['accountIDS'][-1],
                    "handle": user,
                    "amount": amount,
                    "dueDate": datetime.strptime(date, '%Y-%m-%d').timestamp() * 1000 if date else (datetime.now() + timedelta(weeks=4)).timestamp() * 1000,
                    "currency": current_state['member']['defaultAccountData']['defaultDenom'] if current_state.get('member', {}).get('defaultAccountData', {}) else current_state['member']['memberDashboard'].get('defaultDenom'),
                    "securedCredex": False
                }


            serializer = OfferCredexSerializer(data=payload)
            if serializer.is_valid():
                accounts = []
                count = 1
                account_string = f""

                for account in current_state['member']['accountDashboards']:
                    account_string += f" *{count}.*  _{account.get('accountName')}_\n"
                    accounts.append(
                        {
                            "id": account.get('accountID'),
                            "title": f"👤 {account.get('accountName')}"
                        }
                    )

                    if count > 8:
                        break
                    count += 1

                count += 1
                response = CONFIRM_SECURED_CREDEX.format(
                    party=serializer.validated_data.get('full_name'),
                    amount=serializer.validated_data.get('InitialAmount'),
                    currency=serializer.validated_data.get('Denomination'),
                    source=current_state['member']['defaultAccountData'].get('accountName'),
                    handle=serializer.validated_data.pop('handle'),
                    secured='*secured*',
                    accounts=account_string

                ) if serializer.validated_data.get('securedCredex') else CONFIRM_UNSECURED_CREDEX.format(
                    party=serializer.validated_data.get('full_name'),
                    amount=serializer.validated_data.get('InitialAmount'),
                    currency=serializer.validated_data.get('Denomination'),
                    source=current_state['member']['defaultAccountData'].get('accountName'),
                    handle=serializer.validated_data.pop('handle'),
                    secured='*unsecured*',
                    date=f"*Due Date :* {serializer.validated_data.get('dueDate')}",
                    accounts=account_string
                )
                current_state['confirm_offer_payload'] = serializer.validated_data
                current_state['confirm_offer_payload']['secured'] = serializer.validated_data['securedCredex']
                state.update_state(
                    state=current_state,
                    stage='handle_action_offer_credex',
                    update_from="handle_action_offer_credex",
                    option="handle_action_confirm_offer_credex"
                )
                return {
                    "messaging_product": "whatsapp",
                    "to": self.user.mobile_number,
                    "recipient_type": "individual",
                    "type": "interactive",
                    "interactive": {
                        "type": "flow",
                        "body": {
                            "text": response
                        },
                        "action": {
                            "name": "flow",
                            "parameters": {
                                "flow_message_version": "3",
                                "flow_action": "navigate",
                                "flow_token": "not-used",
                                "flow_id": "382339094914403",
                                "flow_cta": "Sign & Send",
                                "flow_action_payload": {
                                    "screen": "OFFER_SECURED_CREDEX",
                                    "data": {
                                        "source_account": accounts
                                    }
                                }
                            }
                        }
                    }
            
                }
            else:
                for err in serializer.errors.keys():
                    if "This field is required." != serializer.errors[err][0]:
                        message = f'*{serializer.errors[err][0]}❗*'
                        break
        
        if state.option == "handle_action_confirm_offer_credex":    
            to_credex = current_state.get('confirm_offer_payload')
            to_credex['issuerAccountID'] = current_state['member']['defaultAccountData'].get('accountID')
            if self.message['type'] == "nfm_reply":
                print(self.message)
                to_credex['issuerAccountID'] = self.message['message']['source_account']

            
            to_credex['memberID'] =  current_state['member']['memberDashboard'].get('memberID')
            to_credex.pop("handle", None)
            if to_credex.get('securedCredex'):
                to_credex.pop('dueDate', None)
            
            to_credex.pop('secured', None)
            payload = json.dumps(current_state.get('confirm_offer_payload'))
            headers = {
                'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
                'Content-Type': 'application/json',
                'whatsappBotAPIkey': config('WHATSAPP_BOT_API_KEY'),
            }
            message = ''
            print("PAYLOAD : ", payload)
            response = requests.request("POST", f"{config('CREDEX')}/offerCredex", headers=headers, data=payload)
            print("RESPONSE : ", response.content)
            if response.status_code == 200:

                response = response.json()

                if response.get("offerCredexData", {}).get("credex"):
                    response = response.get("offerCredexData", {})
                    current_state.pop('confirm_offer_payload', {})
                    denom = current_state['member']['defaultAccountData']['defaultDenom']
                    current_state.pop('defaultAccountData', {})
                    CredexWhatsappService(payload={
                        "messaging_product": "whatsapp",
                        "preview_url": False,
                        "recipient_type": "individual",
                        "to": self.user.mobile_number,
                        "type": "text",
                        "text": {
                            "body": OFFER_SUCCESSFUL.format(
                                type='Secured Credex' if response['credex']['secured'] else 'Unsecured Credex',
                                amount=response['credex']['formattedInitialAmount'],
                                currency=denom,
                                recipient=response['credex']['counterpartyAccountName'],
                                source=current_state['member']['defaultAccountData'].get('accountName'),
                                secured='*Secured* credex' if response['credex']['secured'] else '*Unsecured* credex',
                            )
                        }
                    }).notify()
                    default = current_state['member']['defaultAccountData'].get('accountID')
                    current_state.get('member', {}).pop('defaultAccountData', {})

                    count = 0
                    for account in current_state['member']['accountDashboards']:
                        count += 1
                        if default == account.get('accountID'):
                            current_state['member']['defaultAccountData'] = account
                            break
                    
                    state.update_state(
                        state=current_state,
                        stage='handle_action_menu',
                        update_from="handle_action_menu",
                        option="handle_action_menu"
                    )
                    
                    self.refresh(reset=True)
                    self.body = current_state['member']['defaultAccountData'].get('accountHandle')
                    return self.handle_action_select_profile
                else:
                    current_state.pop('confirm_offer_payload', {})
                    message = self.format_synopsis(response.get("offerCredexData", {}).get('message').replace("Error:", ""))
                
            else:
                try:
                    current_state.pop('confirm_offer_payload', {})
                    message = self.format_synopsis(response.get("offerCredexData", {}).get('message').replace("Error:", ""))
                    return self.wrap_text(OFFER_FAILED.format(message=message), x_is_menu=True,
                                        back_is_cancel=False)
                except Exception as e:
                    print("E : ", e)
                    pass
                message = 'Invalid option selected'


        state.update_state(
            state=current_state,
            stage='handle_action_offer_credex',
            update_from="handle_action_offer_credex",
            option="handle_action_offer_credex"
        )
        from datetime import datetime, timedelta
        return {
                "messaging_product": "whatsapp",
                "to": self.user.mobile_number,
                "recipient_type": "individual",
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "body": {
                        "text": OFFER_CREDEX.format(message=self.format_synopsis(message))
                    },
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_action": "navigate",
                            "flow_token": "not-used",
                            "flow_id": "3435593326740751",
                            "flow_cta": " Offer Secured Credex",
                            "flow_action_payload": {
                                "screen": "MAKE_SECURE_OFFER",
                                "data": {
                                    "min_date": str((datetime.now() +timedelta(days=1)).timestamp()* 1000),
                                    "max_date": str((datetime.now() +timedelta(weeks=5)).timestamp()* 1000)

                                }
                            }
                        }
                    }
                }
            
            }

    def format_synopsis(self, synopsis, style=None):
        formatted_synopsis = ""
        words = synopsis.split()
        line_length = 0

        for word in words:
            # If adding the word exceeds the line length, start a new line
            if line_length + len(word) + 1 > 35:
                formatted_synopsis += "\n"
                line_length = 0
            if style:
                word = f"{style}{word}{style}"
            formatted_synopsis += word + " "
            line_length += len(word) + 1

        return formatted_synopsis.strip()

    def wrap_text(self, message, proceed_option=False, x_is_menu=False, include_back=False, navigate_is="Respond",
                  extra_rows=[], number=None, back_is_cancel=False, use_buttons=False, yes_or_no=False, custom={}, plain=False, include_menu=True):
        """THIS METHOD HANDLES ABSTRACTS CLOUDAPI MESSAGE DETAILS"""
        if use_buttons:
            rows = [
                {
                    "type": "reply",
                    "reply": {
                        "id": "N",
                        "title": "❌ No"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "Y",
                        "title": "✅ Yes"
                    }
                }
            ]
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": number or self.user.mobile_number,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {
                        "text": message
                    },
                    "action": {
                        "buttons": [
                            {
                                "type": "reply",
                                "reply": custom if custom else {
                                    "id": "X",
                                    "title": "🏡 Menu" if x_is_menu else "❌ Cancel"
                                }
                            }
                        ] if not yes_or_no else rows
                    }
                }
            }

        if len(message) > 1024 or plain:
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": number or self.user.mobile_number,
                "type": "text",
                "text": {
                    "body": message
                }
            }
        rows = extra_rows

        if proceed_option == True:
            rows.append({
                "id": "Y",
                "title": "✅ Continue"
            })
        
        if include_menu:
            rows.append({
                "id": "X",
                "title": "🏡 Menu"
            }
            )
        row_data = []
        keystore = []
        for row in rows:
            if row.get("id") not in keystore:
                row_data.append(row)
                keystore.append(row.get("id"))
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": number or self.user.mobile_number,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {
                    "text": message
                },
                "action":
                    {
                        "button": f"🕹️ {navigate_is}",
                        "sections": [
                            {
                                "title": "Control",
                                "rows": row_data
                            }
                        ]
                    }
            }
        }

    @property
    def handle_action_more_options(self):
        state = self.user.state
        current_state = state.get_state(self.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        if state.option == "handle_action_more_options":
            if self.body in ['1', 'action_perform_company']:
                return self.handle_action_create_business_account
            elif self.body in ['2', 'handle_action_authorize_member']:
                return self.handle_action_authorize_member
            elif self.body in ['3', 'handle_action_pending_offers_out']:
                self.body = 'handle_action_pending_offers_out'
                state.update_state(
                    state=current_state,
                    stage='handle_action_pending_offers_out',
                    update_from="handle_action_pending_offers_out",
                    option="handle_action_pending_offers_out"
                )
                return self.handle_action_pending_offers_out
            else:
                return {
                    "messaging_product": "whatsapp",
                    "preview_url": False,
                    "recipient_type": "individual",
                    "to": self.user.mobile_number,
                    "type": "text",
                    "text": {
                        "body": INVALID_ACTION
                    }
                }

        state.update_state(
            state=current_state,
            stage='handle_action_more_options',
            update_from="handle_action_more_options",
            option="handle_action_more_options"
        )
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self.user.mobile_number,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {
                    "text": MANAGE_ACCOUNTS.format(pending_out=len(
                        current_state['member'].get('defaultAccountData', {}).get('pendingOutData', [])))
                },
                "action":
                    {
                        "button": "🕹️ Options",
                        "sections": [
                            {
                                "title": "Options",
                                "rows": [
                                    {
                                        "id": "action_perform_company",
                                        "title": "💼 Create Business"
                                    }, {
                                        "id": "handle_action_authorize_member",
                                        "title": f"🗝️ Authorize Member",
                                        "description": "Assign someone to transact for one of your companies."
                                    },
                                    {
                                        "id": "handle_action_pending_offers_out",
                                        "title": f"📥 Pending Outgoing"
                                    }
                                ]
                            }
                        ]
                    }
            }
        }

    @property
    def handle_action_authorize_member(self):
        state = self.user.state
        current_state = state.get_state(self.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        if state.option == "select_option":
            if self.body == '1':

                state.update_state(
                    state=current_state,
                    stage='handle_action_authorize_member',
                    update_from="handle_action_authorize_member",
                    option="get_handle"
                )
                return self.wrap_text(ADD_MERMBER.format(company=current_state['member'].get('defaultAccountData', {}).get('accountName'), message=''))
            else:
                if self.body.isdigit():
                    if int(self.body) in range(2, len(current_state.get('member', {}).get('defaultAccountData', {}).get('authFor', []))+1):
                        print("Remove > ", current_state.get('member', {}).get('defaultAccountData', {}).get('authFor', [])[int(self.body)-2])
                        url = f"{config('CREDEX')}/unauthorizeForAccount"

                        payload = json.dumps(
                            {
                                "AccountIDtoBeUnauthorized": current_state.get('member', {}).get('defaultAccountData', {}).get('authFor', [])[int(self.body)-2]['memberID'],
                                "memberIDtoBeUnauthorized": current_state.get('member', {}).get('defaultAccountData', {}).get('authFor', [])[int(self.body)-2]['memberID'],
                                "accountID": current_state['member'].get('defaultAccountData', {}).get('accountID'),
                                "ownerID": current_state['member']['memberDashboard'].get('memberID')
                            }
                        )

                        headers = {
                            'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
                            'Content-Type': 'application/json',
                            'whatsappBotAPIkey': config('WHATSAPP_BOT_API_KEY'),
                        }
                        # print(payload)
                        response = requests.request("POST", url, headers=headers, data=payload)
                        # print(response.content)
                        if response.status_code == 200:
                            data = response.json()
                            # print(data)
                            if data:
                                self.refresh(reset=False)
                                return self.wrap_text(DEAUTHORIZATION_SUCCESSFUL.format(member=f"{current_state.get('member', {}).get('defaultAccountData', {}).get('authFor', [])[int(self.body)-2].get('firstname')} {current_state.get('member', {}).get('defaultAccountData', {}).get('authFor', [])[int(self.body)-2].get('lastname')}", company=current_state['member'].get('defaultAccountData', {}).get(
                                    'accountName')), x_is_menu=True, back_is_cancel=False)
                return self.wrap_text(INVALID_ACTION)
        
        elif state.option == "get_handle":
            
            url = f"{config('CREDEX')}/getMemberByHandle"

            payload = json.dumps({
                "memberHandle": self.body.lower()
            })
            headers = {
                'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
                'Content-Type': 'application/json',
                'whatsappBotAPIkey': config('WHATSAPP_BOT_API_KEY'),
            }

            response = requests.request("GET", url, headers=headers, data=payload)
            # print(response.content)
            data = response.json()
            # print(data)
            if not data.get('Error'):
                data = data['memberData']
                data['handle'] = self.body.lower()
                print("1...", f"authorize_for_{current_state['member'].get('defaultAccountData', {}).get('accountName')}")
                current_state[
                    f"authorize_for_{current_state['member'].get('defaultAccountData', {}).get('accountName')}"] = data
                print(data)
                state.update_state(
                    state=current_state,
                    stage='handle_action_authorize_member',
                    update_from="handle_action_authorize_member",
                    option="confirm_authorization"
                )
                return self.wrap_text(CONFIRM_AUTHORIZATION.format(member=data.get('memberName'),
                                                                   company=current_state['member'].get(
                                                                       'defaultAccountData', {}).get('accountName')),
                                      x_is_menu=True, back_is_cancel=False, navigate_is="🏡 Menu", extra_rows=[{"id": '1', "title": "✅ Authorize"}, {"id": '2', "title": "❌ Cancel"}])
            else:
                self.wrap_text(ADD_MERMBER.format(company=current_state['member'].get('defaultAccountData', {}).get('accountName'), message="Member not found!"))

        if state.option == "confirm_authorization":
            # print("INSIDE CONFIRM")
            if self.body not in ['1', '2']:
                return {
                    "messaging_product": "whatsapp",
                    "preview_url": False,
                    "recipient_type": "individual",
                    "to": self.user.mobile_number,
                    "type": "text",
                    "text": {
                        "body": INVALID_ACTION
                    }
                }

            if self.body == '1':
                url = f"{config('CREDEX')}/authorizeForAccount"

                payload = json.dumps({
                    "AccountHandleToBeAuthorized":current_state[
                        f"authorize_for_{current_state['member'].get('defaultAccountData', {}).get('accountName')}"].get('handle'),
                    "memberHandleToBeAuthorized": current_state[
                        f"authorize_for_{current_state['member'].get('defaultAccountData', {}).get('accountName')}"].get('handle'),
                    "accountID": current_state['member'].get('defaultAccountData', {}).get('accountID'),
                    "ownerID": current_state['member']['memberDashboard'].get('memberID')
                })

                headers = {
                    'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
                    'Content-Type': 'application/json',
                    'whatsappBotAPIkey': config('WHATSAPP_BOT_API_KEY'),
                }
                # print(payload)
                response = requests.request("POST", url, headers=headers, data=payload)
                # print(response.content)
                if response.status_code == 200:
                    data = response.json()
                    # print(data)
                    if data.get('message') == "account authorized":
                        self.refresh(reset=False, silent=True)
                        return self.wrap_text(AUTHORIZATION_SUCCESSFUL.format(member=current_state[
                            f"authorize_for_{current_state['member'].get('defaultAccountData', {}).get('accountName')}"].get(
                            'memberName'), company=current_state['member'].get('defaultAccountData', {}).get(
                            'accountName')), x_is_menu=True, back_is_cancel=False)
                    else:
                        return self.wrap_text(INVALID_ACTION)
            return self.wrap_text(AUTHORIZATION_FAILED.format(message=data.get('message', "authorization failed")))

        state.update_state(
            state=current_state,
            stage='handle_action_authorize_member',
            update_from="handle_action_authorize_member",
            option="select_option"
        )
        menu_string = ""
        rows = [
            {
                "id": '1',
                "title": f"➕ Add new member"
            }
        ]
        count = 2

        for user in current_state.get('member', {}).get('defaultAccountData', {}).get('authFor', []):
            menu_string += f"{count}. Remove {user.get('firstname')} {user.get('lastname')}\n"
            rows.append({
                "id": count,
                "title": f"❌ {user.get('firstname')} {user.get('lastname')}"
            })
            count += 1
        
        rows.append(
            {
                "id": "X",
                "title": "🏡 Menu"
            }
        )
            
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self.user.mobile_number,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {
                    "text": MEMBERS.format(members=menu_string)
                },
                "action":
                    {
                        "button": "🏡 Menu",
                        "sections": [
                            {
                                "title": "Options",
                                "rows":rows
                            }
                        ]
                    }
            }
        }
