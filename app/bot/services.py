import json
import locale
import requests
from decouple import config
from bot.utils import CredexWhatsappService
from bot.serializers.company import CompanyDetailsSerializer
from bot.serializers.offers import OfferCredexSerializer
from bot.serializers.members import MemberDetailsSerializer
from bot.screens import *
from bot.constants import *


locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')


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
            response = self.refresh()
            if response and state.stage != "handle_action_register":
                return response
            

        # OVERRIDE FLOW IF USER WANTS TO ACCEPT, DECLINE OR CANCEL CREDEXES AND ROUTE TO THE APPROPRIATE METHOD
        if f"{self.body}".startswith("accept_") or f"{self.body}".startswith("cancel_") or f"{self.body}".startswith(
                "decline_") or f"{self.body}" == "AcceptAllIncomingOffers":
            if f"{self.body}".startswith("accept_"):
                return self.handle_action_accept_offer
            elif f"{self.body}".startswith("decline_"):
                return self.handle_action_decline_offer
            elif f"{self.body}".startswith("cancel_"):
                return self.handle_action_cancel_offer
            elif f"{self.body}" == "AcceptAllIncomingOffers":
                return self.handle_action_accept_all_incoming_offers

        # IF PROMPT IS IN GREETINGS THEN CLEAR CACHE AND FETCH MENU
        if f"{self.body}".lower() in GREETINGS and f"{self.body}".lower() not in ["y", "yes", "retry", "n", "no"]:
            self.user.state.reset_state()
            state = self.user.state
            current_state = state.get_state(self.user)
            if not isinstance(current_state, dict):
                current_state = current_state.state
            current_state = {"state": {}, 'member': current_state.get('member')}
            state.update_state(current_state, update_from='menu')
            return self.handle_action_menu

            # IF USER IS AT MENU STAGE FIND THE NEXT ROUTE BASED ON MESSAGE
        if self.user.state.stage == "handle_action_menu":
            selected_action = MENU_OPTIONS.get(f"{self.body}".lower())
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

    def refresh(self):
        """THIS METHOD REFRESHES MEMBER INFO BY MAKING AN API CALL TO CREDEX CALL"""
        state = self.user.state
        current_state = state.get_state(self.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        url = f"{config('CREDEX')}/whatsAppLogin"

        payload = json.dumps({
            "phone": self.message['from']
        })
        headers = {
            'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
            'Content-Type': 'application/json',
            'API-KEY': config('CREDEX_API_CREDENTIALS'),
        }
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
        response = requests.request("GET", url, headers=headers, data=payload)
        if response.status_code == 200:
            current_state['member'] = response.json()
            current_state['member'].pop('defaultAccountData', None)
            state.update_state(
                state=current_state,
                stage='handle_action_select_profile',
                update_from="handle_action_select_profile",
                option="select_account_to_use"
            )
        else:
            state.update_state(
                state=current_state,
                stage='handle_action_register',
                update_from="refresh",
                option="handle_action_register"
            )
            return {
                "messaging_product": "whatsapp",
                "to": self.user.mobile_number,
                "recipient_type": "individual",
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "body": {
                        "text": REGISTER
                    },
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_action": "navigate",
                            "flow_token": "not-used",
                            "flow_id": config('WHATSAPP_REGISTRATION_FLOW_ID'),
                            "flow_cta": "Register",
                            "flow_action_payload": {
                                "screen": "REGISTRATION"
                            }
                        }
                    }
                }
            }

    @property
    def handle_action_switch_account(self):
        state = self.user.state
        current_state = state.get_state(self.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        self.body = "Hi"
        self.message['message'] = "Hi"
        self.refresh()
        return self.handle_action_menu

    @property
    def handle_action_register(self):
        """HANDLING CLIENT REGISTRATIONS"""

        if self.message['type'] == "nfm_reply":
            payload = {
                "first_name": self.body.get('firstName'),
                "last_name": self.body.get('lastName'),
                "phone_number": self.message['from'],
                "email": self.body.get('email'),

            }
            message = ""
            serializer = MemberDetailsSerializer(data=payload)
            print(serializer.is_valid(), serializer.errors)
            if serializer.is_valid():
                url = f"{config('CREDEX')}/createMember"
                headers = {
                    'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
                    'Content-Type': 'application/json'
                }
                print(payload)
                response = requests.request("POST", url, headers=headers, json=serializer.validated_data)
                print("########### ", response.content)
                if response.status_code == 200:

                    return self.wrap_text(
                        REGISTRATION_COMPLETE.format(
                            full_name=f"{self.body.get('firstName')} {self.body.get('lastName')}",
                            username=self.body.get('email'),
                            phone=self.message['from']
                        ),
                        x_is_menu=True, back_is_cancel=False
                    )
                else:
                    try:
                        if "Internal Server Error" in response.json().get('error'):
                            message = "Failed to perform action"
                        else:
                            message = response.json().get('error')

                    except Exception as e:
                        pass
                    print(response.content)

            return {
                "messaging_product": "whatsapp",
                "to": self.user.mobile_number,
                "recipient_type": "individual",
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "body": {
                        "text": COMPANY_REGISTRATION.format(message=message)
                    },
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_action": "navigate",
                            "flow_token": "not-used",
                            "flow_id": config('WHATSAPP_COMPANY_REGISTRATION_FLOW_ID'),
                            "flow_cta": "Register",
                            "flow_action_payload": {
                                "screen": "COMPANY"
                            }
                        }
                    }
                }
            }

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
                "ownerID": current_state['member']['loginData']['humanMemberData'].get('memberID'),
                "companyname": self.body.get('firstName'),
                "defaultDenom": self.body.get('currency'),
                "handle": self.body.get('email')

            }
            serializer = CompanyDetailsSerializer(data=payload)

            if serializer.is_valid():
                url = f"{config('CREDEX')}/createCompany"
                headers = {
                    'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
                    'Content-Type': 'application/json'
                }
                response = requests.request("POST", url, headers=headers, json=serializer.validated_data)
                if response.status_code == 200:
                    self.refresh()
                    return self.wrap_text(
                        REGISTRATION_COMPLETE.format(
                            full_name=f"{self.body.get('firstName')}",
                            username=self.body.get('email'),
                            phone=self.message['from']
                        ),
                        x_is_menu=True, back_is_cancel=False, navigate_is='🏡 Menu'
                    )
                else:
                    try:
                        if "Internal Server Error" in response.json().get('error'):
                            message = "Failed to perform action"
                        else:
                            message = response.json().get('error')
                    except Exception as e:
                        pass
                    print(response.content)
            else:
                print(serializer.errors)
        state.update_state(
            state=current_state,
            stage='handle_action_create_business_account',
            update_from="handle_action_create_business_account",
            option="handle_action_create_business_account"
        )
        return {
            "messaging_product": "whatsapp",
            "to": self.user.mobile_number,
            "recipient_type": "individual",
            "type": "interactive",
            "interactive": {
                "type": "flow",
                "body": {
                    "text": COMPANY_REGISTRATION.format(message=message)
                },
                "action": {
                    "name": "flow",
                    "parameters": {
                        "flow_message_version": "3",
                        "flow_action": "navigate",
                        "flow_token": "not-used",
                        "flow_id": config('WHATSAPP_COMPANY_REGISTRATION_FLOW_ID'),
                        "flow_cta": "Create",
                        "flow_action_payload": {
                            "screen": "COMPANY"
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

        if not isinstance(current_state, dict):
            current_state = current_state.state

        if not current_state['member'].get('defaultAccountData'):
            return self.handle_action_select_profile

        pending_in = 0
        if current_state['member']['defaultAccountData']['pendingInData']:
            pending_in = len(current_state['member']['defaultAccountData']['pendingInData'])

        secured = ""
        for item in current_state['member']['defaultAccountData']['balanceData']['securedNetBalancesByDenom']:
            secured += f" *{item}* \n"
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self.user.mobile_number,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {
                    "text": HOME.format(
                        balance=BALANCE.format(
                            securedNetBalancesByDenom=
                            current_state['member']['defaultAccountData']['balanceData']['securedNetBalancesByDenom'][
                                0] if current_state['member']['defaultAccountData']['balanceData'][
                                'securedNetBalancesByDenom'] else "$0.00",
                            totalPayables=current_state['member']['defaultAccountData']['balanceData'][
                                'unsecuredBalancesInDefaultDenom']['totalPayables'],
                            totalReceivables=current_state['member']['defaultAccountData']['balanceData'][
                                'unsecuredBalancesInDefaultDenom']['totalReceivables'],
                            netPayRec=current_state['member']['defaultAccountData']['balanceData'][
                                'unsecuredBalancesInDefaultDenom']['netPayRec'],
                            netCredexAssetsInDefaultDenom=current_state['member']['defaultAccountData']['balanceData'][
                                'netCredexAssetsInDefaultDenom']
                        ),
                        pending_in=pending_in,
                        handle=current_state['member']['defaultAccountData']['handle']
                    )
                },
                "action":
                    {
                        "button": "🕹️ Choose",
                        "sections": [
                            {
                                "title": "Options",
                                "rows":
                                    [
                                        {
                                            "id": "handle_action_pending_offers_in",
                                            "title": f"📥 Pending Offers"
                                        },
                                        {
                                            "id": "handle_action_switch_account",
                                            "title": "🔀 Switch Account",
                                        },
                                        {
                                            "id": "handle_action_transactions",
                                            "title": f"📒 Review Ledger",
                                        },
                                        {
                                            "id": "handle_action_offer_credex",
                                            "title": f"💸 Offer Credex",
                                        },
                                        {
                                            "id": "handle_action_more_options",
                                            "title": f"💼 More Options",
                                        }
                                    ]
                            }
                        ]
                    }
            }
        }

    @property
    def handle_action_select_profile(self):
        """HANDLES MENU STAGE GIVING THE USER THE MAIN MENU"""
        state = self.user.state
        current_state = state.get_state(self.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        if not current_state.get('member'):
            self.refresh()
            # print(response.text)

        if state.option == "select_account_to_use":
            options = {}
            count = 1
            for acc in current_state['member']['loginData']['dashboardData']:
                options[str(count)] = int(count) - 1
                options[acc.get('handle')] = int(count) - 1
                count += 1

            if options.get(self.body) is not None:
                current_state['member']['defaultAccountData'] = current_state['member']['loginData']['dashboardData'][
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
                    if self.body in [str(len(current_state['member']['loginData']['dashboardData']) + 1),
                                     "handle_action_create_business_account"]:
                        return self.handle_action_create_business_account
                    elif self.body in [str(len(current_state['member']['loginData']['dashboardData']) + 2),
                                       "handle_action_find_agent"]:
                        return self.wrap_text("Agents")

        accounts = []
        count = 1
        account_string = f""
        for account in current_state['member']['loginData']['dashboardData']:
            account_string += f" *{count}.* 👤 _{account.get('displayName')}_\n"
            accounts.append(
                {
                    "id": account.get('handle'),
                    "title": f"👤 {account.get('displayName')}"
                }
            )

            if count > 7:
                break
            count += 1

        account_string += f" *{count}.* 💼 _Create Business Account_\n"
        accounts.append(
            {
                "id": "handle_action_create_business_account",
                "title": f"💼 Create Account"
            }
        )
        count += 1

        account_string += f" *{count}.* 🏦 _Find VimbisoPay Agents_\n"
        accounts.append(
            {
                "id": "handle_action_find_agent",
                "title": f"🏦 Find Agent"
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
                    "text": ACCOUNT_SELECTION.format(greeting=get_greeting(), accounts=account_string,
                                                     first_name=current_state['member']['loginData'][
                                                         'humanMemberData'].get('displayName'))
                },
                "action":
                    {
                        "button": "🕹️ Choose",
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
                    print(current_state['current_page'][int(self.body) - 1])
                    self.body = current_state['current_page'][int(self.body) - 1]['id']

            url = f"{config('CREDEX')}/getCredex"

            payload = json.dumps({
                "credexID": self.body,
                "memberID": current_state['member']['defaultAccountData'].get('memberID'),
            })
            headers = {
                'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
                'Content-Type': 'application/json'
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
                                    counterpartyDisplayname=credex['credexData'].get('counterpartyDisplayname'),
                                    date=credex['credexData'].get('dateTime') if credex['credexData'].get(
                                        'dateTime') else 'N/A',
                                    type=credex['credexData'].get('transactionType')
                                )
                            },
                            "action":
                                {
                                    "button": "🕹️ Choose",
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

            menu_string = "*Empty*\n\n🪹 No transactions found!\n\n"
            rows = [
                {
                    "id": "X",
                    "title": "🏡 Menu"
                }
            ]
            return self.wrap_text(message=menu_string, extra_rows=rows)

        url = f"{config('CREDEX')}/getLedger"

        payload = json.dumps({
            "memberID": current_state['member']['defaultAccountData'].get('memberID'),
            "numRows": 8,
            "startRow": (page_number * 7) - 7
        })
        headers = {
            'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
            'Content-Type': 'application/json',
            'API-KEY': config('CREDEX_API_CREDENTIALS'),
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

                menu_string += f"{count}. *{txn.get('formattedInitialAmount')}*\n        {'to ' if '-' in txn.get('formattedInitialAmount') else 'from '}{txn.get('counterpartyDisplayname')}\n\n"
                rows.append({
                    "id": txn.get('credexID'),
                    "title": f"{txn.get('formattedInitialAmount').replace('-', '')} {'DEBIT ' if '-' in txn.get('formattedInitialAmount') else 'CREDIT '}",
                    "description": f"{txn.get('formattedInitialAmount')} {'to ' if '-' in txn.get('formattedInitialAmount') else 'from '}{txn.get('counterpartyDisplayname')}"
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
                                "button": "🕹️ Choose",
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
            "credexID": self.body.split("_")[-1],
            "memberID": current_state['member']['loginData']['humanMemberData'].get('memberID'),
            "accountID": current_state['member']['defaultAccountData'].get('memberID')
        })
        headers = {
            'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
            'Content-Type': 'application/json',
            'API-KEY': config('CREDEX_API_CREDENTIALS'),
        }
        response = requests.request("PUT", f"{config('CREDEX')}/acceptCredex", headers=headers, data=payload)
        if response.status_code == 200:
            try:
                current_state['member']['defaultAccountData']['pendingInData'] = response.get("dashboardData", {}).get(
                    "pendingInData", {})
                current_state['member']['defaultAccountData']['pendingOutData'] = response.get("dashboardData", {}).get(
                    "pendingOutData", {})
                current_state['member']['defaultAccountData']['balanceData'] = response.get("dashboardData", {}).get(
                    "balanceData", {})
            except Exception as e:
                print("ERROR FETCHING ", e)
            return self.wrap_text("> *🥳 Success*\n\n Offer successfully accepted!", x_is_menu=True,
                                  back_is_cancel=False)
        return self.wrap_text("> *😞 Failed*\n\n Failed to accept offer!", x_is_menu=True, back_is_cancel=False)

    @property
    def handle_action_decline_offer(self):
        """THIS METHOD HANDLES DECLINING AN OFFER"""
        state = self.user.state
        current_state = state.get_state(self.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        payload = json.dumps({
            "credexID": self.body.split("_")[-1],
            "memberID": current_state['member']['defaultAccountData'].get('memberID')
        })
        headers = {
            'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
            'Content-Type': 'application/json',
            'API-KEY': config('CREDEX_API_CREDENTIALS'),
        }
        response = requests.request("PUT", f"{config('CREDEX')}/declineCredex", headers=headers, data=payload)
        if response.status_code == 200:
            self.refresh()
            return self.wrap_text("> *🥳 Success*\n\n Offer successfully declined!", x_is_menu=True,
                                  back_is_cancel=False)
        return self.wrap_text("> *😞 Failed*\n\n Failed to decline offer!", x_is_menu=True, back_is_cancel=False)

    @property
    def handle_action_cancel_offer(self):
        """THIS METHOD HANDLES CANCELLING A SINGLE OFFER"""
        state = self.user.state
        current_state = state.get_state(self.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        payload = json.dumps({
            "credexID": self.body.split("_")[-1],
            "memberID": current_state['member']['defaultAccountData'].get('memberID')
        })
        headers = {
            'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
            'Content-Type': 'application/json',
            'API-KEY': config('CREDEX_API_CREDENTIALS'),
        }
        response = requests.request("PUT", f"{config('CREDEX')}/cancelCredex", headers=headers, data=payload)
        if response.status_code == 200:
            self.refresh()
            return self.wrap_text("> *🥳 Success*\n\n Offer successfully cancelled!", x_is_menu=True,
                                  back_is_cancel=False)
        return self.wrap_text("> *😞 Failed*\n\n Failed to cancel offer!", x_is_menu=True, back_is_cancel=False)

    @property
    def handle_action_accept_all_incoming_offers(self):
        """THIS METHOD HANDLES ACCEPTING ALL INCOMING OFFERS"""
        state = self.user.state
        current_state = state.get_state(self.user)

        payload = json.dumps({
            "credexID": self.body.split("_")[-1],
            "memberID": current_state['member']['defaultAccountData'].get('memberID')
        })
        headers = {
            'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
            'Content-Type': 'application/json',
            'API-KEY': config('CREDEX_API_CREDENTIALS'),
        }
        response = requests.request("PUT", f"{config('CREDEX')}/acceptCredexBulk", headers=headers, data=payload)
        if response.status_code == 200:
            self.refresh()
            return self.wrap_text("> *🥳 Success*\n\n Accepted all successfully!", x_is_menu=True, back_is_cancel=False)
        return self.wrap_text("> *😞 Failed*\n\n Failed to accept all!", x_is_menu=True, back_is_cancel=False)

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
                                                             party=item.get('counterpartyDisplayname'),
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
            menu_string = "> *📥 Pending Incoming*\n\n"
            count = 1
            data = current_state['member'].get('defaultAccountData', {}).get('pendingInData') if current_state[
                'member'].get('defaultAccountData', {}).get('pendingInData') else []
            for item in data[:10]:
                menu_string += f"{count}. *{item.get('formattedInitialAmount')}*\n        from {item.get('counterpartyDisplayname')}\n"
                rows.append(
                    {
                        "id": item.get('credexID'),
                        "title": f"{item.get('formattedInitialAmount')}",
                        "description": f"from {item.get('counterpartyDisplayname')}"
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
                                                               party=item.get('counterpartyDisplayname'),
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
            data = current_state['member'].get('defaultAccountData', {}).get('pendingOutData') if current_state[
                'member'].get('defaultAccountData', {}).get('pendingOutData') else []
            for item in data[:10]:
                counterparty = item.get('counterpartyDisplayname').replace(' ', '\n         ', 1)
                menu_string += f"{count}. *{item.get('formattedInitialAmount')}* to {counterparty}\n"
                rows.append(
                    {
                        "id": item.get('credexID'),
                        "title": f"{item.get('formattedInitialAmount')}",
                        "description": f"to {item.get('counterpartyDisplayname')}"
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
                            "button": "🕹️ Choose",
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

        payload = {}
        if "=>" in f"{self.body}" or "->" f"{self.body}" or self.message['type'] == "nfm_reply":
            if self.message['type'] == "nfm_reply":
                payload = {
                    "authorizer_member_id": current_state['member']['loginData']['humanMemberData'].get('memberID'),
                    "issuer_member_id": current_state['member']['defaultAccountData'].get('memberID'),
                    "recipient_phone_number": self.body.get('recipent_phone_number'),
                    "amount": self.body.get('amount'),
                    "dueDate": self.body.get('dueDate'),
                    "currency": self.body.get('currency'),
                    "securedCredex": True if self.body.get('securedCredex') else False,
                }

            if "=>" in f"{self.body}" or "->" f"{self.body}":
                if "=>" in f"{self.body}":
                    amount, user = f"{self.body}".split('=>')
                    if "=" in user:
                        user, _ = user.split("=")
                    from datetime import datetime, timedelta
                    payload = {
                        "authorizer_member_id": current_state['member']['loginData']['humanMemberData'].get('memberID'),
                        "issuer_member_id": current_state['member']['defaultAccountData'].get('memberID'),
                        "handle": user,
                        "amount": amount,
                        "dueDate": (datetime.now() + timedelta(weeks=4)).timestamp() * 1000,
                        "currency": current_state['member']['defaultAccountData']['defaultDenom'],
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
                    return self.wrap_text(OFFER_CREDEX.format(message='*Missing Due Date❗*'), x_is_menu=True)
                payload = {
                    "authorizer_member_id": current_state['member']['loginData']['humanMemberData'].get('memberID'),
                    "issuer_member_id": current_state['member']['defaultAccountData'].get('memberID'),
                    "handle": user,
                    "amount": amount,
                    "dueDate": datetime.strptime(date, '%Y-%m-%d').timestamp() * 1000,
                    "currency": current_state['member']['defaultAccountData']['defaultDenom'],
                    "securedCredex": False
                }

            serializer = OfferCredexSerializer(data=payload)

            if serializer.is_valid():
                accounts = []
                count = 1

                account_string = f""
                for account in current_state['member']['loginData']['dashboardData']:
                    account_string += f" *{count}.*  _{account.get('displayName')}_\n"
                    accounts.append(
                        {
                            "id": account.get('handle'),
                            "title": f"👤 {account.get('handle')}"
                        }
                    )

                    if count > 9:
                        break
                    count += 1

                account_string += f" *{count}.*  _Cancel_\n"
                accounts.append(
                    {
                        "id": "handle_action_create_business_account",
                        "title": f"❌ Cancel"
                    }
                )
                count += 1
                response = CONFIRM_SECURED_CREDEX.format(
                    party=serializer.validated_data.get('full_name'),
                    amount=serializer.validated_data.get('InitialAmount'),
                    currency=serializer.validated_data.get('Denomination'),
                    handle=serializer.validated_data.pop('handle'),
                    secured='*secured*',
                    accounts=account_string

                ) if serializer.validated_data.get('securedCredex') else CONFIRM_UNSECURED_CREDEX.format(
                    party=serializer.validated_data.get('full_name'),
                    amount=serializer.validated_data.get('InitialAmount'),
                    currency=serializer.validated_data.get('Denomination'),
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
                return self.wrap_text(response, extra_rows=accounts, navigate_is="Select Acc")
            else:
                for err in serializer.errors.keys():
                    if "This field is required." != serializer.errors[err][0]:
                        message = f'*{serializer.errors[err][0]}❗*'
                        break

        if current_state.get('confirm_offer_payload'):
            accounts = []
            count = 1
            for account in current_state['member']['loginData']['dashboardData']:
                accounts.append(account.get('memberID'))
                count += 1
            accounts.append("Cancel")

            if str(self.body).isdigit():
                self.body = accounts[int(self.body) - 1] if int(self.body) <= len(accounts) else "out_of_range"
            if self.body in accounts:
                if self.body in ['CANCEL', 'Cancel', 'cancel']:
                    current_state.pop('confirm_offer_payload')
                    message = '*Offer Cancelled By User❗*'
                else:
                    current_state['confirm_offer_payload']['issuerMemberID'] = self.body
                    url = f"{config('CREDEX')}/offerCredex"
                    if current_state['confirm_offer_payload'].get('securedCredex'):
                        # secured = current_state['confirm_offer_payload'].pop('securedCredex')
                        current_state['confirm_offer_payload'].pop('dueDate')
                        current_state['confirm_offer_payload'].pop('full_name')
                    else:
                        current_state['confirm_offer_payload'].pop('full_name', None)
                        current_state['confirm_offer_payload'].pop('secured', None)

                    to_credex = current_state.get('confirm_offer_payload')
                    to_credex.pop("handle", None)
                    payload = json.dumps(current_state.get('confirm_offer_payload'))
                    headers = {
                        'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
                        'Content-Type': 'application/json',
                        'API-KEY': config('CREDEX_API_CREDENTIALS'),
                    }
                    message = ''
                    response = requests.request("POST", url, headers=headers, data=payload)
                    if response.status_code == 200:

                        response = response.json()
                        try:
                            current_state['member']['defaultAccountData']['pendingInData'] = response.get(
                                "dashboardData", {}).get("pendingInData", {})
                            current_state['member']['defaultAccountData']['pendingOutData'] = response.get(
                                "dashboardData", {}).get("pendingOutData", {})
                            current_state['member']['defaultAccountData']['balanceData'] = response.get("dashboardData",
                                                                                                        {}).get(
                                "balanceData", {})
                        except Exception as e:
                            print("ERROR FETCHING ", e)

                        if response.get("offerCredexData", {}).get("credex"):
                            current_state.pop('confirm_offer_payload', {})
                            return self.wrap_text(OFFER_SUCCESSFUL.format(
                                type='Secured Credex' if response['credex']['secured'] else 'Unsecured Credex',
                                amount=response['credex']['formattedInitialAmount'],
                                currency=current_state['member']['defaultAccountData']['defaultDenom'],
                                recipient=response['credex']['counterpartyDisplayname'],
                                secured='yes' if response['credex']['secured'] else 'no'
                            ), x_is_menu=True, back_is_cancel=False)
                        else:
                            current_state.pop('confirm_offer_payload', {})
                            message = self.format_synopsis(response.get("offerCredexData", {}).get('message'))
                    try:
                        current_state.pop('confirm_offer_payload', {})
                        message = self.format_synopsis(response.get("offerCredexData", {}).get('message'))
                        return self.wrap_text(OFFER_FAILED.format(message=message), x_is_menu=True,
                                              back_is_cancel=False)
                    except Exception as e:
                        print("E : ", e)
                        pass

                current_state.pop('confirm_offer_payload', {})
                return self.wrap_text(OFFER_FAILED.format(message=message), x_is_menu=True, back_is_cancel=False)
            else:
                message = 'Invalid option selected'
        state.update_state(
            state=current_state,
            stage='handle_action_offer_credex',
            update_from="handle_action_offer_credex",
            option="handle_action_offer_credex"
        )

        return self.wrap_text(OFFER_CREDEX.format(message=message))

    def format_synopsis(self, synopsis, style=None):
        formatted_synopsis = ""
        words = synopsis.split()
        line_length = 0

        for word in words:
            # If adding the word exceeds the line length, start a new line
            if line_length + len(word) + 1 > 30:
                formatted_synopsis += "\n"
                line_length = 0
            if style:
                word = f"{style}{word}{style}"
            formatted_synopsis += word + " "
            line_length += len(word) + 1

        return formatted_synopsis.strip()

    def wrap_text(self, message, proceed_option=False, x_is_menu=False, include_back=False, navigate_is="Navigate",
                  extra_rows=[], number=None, back_is_cancel=False, use_buttons=False, yes_or_no=False, custom={}):
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

        if len(message) > 1024:
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
                        "button": "🕹️ Choose",
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

        message = ''

        if state.option == "get_handle":
            url = f"{config('CREDEX')}/getMemberByHandle"

            payload = json.dumps({
                "handle": self.body.lower()
            })
            headers = {
                'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
                'Content-Type': 'application/json'
            }

            response = requests.request("GET", url, headers=headers, data=payload)
            data = response.json()
            if not data.get('Error'):
                data = data['memberData']
                data['handle'] = self.body.lower()
                current_state[
                    f"authorize_for_{current_state['member'].get('defaultAccountData', {}).get('displayName')}"] = data
                state.update_state(
                    state=current_state,
                    stage='handle_action_authorize_member',
                    update_from="handle_action_authorize_member",
                    option="confirm_authorization"
                )
                return self.wrap_text(CONFIRM_AUTHORIZATION.format(member=data.get('displayName'),
                                                                   company=current_state['member'].get(
                                                                       'defaultAccountData', {}).get('displayName')),
                                      x_is_menu=True, back_is_cancel=False, navigate_is="🏡 Menu")
            else:
                message = "Member not found!"

        if state.option == "confirm_authorization":
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
                url = f"{config('CREDEX')}/authorizeForCompany"

                payload = json.dumps({
                    "MemberIDtoBeAuthorized": current_state[
                        f"authorize_for_{current_state['member'].get('defaultAccountData', {}).get('displayName')}"].get(
                        'memberID'),
                    "MemberHandleToBeAuthorized": current_state[
                        f"authorize_for_{current_state['member'].get('defaultAccountData', {}).get('displayName')}"].get(
                        'handle'),
                    "companyID": current_state['member'].get('defaultAccountData', {}).get('memberID'),
                    "ownerID": current_state['member']['loginData']['humanMemberData'].get('memberID')
                })

                headers = {
                    'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
                    'Content-Type': 'application/json'
                }
                print(payload)
                response = requests.request("POST", url, headers=headers, data=payload)
                print(response.content)
                if response.status_code == 200:
                    data = response.json()
                    print(data)
                    if not data.get('Error'):
                        return self.wrap_text(AUTHORIZATION_SUCCESSFUL.format(member=current_state[
                            f"authorize_for_{current_state['member'].get('defaultAccountData', {}).get('displayName')}"].get(
                            'displayName'), company=current_state['member'].get('defaultAccountData', {}).get(
                            'displayName')), x_is_menu=True, back_is_cancel=False)
                    else:
                        return self.wrap_text()
            return self.wrap_text(AUTHORIZATION_FAILED)

        state.update_state(
            state=current_state,
            stage='handle_action_authorize_member',
            update_from="handle_action_authorize_member",
            option="get_handle"
        )
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self.user.mobile_number,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {
                    "text": ADD_MERMBER.format(
                        company=current_state['member'].get('defaultAccountData', {}).get('displayName'),
                        message=message)
                },
                "action":
                    {
                        "button": "🏡 Menu",
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

    # @property
    # def handle_action_balance_enquiry(self):
    # state = self.user.state
    # current_state = state.get_state(self.user)

    # if not isinstance(current_state, dict):
    #     current_state = current_state.state

    #     url = f"{config('CREDEX')}/getBalances"

    #     payload = json.dumps({
    #         "memberID": current_state['member']['defaultAccountData'].get('memberID'),
    #     })
    #     headers = {
    #         'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
    #         'Content-Type': 'application/json'
    #     }

    #     response = requests.request("GET", url, headers=headers, data=payload)
    #     print(response.content)
    #     if response.status_code == 200:
    #         response =  response.json()
    #         return self.wrap_text(
    #             BALANCE.format(
    #                 securedNetBalancesByDenom=response['securedNetBalancesByDenom'][0] if response['securedNetBalancesByDenom'] else "$0.00", 
    #                 totalPayables=response['unsecuredBalancesInDefaultDenom']['totalPayables'], 
    #                 totalReceivables=response['unsecuredBalancesInDefaultDenom']['totalReceivables'],
    #                 netPayRec=response['unsecuredBalancesInDefaultDenom']['netPayRec'],
    #                 netCredexAssetsInDefaultDenom=response['netCredexAssetsInDefaultDenom']
    #             ), x_is_menu=True
    #         )
    #     else:
    #         return self.wrap_text(BALANCE_FAILED)

