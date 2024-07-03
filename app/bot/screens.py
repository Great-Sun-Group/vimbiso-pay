ACCOUNT_SELECTION = """
> *👥 Accounts*

*{greeting}*

{first_name}, welcome to
your credex account.

*_Which account would you like_*
*_to view and manage?_*

{accounts}
"""

HOME = """
> *🏦 Credex*
{balance}
*👤 Account: _{handle}_*
 *1. 📥 Pending Offers ({pending_in})*
 *2. 🔀 Switch Account*
 *3. 📒 Review Ledger*
 *4. 💸 Offer Credex*
 *5. 💼 More Options*

 *What would you like to do ?*
"""

MANAGE_ACCOUNTS = """
> *💼 Manage Accounts*

*👥 My Accounts*
 *1. 💼 Create Business*
 *2. 🗝️ Authorize Member*
 *3. 📤 Pending Outgoing ({pending_out})*

Send *'Menu'* to go back to Menu
"""

INVALID_ACTION = """
*Invalid option selected*
"""

DELAY = """
*Hold on a moment ...*
"""

BALANCE = """
*SECURED BALANCE*
  Balance : *{securedNetBalancesByDenom}*

*USECURED BALANCE*
  Payables : *{totalPayables}*
  Receivables : *{totalReceivables}*
  PayRec : *{netPayRec}*

*CREDEX ASSETS*
  Credex Assets : *{netCredexAssetsInDefaultDenom}*
"""

BALANCE_FAILED = """
> *😞 Enquiry Failed*

Failed to perform balance
enquiry at the moment.
  
Send *'Menu'* to go back to Menu
"""

CREDEX = """
> *💰 Credex*

*Summary*

 Outstanding : {formattedOutstandingAmount}
 Party : {counterpartyDisplayname}
 Amount : {formattedInitialAmount}
 Date : {date}
 Type : {type}

Send *'Menu'* to go back to Menu
"""

REGISTER = """
> *👤  Registration*

*ℹ️  INSTRUCTIONS*
 To sign up for an account:

 - Click the *'Register'* button
   below and fill in the required
   fields and click submit.

Send *'Menu'* to go back to Menu
"""

COMPANY_REGISTRATION = """
> *💼  Create Business Account*

*ℹ️  INSTRUCTIONS*
 To create a new account :

 - Click the *'Create'* button
   below and fill in the required
   fields and click submit.

{message}
"""

OFFER_CREDEX = """
> *💰 Offer Credex*

*1.25=>CpHandle*
to offer *secured* credex 
from your account

  *OR*

*1.25->CpHandle=2024-06-03*
to offer *unsecured* credex 
from your account

_*CpHandle = CounterPartyHandle*_

{message}
"""

REGISTRATION_COMPLETE = """
> *🎉 Registered!*

Hello {full_name}

Welcome to Credex! We are 
excited to have you on board.

Send *'Menu'* and start 
exploring all the features 
we offer.
"""

CONFIRM_SECURED_CREDEX = """
> *💰 Confirm*

Offer unsecured credex:
  ${amount} {currency} to {party}

Make offer from:
{accounts}

"""

CONFIRM_UNSECURED_CREDEX = """
> *💰 Confirm*

Offer unsecured credex:
  ${amount} {currency} to {party}
  due {date}

Make offer from:
{accounts}
"""

ACCEPT_CREDEX = """
> *💰 Accept Offer*

*Accept {amount} offer*

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
> *✅ Success!*

Offered to: {recipient}
Amount: {amount} {currency}
Secured: {secured}

Send *'Menu'* to go back to Menu
"""

OFFER_FAILED = """
> *😞 Failed*

Failed to perform transaction
at the moment.

{message}

Send *'Menu'* to go back to Menu
"""

ADD_MERMBER = """
> *🗝️ Authorize Member*

Send member *handle* of the 
member you wish to allow to 
authorize transactions for 
*{company}*

{message}
"""

CONFIRM_AUTHORIZATION = """
> *🗝️ Confirm Authorization*

Do you wish to allow member:

- *{member}*

to perform transactions for
*{company} ?*

*1. ✅ Authorize*
*2. ❌ Cancel*
"""

AUTHORIZATION_SUCCESSFUL = """
> *✅ Success*

Member authorization complete!

- *{member}*

can now transact onbehalf of 
*{company}*
"""

AUTHORIZATION_FAILED = """
> *❌ Failed*

Member authorization failed!
"""