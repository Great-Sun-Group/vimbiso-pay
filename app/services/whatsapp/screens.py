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

INVALID_ACTION = """❌ Invalid option selected.

⚠️ Your session may have expired.
Send "hi" to log back in."""

DELAY = """🌟 Welcome to the credex ecosystem.
⏳ Please hold a moment."""

BALANCE = """*💰 SECURED BALANCES*
{securedNetBalancesByDenom}

*📊 NET ASSETS*
  {netCredexAssetsInDefaultDenom}
{tier_limit_display}"""

UNSECURED_BALANCES = """*📈 UNSECURED BALANCES*
  📉 Payables : {totalPayables}
  📈 Receivables : {totalReceivables}
  💱 PayRec : {netPayRec}"""

BALANCE_FAILED = """*😞 Enquiry Failed*

❌ Failed to perform balance
enquiry at the moment.

Type *'Menu'* to return to dashboard"""

CREDEX = """*💰 Credex*

*📋 Summary*

 📊 Outstanding : {formattedOutstandingAmount}
 👥 Party : {counterpartyDisplayname}
 💵 Amount : {formattedInitialAmount}
 📅 Date : {date}
 📝 Type : {type}

Type *'Menu'* to return to dashboard"""

REGISTER = """Welcome to VimbisoPay 💰

We're your portal 🚪🌐
to the credex ecosystem 🌱

Open a free credex account 💳
to get started 📈"""

CONFIRM_OFFER_CREDEX = """*💰 Offer Confirmation*

📤 Offer ${amount} {denomination} {secured} credex to
*{party}* from
account *{source}*

1. ✅ Yes
2. ❌ No"""

ACCEPT_CREDEX = """*💰 Accept Offer*

*📥 Accept ${amount} offer*

  {type} credex from
- {party}"""

OUTGOING_CREDEX = """*💰 Cancel Offer*

*❌ Cancel {amount} offer*

  {type} credex to
- {party}"""

ACCEPT_INCOMING_CREDEX = """*💰 Accept Incoming Offer*

*📥 Accept ${amount} offer*

  {type} credex from
- {party}

1. ✅ Accept
2. ❌ Decline"""

DECLINE_INCOMING_CREDEX = """*💰 Decline Offer*

*❌ Decline ${amount} offer*

  {type} credex from
- {party}

Are you sure you want to decline?

1. ✅ Yes, decline
2. ❌ No, keep offer"""

OFFER_SUCCESSFUL = """*💰 Complete!*

*✅ Transaction Complete!!*

📤 You have successfully offered
${amount} {denomination} {secured} to
{recipient}.

📤 From: {source}"""

OFFER_FAILED = """*😞 Failed*

 {message}‼️

*📤 To issue a secured credex send*
  0.5=>recipientHandle

*📤 To issue an unecured credex send*
  0.5->recipientHandle

Type *'Menu'* to return to dashboard"""

ADD_MEMBER = """*🗝️ Authorize Member*

👤 Send member *handle* of the member
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

🎉 Member authorization complete!
👤 *{member}* can now transact on
behalf of *{company}*"""

DEAUTHORIZATION_SUCCESSFUL = """*✅ Success*

🔒 Access has been revoked!
👤 *{member}* can no longer
transact on behalf of *{company}*"""

AUTHORIZATION_FAILED = """*❌ Failed*

🚫 Member authorization failed!

{message}"""

MEMBERS = """*👥 Members*

*👤 Add or remove members*

🔑 You can authorize others to transact
on behalf of this account (max 5).

1. ➕ Add new member
{members}"""

NOTIFICATIONS = """*🔔 Notifications*

*📱 Update notification recipient*

👤 *{name}* currently receives
notifications of incoming offers.

Change to:
{members}"""

NOTIFICATION = """*🔔 Notifications*

📱 Notifications of incoming offers now
being sent to :
- 👤 *{name}*"""

PROFILE_SELECTION = """*👤 Profile*
{message}"""
