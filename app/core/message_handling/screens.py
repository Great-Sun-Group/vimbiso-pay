ACCOUNT_SELECTION = """
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
*{greeting}*
{message}
*_Which account would you like to_* 
*_view and manage?_*

{accounts}
 ⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""


HOME_1 = """
> *💳 {account}*
*Account Handle:* {handle}
{message}
{balance}

 ⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""


# HOME_1 = """
# > *💳 {account}*
# {balance}
# - *💸 Make Credex Offer* 
# - *📥 Pending Offers ({pending_in})*
# - *📤 Review Outgoing Offers ({pending_out})*
# - *📒 Review Transactions*

#  ⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
# """

HOME_2 = """
> *💳 {account}*
*Account Handle:* {handle}
{message}
{balance}

 ⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

# HOME_2 = """
# > *💳 {account}*
# accountHandle: {handle}

# {balance}
# - *💸 Make Credex Offer*
# - *📥 Pending Offers ({pending_in})*
# - *📤 Review Outgoing Offers ({pending_out})*
# - *📒 Review Transactions*
# - *👥 Add or remove members*
# - *🛎️ Update notification recipient* 
# - *🏡 Return to Member Dashboard*

#  ⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
# """

MANAGE_ACCOUNTS = """
> *💼 Manage Accounts*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
*👥 My Accounts*
 *1. 💼 Create Business*
 *2. 🗝️ Authorize Member*
 *3. 📤 Pending Outgoing ({pending_out})*

Type *'Menu'* to return to dashboard

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

INVALID_ACTION = """
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Invalid option selected. 

Your session may have expired. 
Send “hi” to log back in.

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

DELAY = """
Welcome to the credex ecosystem. 
Please hold a moment.
"""

BALANCE = """
*SECURED BALANCES*
{securedNetBalancesByDenom}
{unsecured_balance}
*NET ASSETS*
  {netCredexAssetsInDefaultDenom}
"""

UNSERCURED_BALANCES = """
*UNSECURED BALANCES*
  Payables : {totalPayables}
  Receivables : {totalReceivables}
  PayRec : {netPayRec}
"""

BALANCE_FAILED = """
> *😞 Enquiry Failed*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Failed to perform balance
enquiry at the moment.
  
Type *'Menu'* to return to dashboard

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

CREDEX = """
> *💰 Credex*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

*Summary*

 Outstanding : {formattedOutstandingAmount}
 Party : {counterpartyDisplayname}
 Amount : {formattedInitialAmount}
 Date : {date}
 Type : {type}

Type *'Menu'* to return to dashboard

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

REGISTER = """
> *👤  Registration*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

I'm VimbisoPay. I'm a WhatsApp 
chatbot. It's my job to connect 
you to the credex ecosystem. 

I'll show you around, and you 
can message me to interact with 
your credex accounts.

Would you like to become a 
member of the credex ecosystem?
{message}
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

MORE_ABOUT_CREDEX = """
> *About Us*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Credex is an accounting app that is helping Zimbabweans overcome the challenges of small change and payments. 

VimbisoPay is a Zimbabwe company that facilitates and secures transactions in the credex ecosystem.

A credex is a promise to provide value, and the credex ecosystem finds loops of value exchange. 

If I owe you and you owe me, we can cancel our debts to each other without money changing hands. 

If I owe you, and you owe Alice, and Alice owes Bob, and Bob owes me, we could cancel those debts in the same manner.

*It's free to:*
- Open a credex account.
- Receive a secured credex from VimbisoPay or any other counterparty.
- Issue a secured or unsecured credex.
- Accept a credex.

*Fees:*
A fee of 2% will be charged when cashing out a secured credex with VimbisoPay for USD or ZIG. Third parties may add additional charges. So only cash out if your counterparty won’t accept a credex.

Your account and transactions are managed easily within WhatsApp.

1. Join the credex ecosystem
2. Find out more about credex

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

REGISTER_FORM = """
> *👤  Registration*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

That's great, I'll sign you right up. 
I just need to know your name.

{message}
"""

COMPANY_REGISTRATION = """
> *💼  Create New Account*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

To create a new account, tap *Create* 
*Account* below and submit the linked 
form.

{message}
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

OFFER_CREDEX = """
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

 To issue a secured credex, enter the 
 details of the transfer into this form.
 
 {message}
"""

# OFFER_CREDEX = """
# ⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

