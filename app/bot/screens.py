HOME = """
> *🏦 Credex*

*{greeting}*
{balance}
*🏡 Menu*
 *1. 📥 Pending Incoming ({pending_in})*
 *2. 📤 Pending Outgoing ({pending_out})*
 *3. 💸 Offer Credex*
 *4. 📒 Review Ledger*

*What would you like to do ?*
"""

PENDING_OFFERS = """
> *⏳ Pending Offers*

*Offer Types*
 *1. 📥 Pending Incoming ({incoming_count})*
 *2. 📤 Pending Outgoing ({outgoing_count})*

Send *'Menu'* to go back to Menu
"""

INVALID_ACTION = """
> *Invalid 🚫*

  *The option you selected*
  *is invalid please enter*
  *a valid input*

*Cancel = _'C'_*
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

 Date : {date}
 Outstanding : {formattedOutstandingAmount}
 Party : {counterpartyDisplayname}
 Amount : {formattedInitialAmount}
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

OFFER_CREDEX = """
> *💰 Offer Credex*
{message}
*ℹ️ INSTRUCTIONS*
*1.25=>CpHandle*
to offer *secured* credex 
from your account

  *OR*

*1.25->CpHandle=2024-06-03*
to offer *unsecured* credex 
from your account

_*CpHandle = CounterPartyHandle*_

Send *'Menu'* to go back to Menu
"""

REGISTRATION_COMPLETE = """
> *🎉 Registered!*

Hello {full_name}

Welcome to Credex! We are 
excited to have you on board.

Your registration is now 
complete. 

Here are your details:

Handle: {username}
Phone: {phone}

Send *'Menu'* and start 
exploring all the features 
we offer.

Thank you for joining us!

Best regards,
Credex
"""

CONFIRM_SECURED_CREDEX = """
> *💰 Confirm*
Would you like to offer 
{secured} credex to 
{party} for 
{amount} {currency}?

"""

CONFIRM_UNSECURED_CREDEX = """
> *💰 Confirm*
Would you like to offer 
{secured} credex to 
{party} for 
{amount} {currency}?

{date}
"""

ACCEPT_CREDEX = """
> *💰 Accept Offer*
Accept credex of {amount} 
{party}
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
  
Send *'Menu'* to go back to Menu
"""
