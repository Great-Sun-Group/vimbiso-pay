from core.message_handling.whatsapp_forms import registration_form, offer_credex
from .screens import (
    UNSERCURED_BALANCES,
    ACCOUNT_SELECTION,
    BALANCE,
    AGENTS,
    HOME_1,
    HOME_2,
    OFFER_CREDEX,
    OFFER_FAILED
)
from ..utils.utils import wrap_text, get_greeting
from ..config.constants import *
from serializers.members import MemberDetailsSerializer
from serializers.offers import OfferCredexSerializer


class ActionHandler:

    def __init__(self, service: 'CredexBotService'):
        self.service = service

    def handle_action_register(self, register=False):
        if register:
            return registration_form(
                self.service.user.mobile_number,
                "*Welcome To Credex!*\n\nIt looks like you're new here. Let's get you \nset up."
            )

        if self.service.message['type'] == "nfm_reply":
            payload = {
                "first_name": self.service.body.get('firstName'),
                "last_name": self.service.body.get('lastName'),
                "phone_number": self.service.message['from']
            }
            serializer = MemberDetailsSerializer(data=payload)
            if serializer.is_valid():
                successful, message = self.service.api_interactions.register_member(serializer.validated_data)
                if successful:
                    self.service.state.update_state(
                        self.service.current_state,
                        stage="handle_action_select_profile",
                        update_from="handle_action_register",
                        option="handle_action_select_profile"
                    )
                    return self.handle_action_select_profile(message=f"\n{message}\n\n")
                else:
                    return wrap_text(message, self.service.user.mobile_number)
            else:
                # Handle invalid serializer
                pass

        print("Rest of the implementation")
        # Rest of the implementation

    def handle_action_menu(self):
        """Implementation for handling menu actions"""

        print("Handling Menu Action")

        # Refresh the user state
        response = self.service.refresh(reset=True)
        if response:
            self.service.state_manager.update_state(
                new_state=self.service.current_state,
                update_from="handle_action_menu",
                stage='handle_action_register',
                option="handle_action_register"
            )
            return response

        # Get the current user state
        user = CachedUser(self.service.user.mobile_number)
        current_state = user.state.get_state(user)

        # Get the member tier & currently selected account to render the menu
        member_tier = current_state.get('member', {}).get('memberDashboard', {}).get('memberTier', 1)
        selected_account = current_state.get('default_profile')
        print("Member Tier & Selected Account : ", member_tier, selected_account)

        if member_tier >= 2 and not selected_account:
            return self.handle_action_select_profile()

        pending = ''
        pending_in = 0
        if selected_account['pendingInData']:
            pending_in = len(selected_account['pendingInData'])
            pending = f"    Pending Offers ({pending_in})"

        pending_out = 0
        if selected_account['pendingOutData']:
            pending_out = len(selected_account['pendingOutData'])

        secured = ""
        for item in selected_account['balanceData']['securedNetBalancesByDenom']:
            secured += f" *{item}* \n"

        balances = ""
        balance_lists = selected_account['balanceData']['securedNetBalancesByDenom']
        for bal in balance_lists:
            balances += f"- {bal}\n"

        is_owned_account = current_state['member'].get('default_profile', {}).get('isOwnedAccount')
        member_tier = current_state['member']['memberDashboard'].get('memberTier')

        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self.service.user.mobile_number,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {
                    "text": (HOME_2 if is_owned_account else HOME_1).format(
                        account=current_state['member'].get('default_profile', {}).get('accountName',
                                                                                       "Personal Account"),
                        balance=BALANCE.format(
                            securedNetBalancesByDenom=balances if balances else "    $0.00\n",
                            unsecured_balance=UNSERCURED_BALANCES.format(
                                totalPayables=selected_account['balanceData'][
                                    'unsecuredBalancesInDefaultDenom']['totalPayables'],
                                totalReceivables=selected_account['balanceData'][
                                    'unsecuredBalancesInDefaultDenom']['totalReceivables'],
                                netPayRec=selected_account['balanceData'][
                                    'unsecuredBalancesInDefaultDenom']['netPayRec'],
                            ) if member_tier > 2 else f"Free tier remaining daily spend limit\n    *{current_state['member']['memberDashboard'].get('remainingAvailableUSD', 0)} USD*\n{pending}",
                            netCredexAssetsInDefaultDenom=selected_account['balanceData'][
                                'netCredexAssetsInDefaultDenom']
                        ),
                        handle=selected_account['accountHandle'],
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
                                    ] if not is_owned_account else [
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

    def handle_action_offer_credex(self):
        """
            Handling credex offers
        :return: 
        """

        # Get current user state
        user = CachedUser(self.service.user.mobile_number)
        current_state = user.state.get_state(self.service.user)

        # Get the selected profile
        selected_profile = current_state.get('default_profile', {})

        # Get the member dashboard
        member_dashboard = current_state.get('member', {}).get('memberDashboard', {})

        message = ''

        if not current_state.get('member'):
            # Refresh the user state
            response = self.service.refresh(reset=True)
            if response:
                self.service.state_manager.update_state(
                    new_state=self.service.current_state,
                    update_from="handle_action_offer_credex",
                    stage='handle_action_register',
                    option="handle_action_register"
                )
                return response

        if not current_state.get('default_profile', {}):
            for account in current_state['member']['accountDashboards']:
                if member_dashboard['accountIDS'][-1] == account.get('accountID'):
                    selected_profile = account
                    break

        payload = {}
        if "=>" in f"{self.service.body}" or "->" f"{self.service.body}" or self.service.message['type'] == "nfm_reply":
            if self.service.message['type'] == "nfm_reply":
                from datetime import datetime, timedelta
                payload = {
                    "authorizer_member_id": member_dashboard.get('memberID'),
                    "issuer_member_id": selected_profile.get(
                        'accountID'
                    ) if selected_profile else member_dashboard['accountIDS'][-1],
                    "handle": self.service.body.get('handle'),
                    "amount": self.service.body.get('amount'),
                    "dueDate": self.service.body.get(
                        'due_date'
                    ) if self.service.body.get('due_date') else (
                                                                        datetime.now() + timedelta(
                                                                    weeks=4)).timestamp() * 1000,
                    "currency": self.service.body.get('currency'),
                    "securedCredex": True
                }

            if "=>" in f"{self.service.body}" or "->" f"{self.service.body}":
                if "=>" in f"{self.service.body}":
                    amount, user = f"{self.service.body}".split('=>')
                    if "=" in user:
                        user, _ = user.split("=")
                    from datetime import datetime
                    payload = {
                        "authorizer_member_id": member_dashboard.get('memberID'),
                        "issuer_member_id": selected_profile.get(
                            'accountID'
                        ) if selected_profile else member_dashboard['accountIDS'][-1],
                        "handle": user,
                        "amount": amount,
                        "dueDate": (datetime.now()).timestamp() * 1000,
                        "currency": selected_profile['defaultDenom'] if selected_profile else current_state['member'][
                            'memberDashboard'].get('defaultDenom'),
                        "securedCredex": True
                    }

            if "->" in f"{self.service.body}":
                if '=' in f"{self.service.body}":
                    amount, user_date = f"{self.service.body}".split('->')
                    user, date = user_date.split('=')

                    try:
                        from datetime import datetime
                        # Try to parse the date string with the specified format
                        datetime.strptime(date, '%Y-%m-%d')

                    except ValueError:
                        # If a ValueError is raised, the date string is not in the correct format
                        return self.wrap_text(OFFER_CREDEX.format(message='*Invalid Due Date❗*'), x_is_menu=True)
                else:
                    amount, user = f"{self.service.body}".split('->')
                    date = None

                from datetime import datetime, timedelta
                payload = {
                    "authorizer_member_id": member_dashboard.get('memberID'),
                    "issuer_member_id": selected_profile.get(
                        'accountID') if selected_profile else
                    member_dashboard['accountIDS'][-1],
                    "handle": user,
                    "amount": amount,
                    "dueDate": datetime.strptime(date, '%Y-%m-%d').timestamp() * 1000 if date else (
                                                                                                           datetime.now() + timedelta(
                                                                                                       weeks=4)).timestamp() * 1000,
                    "currency": selected_profile['defaultDenom'] if selected_profile else
                    member_dashboard.get(
                        'defaultDenom'),
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
                    source=selected_profile.get('accountName'),
                    handle=serializer.validated_data.pop('handle'),
                    secured='*secured*',
                    accounts=account_string

                ) if serializer.validated_data.get('securedCredex') else CONFIRM_UNSECURED_CREDEX.format(
                    party=serializer.validated_data.get('full_name'),
                    amount=serializer.validated_data.get('InitialAmount'),
                    currency=serializer.validated_data.get('Denomination'),
                    source=selected_profile.get('accountName'),
                    handle=serializer.validated_data.pop('handle'),
                    secured='*unsecured*',
                    date=f"*Due Date :* {serializer.validated_data.get('dueDate')}",
                    accounts=account_string
                )
                current_state['confirm_offer_payload'] = serializer.validated_data
                current_state['confirm_offer_payload']['secured'] = serializer.validated_data['securedCredex']
                self.service.state_manager.update_state(
                    new_state=current_state,
                    stage='handle_action_offer_credex',
                    update_from="handle_action_offer_credex",
                    option="handle_action_confirm_offer_credex"
                )
                return {
                    "messaging_product": "whatsapp",
                    "to": self.service.user.mobile_number,
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

        if user.state.option == "handle_action_confirm_offer_credex":
            to_credex = current_state.get('confirm_offer_payload')
            to_credex['issuerAccountID'] = selected_profile.get('accountID')
            if self.service.message['type'] == "nfm_reply":
                print(self.service.message)
                to_credex['issuerAccountID'] = self.service.message['message']['source_account']

            to_credex['memberID'] = member_dashboard.get('memberID')
            to_credex.pop("handle", None)
            if to_credex.get('securedCredex'):
                to_credex.pop('dueDate', None)
            to_credex.pop('secured', None)

            success, response = self.service.api_interactions.offer_credex()
            if success:
                if response.get("offerCredexData", {}).get("credex"):
                    
                    response = response.get("offerCredexData", {})
                    current_state.pop('confirm_offer_payload', {})
                    denomination = selected_profile['defaultDenom']
                    current_state.pop('default_profile', {})

                    CredexWhatsappService(
                        payload=wrap_text(
                            OFFER_SUCCESSFUL.format(
                                type='Secured Credex' if response['credex']['secured'] else 'Unsecured Credex',
                                amount=response['credex']['formattedInitialAmount'],
                                currency=denomination,
                                recipient=response['credex']['counterpartyAccountName'],
                                source=selected_profile.get('accountName'),
                                secured='*Secured* credex' if response['credex']['secured'] else '*Unsecured* credex',
                            ), self.service.user.mobile_number
                        )
                    ).notify()

                    default = selected_profile.get('accountID')
                    current_state.pop('default_profile', {})

                    count = 0
                    for account in current_state['member']['accountDashboards']:
                        count += 1
                        if default == account.get('accountID'):
                            selected_profile = account
                            break

                    self.service.state_manager.update_state(
                        new_state=current_state,
                        stage='handle_action_menu',
                        update_from="handle_action_menu",
                        option="handle_action_menu"
                    )

                    # Todo: Refresh state at this point
                    self.service.body = selected_profile.get('accountHandle')
                    return self.handle_action_select_profile
                else:
                    current_state.pop('confirm_offer_payload', {})
                    message = self.format_synopsis(
                        response.get(
                            "offerCredexData", {}
                        ).get('message').replace("Error:", ""))
            else:
                try:
                    current_state.pop('confirm_offer_payload', {})
                    message = self.format_synopsis(
                        response.get(
                            "offerCredexData", {}
                        ).get('message').replace("Error:", "")
                    )
                    return wrap_text(
                        user_mobile_number=self.service.user.mobile_number,
                        message=OFFER_FAILED.format(message=message),
                        x_is_menu=True
                    )
                except Exception as e:
                    print("ERROR : ", e)
                message = 'Invalid option selected'

        self.service.state_manager.update_state(
            new_state=current_state,
            stage='handle_action_offer_credex',
            update_from="handle_action_offer_credex",
            option="handle_action_offer_credex"
        )
        return offer_credex(self.service.user.mobile_number, message=self.format_synopsis(message))

    def handle_default_action(self):
        # Implementation for handling default or unknown actions
        return wrap_text(INVALID_ACTION, self.service.user.mobile_number)

    @staticmethod
    def format_synopsis(synopsis, style=None):
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

# Add other action handling methods as needed