# To make a payment offer click the
# *'Send'* button below and fill
# in the form then submit the details.

# Alternatively you can use the short
# commands below:

# *To issue a secured credex, send*
#   0.5=>recipientHandle

# *To issue an unecured credex, send*
#   0.5->recipientHandle

# {message}
# """

ACCOUNT_REGISTRATION_COMPLETE = """
> *🎉 Account Created!*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Ok, {first_name}, we've got your
new account registered
"""
REGISTRATION_COMPLETE = """
> *🎉 Account Created!*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Ok, {firstName}, we've got you 
registered. The free tier of the 
credex ecosystem gives you one 
credex account, which has been 
automatically created for you. 

This is your personal account. 
You can use it for anything you 
like, including business purposes 
for now, but later on you will 
be able to open dedicated accounts 
for different businesses.

Your credex member handle and the 
account handle of your personal 
credex account have both been 
set to your phone number.

These handles identify you as a 
member, and identify accounts for 
others to send payments to. 

When you make a payment, you'll 
need to enter an account handle 
so the credex goes to the right 
place.

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

CONFIRM_SECURED_CREDEX = """
> *💰 Account to Send From*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Offer ${amount} {currency} {secured} credex
to *{party}*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

CONFIRM_OFFER_CREDEX = """
> *💰 Offer Confirmation*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Offer ${amount} {currency} {secured} credex to 
*{party}* from 
account *{source}*

1. ✅ Yes
2. ❌ No

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

CONFIRM_UNSECURED_CREDEX = """
> *💰 Account to Send From*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Offer ${amount} {currency} {secured} credex to 
*{party}* from 
account *{source}*

{date}
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

ACCEPT_CREDEX = """
> *💰 Accept Offer*

*Accept ${amount} offer*

  {type} credex from
- {party} 
"""

OUTGOING_CREDEX = """
> *💰 Cancel Offer*

*Cancel {amount} offer*

  {type} credex to
- {party} 
"""

OFFER_SUCCESSFUL = """
> *💰 Complete!*

*Transaction Complete!!*

You have successfully offered 
${amount} {currency} {secured} to 
{recipient}.

From: {source}
"""

OFFER_FAILED = """
> *😞 Failed*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
 {message}‼️

*To issue a secured credex, send*
  0.5=>recipientHandle

*To issue an unecured credex, send*
  0.5->recipientHandle

Type *'Menu'* to return to dashboard

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

ADD_MERMBER = """
> *🗝️ Authorize Member*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Send member *handle* of the member 
you wish to allow to authorize 
transactions for *{company}*
{message}
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

CONFIRM_AUTHORIZATION = """
> *🗝️ Confirm Authorization*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Do you wish to allow member
*{member}* to perform transactions 
for *{company} ?*

*1. ✅ Authorize*
*2. ❌ Cancel*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

AUTHORIZATION_SUCCESSFUL = """
> *✅ Success*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Member authorization complete!
*{member}* can now transact on 
behalf of *{company}*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

DEAUTHORIZATION_SUCCESSFUL = """
> *✅ Success*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Access has been revoked!
*{member}* can no longer 
transact on behalf of *{company}*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

AUTHORIZATION_FAILED = """
> *❌ Failed*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
Member authorization failed!

{message}
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

AGENTS = """
> *👤 VimbisoPay*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

*Cash in:* cash can be used to 
purchase a secured credex from 
VimbisoPay at no cost.

Secured credex can also be 
purchased from anyone who has a 
secured balance, at the market 
rate agreed between you.

*Cash out:* if you have a secured 
balance, you can cash out with 
VimbisoPay for a 2% fee. 

You can also sell secured credex 
to other members for cash, at the 
market rate agreed between you.

Cash in/out with VimbisoPay in 
Mbare.


⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

MEMBERS = """
> *👥 Members*

*Add or remove members*

You can authorize others to transact 
on behalf of this account (max 5).

1. Add new member
{members}
"""

NOTIFICATIONS = """
> *🛎️ Notifications*

*Update notification recipient*

*{name}* currently receives 
notifications of incoming offers. 

Change to:
{members}
"""

NOTIFICATION = """
> *🛎️ Notifications*

Notifications of incoming offers now
being sent to :
- *{name}* 
"""

PROFILE_SELECTION = """
> *👤 Profile*
{message}
"""