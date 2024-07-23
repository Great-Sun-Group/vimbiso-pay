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

⚠️ DEMO ENVIRONMENT !!
"""

INVALID_ACTION = """
*Invalid option selected*
"""

DELAY = """
*Hold, just a moment ...*
"""

BALANCE = """
*SECURED BALANCE*
{securedNetBalancesByDenom}
*USECURED BALANCE*
  Payables : {totalPayables}
  Receivables : {totalReceivables}
  PayRec : {netPayRec}

*CREDEX ASSETS*
  Credex Assets : {netCredexAssetsInDefaultDenom}
  
⚠️ DEMO ENVIRONMENT !!
"""

BALANCE_FAILED = """
> *😞 Enquiry Failed*

Failed to perform balance
enquiry at the moment.
  
Send *'Menu'* to go back to Menu

⚠️ DEMO ENVIRONMENT !!
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

⚠️ DEMO ENVIRONMENT !!
"""

REGISTER = """
> *👤  Registration*

*ℹ️  INSTRUCTIONS*
 To sign up for an account:

 - Click the *'Register'* button
   below and fill in the required
   fields and click submit.

Send *'Menu'* to go back to Menu

⚠️ DEMO ENVIRONMENT !!
"""

COMPANY_REGISTRATION = """
> *💼  Create Business Account*

*ℹ️  INSTRUCTIONS*
 To create a new account :

 - Click the *'Create'* button
   below and fill in the required
   fields and click submit.

{message}
⚠️ DEMO ENVIRONMENT !!
"""

OFFER_CREDEX = """
> *💰 Offer Credex*

1.25=>CounterPartyHandle
to offer *secured* credex 
from your account

{message}
⚠️ DEMO ENVIRONMENT !!
"""

REGISTRATION_COMPLETE = """
> *🎉 Registered!*

Hello {full_name}

Welcome to Credex! We are 
excited to have you on board.

Send *'Menu'* and start 
exploring all the features 
we offer.

⚠️ DEMO ENVIRONMENT !!
"""

CONFIRM_SECURED_CREDEX = """
> *💰 Confirm*

Offer {secured} credex:
  ${amount} {currency} to {party}

Make offer from:
{accounts}
⚠️ DEMO ENVIRONMENT !!
"""

CONFIRM_UNSECURED_CREDEX = """
> *💰 Confirm*

Offer {secured} credex:
  ${amount} {currency} to {party}
  due {date}

Make offer from:
{accounts}
⚠️ DEMO ENVIRONMENT !!
"""

ACCEPT_CREDEX = """
> *💰 Accept Offer*

*Accept {amount} offer*

  {type} credex from
- {party} 
⚠️ DEMO !!
"""

OUTGOING_CREDEX = """
> *💰 Cancel Offer*

*Cancel {amount} offer*

  {type} credex to
- {party} 
⚠️ DEMO !!
"""

OFFER_SUCCESSFUL = """
> *✅ Success!*

*Offered*

{recipient}
Amount: {amount} {currency}
Secured: {secured}

Send *'Menu'* to go back to Menu
⚠️ DEMO ENVIRONMENT !!
"""

OFFER_FAILED = """
> *😞 Failed*

Failed to perform transaction
at the moment.

{message}

Send *'Menu'* to go back to Menu

⚠️ DEMO ENVIRONMENT !!
"""

ADD_MERMBER = """
> *🗝️ Authorize Member*

Send member *handle* of the 
member you wish to allow to 
authorize transactions for 
*{company}*

{message}
⚠️ DEMO ENVIRONMENT !!
"""

CONFIRM_AUTHORIZATION = """
> *🗝️ Confirm Authorization*

Do you wish to allow member:

- *{member}*

to perform transactions for
*{company} ?*

*1. ✅ Authorize*
*2. ❌ Cancel*

⚠️ DEMO ENVIRONMENT !!
"""

AUTHORIZATION_SUCCESSFUL = """
> *✅ Success*

Member authorization complete!

- *{member}*

can now transact on behalf of 
*{company}*
⚠️ DEMO ENVIRONMENT !!
"""

AUTHORIZATION_FAILED = """
> *❌ Failed*

Member authorization failed!

⚠️ DEMO ENVIRONMENT !!
"""

AGENTS = """
> *👤 Agents*

Agents
1. Hre (+263 77 369 6227)
2. Byo (+263 77 369 6227)
3. Kwe (+263 77 369 6227)
4. Kdm (+263 77 369 6227)
5. Rspe (+263 77 369 6227)

⚠️ DEMO ENVIRONMENT !!
"""
