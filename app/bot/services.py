import requests
import json
import locale
import requests
from decouple import config
from django.core.files import File
from io import BytesIO
from bot.serializers.offers import OfferCredexSerializer
from bot.serializers.members import MemberDetailsSerializer
from bot.screens import *
from bot.constants import *

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')


class CredexBotService:
    def __init__(self, payload, methods: dict = {}, user: object = None) -> None:
        self.message = payload
        self.user = user
        self.body = self.message['message']

        # Registering Methods Needed To Handle This Particular Stage 
        """ 
            I dynamically add methods to the class 
            to  avoid cluttering the class and file 
            with methods that might not be required 
            at this stage

            E.g At home screen there is no need for
                check balane handler
        """

        # Load 
        state = self.user.state
        print("####### ", self.user.state)
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
            self.refresh()

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
                return self.wrap_text(INVALID_ACTION, x_is_menu=True, navigate_is="Menu")
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

        url = f"{config('CREDEX')}/getMemberByPhone"

        payload = json.dumps({
            "phone": self.message['from']
        })
        headers = {
            'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
            'Content-Type': 'application/json'
        }

        response = requests.request("GET", url, headers=headers, data=payload)
        if response.status_code == 200:
            current_state['member'] = response.json()
            state.update_state(
                state=current_state,
                stage='handle_action_menu',
                update_from="handle_action_menu",
                option="handle_action_menu"
            )

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
            serializer = MemberDetailsSerializer(data=payload)
            if serializer.is_valid():
                url = f"{config('CREDEX')}/createMember"
                headers = {
                    'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
                    'Content-Type': 'application/json'
                }
                response = requests.request("POST", url, headers=headers, json=serializer.validated_data)
                if response.status_code == 200:
                    print(response.content)
                    return self.wrap_text(
                        REGISTRATION_COMPLETE.format(
                            full_name=f"{self.body.get('firstName')} {self.body.get('lastName')}",
                            username=self.body.get('email'),
                            phone=self.message['from']
                        ),
                        x_is_menu=True
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
                            "flow_id": "2132950867068712",
                            "flow_cta": "Rgister",
                            "flow_action_payload": {
                                "screen": "REGISTRATION"
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

        payload = json.dumps({
            "phone": self.message['from']
        })
        headers = {
            'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
            'Content-Type': 'application/json'
        }

        response = requests.request("GET", f"{config('CREDEX')}/getMemberByPhone", headers=headers, data=payload)
        if response.status_code == 200:
            current_state['member'] = response.json()
            state.update_state(
                state=current_state,
                stage='handle_action_menu',
                update_from="handle_action_menu",
                option="handle_action_menu"
            )
        else:
            state.update_state(
                state=current_state,
                stage='handle_action_register',
                update_from="handle_action_menu",
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
                            "flow_id": "2132950867068712",
                            "flow_cta": "Rgister",
                            "flow_action_payload": {
                                "screen": "REGISTRATION"
                            }
                        }
                    }
                }
            }

            # print(response.text)
        pending_in = 0
        pending_out = 0
        if current_state['member']['pendingInData']:
            pending_in = len(current_state['member']['pendingInData'])

        if current_state['member']['pendingOutData']:
            pending_out = len(current_state['member']['pendingOutData'])
        secured = ""
        for item in current_state['member']['balanceData']['securedNetBalancesByDenom']:
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
                        greeting=get_greeting(current_state['member']['memberData'].get('firstname')),
                        balance=BALANCE.format(
                            securedNetBalancesByDenom=
                            current_state['member']['balanceData']['securedNetBalancesByDenom'][0] if
                            current_state['member']['balanceData']['securedNetBalancesByDenom'] else "$0.00",
                            totalPayables=current_state['member']['balanceData']['unsecuredBalancesInDefaultDenom'][
                                'totalPayables'],
                            totalReceivables=current_state['member']['balanceData']['unsecuredBalancesInDefaultDenom'][
                                'totalReceivables'],
                            netPayRec=current_state['member']['balanceData']['unsecuredBalancesInDefaultDenom'][
                                'netPayRec'],
                            netCredexAssetsInDefaultDenom=current_state['member']['balanceData'][
                                'netCredexAssetsInDefaultDenom']
                        ),
                        pending_in=pending_in,
                        pending_out=pending_out
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
                                            "title": f"📥 Pending Incoming"
                                        },
                                        {
                                            "id": "handle_action_pending_offers_out",
                                            "title": f"📤 Pending Outgoing"
                                        },
                                        {
                                            "id": "handle_action_offer_credex",
                                            "title": f"💸 Offer Credex",
                                        },
                                        {
                                            "id": "handle_action_transactions",
                                            "title": f"📒 Review Ledger",
                                        }
                                    ]
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
                "memberID": current_state['member']['memberData'].get('memberID'),
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
                                    counterpartyDisplayname=credex['credexData'].get('counterpartyDisplayname').title(),
                                    date=credex['credexData'].get('dateTime'),
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
                                                    "title": "Menu"
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
                    "title": "Menu"
                }
            ]
            return self.wrap_text(message=menu_string, extra_rows=rows)

        url = f"{config('CREDEX')}/getLedger"

        payload = json.dumps({
            "memberID": current_state['member']['memberData'].get('memberID'),
            "numRows": 8,
            "startRow": (page_number * 7) - 7
        })
        headers = {
            'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
            'Content-Type': 'application/json'
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
                    "title": "Menu"
                }
            ]
            return self.wrap_text(message=menu_string, extra_rows=rows)
        else:
            menu_string = "*Empty*\n\n🪹 No transactions found!\n\n"
            rows = [
                {
                    "id": "X",
                    "title": "Menu"
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
            "memberID": current_state['member']['memberData'].get('memberID')
        })
        headers = {
            'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
            'Content-Type': 'application/json'
        }

        response = requests.request("PUT", f"{config('CREDEX')}/acceptCredex", headers=headers, data=payload)
        if response.status_code == 200:
            self.refresh()
            if not response.json().get('Error'):
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
            "memberID": current_state['member']['memberData'].get('memberID')
        })
        headers = {
            'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
            'Content-Type': 'application/json'
        }
        response = requests.request("PUT", f"{config('CREDEX')}/declineCredex", headers=headers, data=payload)
        if response.status_code == 200:
            self.refresh()
            if not response.json().get('Error'):
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
            "memberID": current_state['member']['memberData'].get('memberID')
        })
        headers = {
            'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
            'Content-Type': 'application/json'
        }
        response = requests.request("PUT", f"{config('CREDEX')}/cancelCredex", headers=headers, data=payload)
        if response.status_code == 200:
            self.refresh()
            if not response.json().get('Error'):
                return self.wrap_text("> *🥳 Success*\n\n Offer successfully cancelled!", x_is_menu=True,
                                      back_is_cancel=False)
        return self.wrap_text("> *😞 Failed*\n\n Failed to cancel offer!", x_is_menu=True, back_is_cancel=False)

    @property
    def handle_action_accept_all_incoming_offers(self):
        """THIS METHOD HANDLES ACCEPTING ALL INCOMING OFFERS"""
        state = self.user.state
        current_state = state.get_state(self.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state
        return self.wrap_text("Accepted All Incoming Offers", x_is_menu=True, back_is_cancel=False)

    @property
    def handle_action_pending_offers_in(self):
        """THIS METHOD HANDLES DISPLAYING INCOMING OFFERS"""
        state = self.user.state
        current_state = state.get_state(self.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        if state.option == "handle_action_display_offers":
            data = current_state.get('pending') if current_state.get('pending') else []
            if self.body in [str(i) for i in range(1, len(data) + 1)] or self.message['type'] == 'interactive':
                if data:
                    item = None
                    if self.body.isdigit():
                        item = data[int(self.body) - 1]
                    else:
                        for row in data:
                            if row.get('id') == self.body:
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
                                "text": ACCEPT_CREDEX.format(amount=item.get('title'), party=item.get('description'))
                            },
                            "action": {
                                "buttons": [
                                    {
                                        "type": "reply",
                                        "reply": {
                                            "id": f"decline_{item.get('id')}",
                                            "title": "❌ Decline"
                                        }
                                    },
                                    {
                                        "type": "reply",
                                        "reply": {
                                            "id": f"accept_{item.get('id')}",
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
            data = current_state['member'].get('pendingInData') if current_state['member'].get('pendingInData') else []
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
            current_state['pending'] = rows
            state.update_state(
                state=current_state,
                stage='handle_action_pending_offers_in',
                update_from="handle_action_pending_offers_in",
                option="handle_action_display_offers"
            )
            if not rows:
                print("No rows")
                menu_string = "*Empty*\n\n🪹 No pending offers to display!\n\n"
                rows = [
                    {
                        "id": "X",
                        "title": "Menu"
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

    @property
    def handle_action_pending_offers_out(self):
        """THIS METHOD HANDLES DISPLAYING OUTGOING OFFERS"""
        state = self.user.state
        current_state = state.get_state(self.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        if state.option == "handle_action_display_offers":
            data = current_state.get('pending') if current_state.get('pending') else []
            if self.body in [str(i) for i in range(1, len(data) + 1)] or self.message['type'] == 'interactive':
                if data:
                    item = None
                    if self.body.isdigit():
                        item = data[int(self.body) - 1]
                    else:
                        for row in data:
                            if row.get('id') == self.body:
                                item = row
                                break

                    return {
                        "messaging_product": "whatsapp",
                        "recipient_type": "individual",
                        "to": self.user.mobile_number,
                        "type": "interactive",
                        "interactive": {
                            "type": "list",
                            "body": {
                                "text": item['title']
                            },
                            "action":
                                {
                                    "button": "🕹️ Choose",
                                    "sections": [
                                        {
                                            "title": "Options",
                                            "rows": [
                                                {
                                                    "id": "Cancel",
                                                    "title": "📥 Cancel",
                                                }
                                            ]
                                        }
                                    ]
                                }
                        }
                    } if item else self.wrap_text("404")

        if self.body == 'handle_action_pending_offers_out':
            rows = []
            menu_string = "> *📤 Pending Outgoing*\n\n*Offers*\n"
            count = 1
            data = current_state['member'].get('pendingOutData') if current_state['member'].get(
                'pendingOutData') else []
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

            current_state['pending'] = rows
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
                        "title": "Menu"
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

        if not isinstance(current_state, dict):
            current_state = current_state.state

        payload = {}
        if "=>" in f"{self.body}" or "->" f"{self.body}" or self.message['type'] == "nfm_reply":
            if self.message['type'] == "nfm_reply":
                payload = {
                    "issuer_member_id": current_state['member']['memberData'].get('memberID'),
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
                        "issuer_member_id": current_state['member']['memberData'].get('memberID'),
                        "handle": user,
                        "amount": amount,
                        "dueDate": (datetime.now() + timedelta(weeks=4)).timestamp() * 1000,
                        "currency": current_state['member']['memberData'].get('defaultDenom'),
                        "securedCredex": True
                    }

            if "->" in f"{self.body}" and '=' in f"{self.body}":
                amount, user_date = f"{self.body}".split('->')
                user, date = user_date.split('=')

                try:
                    from datetime import datetime
                    # Try to parse the date string with the specified format
                    datetime.strptime(date, '%Y-%m-%d')

                except ValueError:
                    # If a ValueError is raised, the date string is not in the correct format
                    return self.wrap_text(OFFER_CREDEX.format(message='*Invalid Due Date❗*'), x_is_menu=True)

                payload = {
                    "issuer_member_id": current_state['member']['memberData'].get('memberID'),
                    "handle": user,
                    "amount": amount,
                    "dueDate": datetime.strptime(date, '%Y-%m-%d').timestamp() * 1000,
                    "currency": current_state['member']['memberData'].get('defaultDenom'),
                    "securedCredex": False
                }

            serializer = OfferCredexSerializer(data=payload)

            if serializer.is_valid():
                response = CONFIRM_SECURED_CREDEX.format(
                    party=serializer.validated_data.get('full_name'),
                    amount=serializer.validated_data.get('InitialAmount'),
                    currency=serializer.validated_data.get('Denomination'),
                    handle=serializer.validated_data.pop('handle'),
                    secured='*secured*'
                ) if serializer.validated_data.get('securedCredex') else CONFIRM_UNSECURED_CREDEX.format(
                    party=serializer.validated_data.get('full_name'),
                    amount=serializer.validated_data.get('InitialAmount'),
                    currency=serializer.validated_data.get('Denomination'),
                    handle=serializer.validated_data.pop('handle'),
                    secured='*unsecured*',
                    date=f"*Due Date :* {serializer.validated_data.get('dueDate')}"
                )
                current_state['confirm_offer_payload'] = serializer.validated_data
                current_state['confirm_offer_payload']['secured'] = serializer.validated_data['securedCredex']
                state.update_state(
                    state=current_state,
                    stage='handle_action_offer_credex',
                    update_from="handle_action_offer_credex",
                    option="handle_action_confirm_offer_credex"
                )
                return self.wrap_text(response, use_buttons=True, yes_or_no=True)

        cancelled = False

        if self.body in ['Y', 'y', 'yes', 'YES', 'Yes', 'n', 'NO', 'no', 'No', 'N', '1', '2', 'CANCEL', 'Cancel',
                         'cancel', 'CONFIRM', 'Confirm', 'confirm'] and current_state.get('confirm_offer_payload'):
            if self.body in ['n', 'NO', 'no', 'No', 'N', '2', 'CANCEL', 'Cancel', 'cancel']:
                current_state.pop('confirm_offer_payload')
                cancelled = True
            else:
                url = f"{config('CREDEX')}/offerCredex"
                if current_state['confirm_offer_payload'].get('securedCredex'):
                    secured = current_state['confirm_offer_payload'].pop('securedCredex')
                to_credex = current_state.get('confirm_offer_payload')
                to_credex.pop("handle", None)
                payload = json.dumps(current_state.get('confirm_offer_payload'))
                headers = {
                    'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
                    'Content-Type': 'application/json'
                }
                response = requests.request("POST", url, headers=headers, data=payload)
                if response.status_code == 200:
                    response = response.json()
                    if response.get('credex'):
                        confirm_offer_payload = current_state.pop('confirm_offer_payload', {})
                        self.refresh()
                        return self.wrap_text(OFFER_SUCCESSFUL.format(
                            type=response['credex']['credexType'],
                            amount=round(response['credex']['InitialAmount'] / response['credex']['CXXmultiplier'], 2),
                            currency=response['credex']['Denomination'],
                            recipient=confirm_offer_payload.pop('full_name'),
                            secured='yes' if to_credex['secured'] else 'no'
                        ), x_is_menu=True, navigate_is="Menu", back_is_cancel=False)
                confirm_offer_payload = current_state.pop('confirm_offer_payload', {})
                return self.wrap_text(OFFER_FAILED, x_is_menu=True)

        state.update_state(
            state=current_state,
            stage='handle_action_offer_credex',
            update_from="handle_action_offer_credex",
            option="handle_action_offer_credex"
        )

        return self.wrap_text(OFFER_CREDEX.format(message='*Offer Cancelled By User❗*' if cancelled else ''))

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

        if include_back:
            rows.append({
                "id": "back" if not back_is_cancel else 'X',
                "title": "🔙 Back"
            })

        if proceed_option == True:
            rows.append({
                "id": "Y",
                "title": "✅ Continue"
            })
        rows.append({
                        "id": "X",
                        "title": "❌ Cancel"
                    } if not x_is_menu else {
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

        # @property

    # def handle_action_balance_enquiry(self):
    #     state = self.user.state
    #     current_state = state.get_state(self.user)

    #     if not isinstance(current_state, dict):
    #         current_state = current_state.state

    #     url = f"{config('CREDEX')}/getBalances"

    #     payload = json.dumps({
    #         "memberID": current_state['member']['memberData'].get('memberID'),
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