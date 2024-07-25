ACCOUNT_SELECTION = """
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
*{greeting}*

*_Which account would you like to_* 
*_view and manage?_*

{accounts}
 ⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""



HOME_1 = """
> *👤 {account}*
{balance}
*_{handle}_*
 *1. 📥 Pending Offers ({pending_in})*
 *2. 📒 Review Ledger*
 *3. 📤 Review Outgoing Offers ({pending_in})*
 *4. 💸 Offer Credex*
 *5. 👥 Return to Member Dashboard*

 *What would you like to do ?*
 ⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

HOME_2 = """
> *👤 {account}*
{balance}
*_{handle}_*
 *1. 📥 Pending Offers ({pending_in})*
 *2. 📒 Review Ledger*
 *3. 👥 Add or remove members*
 *4. 🛎️ Update notification recipient* 
 *5. 📤 Review Outgoing Offers ({pending_out})*
 *6. 💸 Offer Credex*
 *7. 🏡 Return to Member Dashboard*

 *What would you like to do ?*
 ⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

MANAGE_ACCOUNTS = """
> *💼 Manage Accounts*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
*👥 My Accounts*
 *1. 💼 Create Business*
 *2. 🗝️ Authorize Member*
 *3. 📤 Pending Outgoing ({pending_out})*

Send *'Menu'* to go back to Menu

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

INVALID_ACTION = """
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

*Invalid option selected*
"""

DELAY = """
Welcome to credex. 

Please hold a moment while 
we fetch your account data.
"""

BALANCE = """
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

*SECURED BALANCES*
{securedNetBalancesByDenom}
*UNSECURED BALANCES*
  Payables : {totalPayables}
  Receivables : {totalReceivables}
  PayRec : {netPayRec}

*NET ASSETS*
  {netCredexAssetsInDefaultDenom}
"""

BALANCE_FAILED = """
> *😞 Enquiry Failed*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Failed to perform balance
enquiry at the moment.
  
Send *'Menu'* to go back to Menu

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

Send *'Menu'* to go back to Menu

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

REGISTER = """
> *👤  Registration*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

To create a new account, tap *Create* 
*Account* below and submit the linked 
form.

Send *'Menu'* to go back to Menu

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
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
> *💰 Offer Credex*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

You can offer payment through the 
chatbot interface. All you need 
to know is the account handle of 
your counterparty, and the amount 
to offer.

When you purchase a secured credex 
from VimbisoPay for $1 USD in cash, 
the VimbisoPay agent enters in the 
chatbot:

1=>youraccounthandle

You will be prompted to approve 
the offer, and when you do it 
will be entered into your ledger 
as a secured credex balance. 
When you want to send $0.50 to 
a vendor, enter:

0.5=>vendorhandle

And if the vendor wants to 
purchase the $1 cash back from 
VimbisoPay, they would enter:

1.02=>vimbisopay

Yes, there is a 2% charge on cash 
out for secured credex. But there’s 
no charge for cash in, or for 
transactions within the ecosystem. 

So only cash out if your 
counterparty won’t accept credex.

{message}
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

REGISTRATION_COMPLETE = """
> *🎉 Registered!*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Hello {full_name}

Welcome to Credex! We are 
excited to have you on board.

Send *'Menu'* and start 
exploring all the features 
we offer.

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

CONFIRM_SECURED_CREDEX = """
> *💰 Confirm*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Offer {secured} credex:
  ${amount} {currency} to {party}

Make offer from:
{accounts}
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

CONFIRM_UNSECURED_CREDEX = """
> *💰 Confirm*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Offer {secured} credex:
  ${amount} {currency} to {party}
  due {date}

Make offer from:
{accounts}
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

ACCEPT_CREDEX = """
> *💰 Accept Offer*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

*Accept {amount} offer*

  {type} credex from
- {party} 
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

OUTGOING_CREDEX = """
> *💰 Cancel Offer*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

*Cancel {amount} offer*

  {type} credex to
- {party} 
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

OFFER_SUCCESSFUL = """
> *✅ Success!*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

*Offered*

{amount} {currency} {secured} to
{recipient}

Send *'Menu'* to go back to Menu
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

OFFER_FAILED = """
> *😞 Failed*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Failed to perform transaction
at the moment.

{message}
Send *'Menu'* to go back to Menu

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

ADD_MERMBER = """
> *🗝️ Authorize Member*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Send member *handle* of the member 
you wish to allow to authorize 
transactions for:
- *{company}*

{message}
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

CONFIRM_AUTHORIZATION = """
> *🗝️ Confirm Authorization*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Do you wish to allow member:

- *{member}*

to perform transactions for
- *{company} ?*

*1. ✅ Authorize*
*2. ❌ Cancel*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

AUTHORIZATION_SUCCESSFUL = """
> *✅ Success*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Member authorization complete!
- *{member}*
can now transact on behalf of 
*{company}*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

DEAUTHORIZATION_SUCCESSFUL = """
> *✅ Success*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Access has been revoked!
- *{member}*
can nolonger transact on behalf of 
*{company}*
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
