"""WhatsApp message templates and screens"""

ACCOUNT_SELECTION = """*{greeting}*
{message}
*_Which account would you like to_*
*_view and manage?_*

{accounts}"""

HOME_1 = """*💳 {account}*
*Account Handle:* {handle}
{message}

{balance}"""

HOME_2 = """*💳 {account}*
*Account Handle:* {handle}
{message}

{balance}"""

MANAGE_ACCOUNTS = """*💼 Manage Accounts*

*👥 My Accounts*
 *1. 💼 Create Business*
 *2. 🗝️ Authorize Member*
 *3. 📤 Pending Outgoing ({pending_out})*

Type *'Menu'* to return to dashboard"""

INVALID_ACTION = """Invalid option selected.

Your session may have expired.
Send "hi" to log back in."""

DELAY = """Welcome to the credex ecosystem.
Please hold a moment."""

BALANCE = """*SECURED BALANCES*
{securedNetBalancesByDenom}

*NET ASSETS*
  {netCredexAssetsInDefaultDenom}"""

UNSECURED_BALANCES = """*UNSECURED BALANCES*
  Payables : {totalPayables}
  Receivables : {totalReceivables}
  PayRec : {netPayRec}"""

BALANCE_FAILED = """*😞 Enquiry Failed*

Failed to perform balance
enquiry at the moment.

Type *'Menu'* to return to dashboard"""

CREDEX = """*💰 Credex*

*Summary*

 Outstanding : {formattedOutstandingAmount}
 Party : {counterpartyDisplayname}
 Amount : {formattedInitialAmount}
 Date : {date}
 Type : {type}

Type *'Menu'* to return to dashboard"""

REGISTER = """*👤  Welcome to VimbisoPay*
~ Your portal to the credex accounting and payment ecosystem

Once you've created your free account below, just message us at this number to manage your accounts and payments, and to be first in line for new features."""

MORE_ABOUT_CREDEX = """*About Us*

Credex is an accounting app that is helping Zimbabweans overcome the challenges of small change and payments.

VimbisoPay is a Zimbabwe company that facilitates and secures transactions in the credex ecosystem.

A credex is a promise to provide value and the credex ecosystem finds loops of value exchange.

If I owe you and you owe me we can cancel our debts to each other without money changing hands.

If I owe you and you owe Alice and Alice owes Bob and Bob owes me we could cancel those debts in the same manner.

*It's free to:*
- Open a credex account.
- Receive a secured credex from VimbisoPay or any other counterparty.
- Issue a secured or unsecured credex.
- Accept a credex.

*Fees:*
A fee of 2% will be charged when cashing out a secured credex with VimbisoPay for USD or ZIG. Third parties may add additional charges. So only cash out if your counterparty won't accept a credex.

Your account and transactions are managed easily within WhatsApp.

1. Join the credex ecosystem
2. Find out more about credex"""

REGISTER_FORM = """*👤  Registration*

That's great I'll sign you right up.
I just need to know your name.

{message}"""

COMPANY_REGISTRATION = """*💼  Create New Account*

To create a new account tap *Create*
*Account* below and submit the linked
form.

{message}"""

OFFER_CREDEX = """*💰 New Secured Credex*

Please fill out the following form to
create a new secured credex offer.

You'll need to provide:
- Amount and denomination
- Recipient's handle
- Source account

{message}"""

ACCOUNT_REGISTRATION_COMPLETE = """*🎉 Account Created!*

Ok {first_name} we've got your
new account registered"""

REGISTRATION_COMPLETE = """*🎉 Account Created!*

Ok {firstName} we've got you
registered. The free tier of the
credex ecosystem gives you one
credex account which has been
automatically created for you.

This is your personal account.
You can use it for anything you
like including business purposes
for now but later on you will
be able to open dedicated accounts
for different businesses.

Your credex member handle and the
account handle of your personal
credex account have both been
set to your phone number.

These handles identify you as a
member and identify accounts for
sending payments to.

When you make a payment you'll
need to enter an account handle
so the credex goes to the right
place."""

CONFIRM_SECURED_CREDEX = """*💰 Confirm Secured Credex*

Offer ${amount} {denomination} {secured} credex
to *{party}*"""

CONFIRM_OFFER_CREDEX = """*💰 Offer Confirmation*

Offer ${amount} {denomination} {secured} credex to
*{party}* from
account *{source}*

1. ✅ Yes
2. ❌ No"""

CONFIRM_UNSECURED_CREDEX = """*💰 Confirm Unsecured Credex*

Offer ${amount} {denomination} {secured} credex to
*{party}* from
account *{source}*

{date}"""

ACCEPT_CREDEX = """*💰 Accept Offer*

*Accept ${amount} offer*

  {type} credex from
- {party}"""

OUTGOING_CREDEX = """*💰 Cancel Offer*

*Cancel {amount} offer*

  {type} credex to
- {party}"""

ACCEPT_INCOMING_CREDEX = """*💰 Accept Incoming Offer*

*Accept ${amount} offer*

  {type} credex from
- {party}

1. ✅ Accept
2. ❌ Decline"""

DECLINE_INCOMING_CREDEX = """*💰 Decline Offer*

*Decline ${amount} offer*

  {type} credex from
- {party}

Are you sure you want to decline?

1. ✅ Yes, decline
2. ❌ No, keep offer"""

OFFER_SUCCESSFUL = """*💰 Complete!*

*Transaction Complete!!*

You have successfully offered
${amount} {denomination} {secured} to
{recipient}.

From: {source}"""

OFFER_FAILED = """*😞 Failed*

 {message}‼️

*To issue a secured credex send*
  0.5=>recipientHandle

*To issue an unecured credex send*
  0.5->recipientHandle

Type *'Menu'* to return to dashboard"""

ADD_MEMBER = """*🗝️ Authorize Member*

Send member *handle* of the member
you wish to allow to authorize
transactions for *{company}*
{message}"""

CONFIRM_AUTHORIZATION = """*🗝️ Confirm Authorization*

Do you wish to allow member
*{member}* to perform transactions
for *{company} ?*

*1. ✅ Authorize*
*2. ❌ Cancel*"""

AUTHORIZATION_SUCCESSFUL = """*✅ Success*

Member authorization complete!
*{member}* can now transact on
behalf of *{company}*"""

DEAUTHORIZATION_SUCCESSFUL = """*✅ Success*

Access has been revoked!
*{member}* can no longer
transact on behalf of *{company}*"""

AUTHORIZATION_FAILED = """*❌ Failed*

Member authorization failed!

{message}"""

AGENTS = """*👤 VimbisoPay*

*Cash in:* cash can be used to
purchase a secured credex from
VimbisoPay at no cost.

Secured credex can also be
purchased from anyone who has a
secured balance at the market
rate agreed between you.

*Cash out:* if you have a secured
balance you can cash out with
VimbisoPay for a 2% fee.

You can also sell secured credex
to other members for cash at the
market rate agreed between you.

Cash in/out with VimbisoPay in
Mbare."""

MEMBERS = """*👥 Members*

*Add or remove members*

You can authorize others to transact
on behalf of this account (max 5).

1. Add new member
{members}"""

NOTIFICATIONS = """*🛎️ Notifications*

*Update notification recipient*

*{name}* currently receives
notifications of incoming offers.

Change to:
{members}"""

NOTIFICATION = """*🛎️ Notifications*

Notifications of incoming offers now
being sent to :
- *{name}*"""

PROFILE_SELECTION = """*👤 Profile*
{message}"""
