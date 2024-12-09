# VimbisoPay User Flows

## 1. Registration & Onboarding

### Initial Contact
When a user first contacts the bot, they receive:
```
I'm VimbisoPay. I'm a WhatsApp chatbot. It's my job to connect
you to the credex ecosystem.

I'll show you around, and you can message me to interact with
your credex accounts.

Would you like to become a member of the credex ecosystem?
```

### About Credex
Users can learn about the system:
```
Credex is an accounting app that is helping Zimbabweans overcome
the challenges of small change and payments.

A credex is a promise to provide value, and the credex ecosystem
finds loops of value exchange.

Free Services:
- Open a credex account
- Receive a secured credex
- Issue secured/unsecured credex
- Accept a credex

Fees:
- 2% fee when cashing out secured credex for USD/ZIG
```

### Account Creation
Upon successful registration:
```
The free tier gives you one credex account, automatically created.
This is your personal account for any purpose.

Your credex member handle and account handle are set to your
phone number. These handles identify you and your accounts for
payments.
```

## 2. Account Management

### Account Selection
For users with multiple accounts:
```
Which account would you like to view and manage?

[List of accounts]
```

### Home Screen
Basic account view:
```
💳 [Account Name]
Account Handle: [handle]

SECURED BALANCES
[balances]

NET ASSETS
[total]
```

### Member Authorization
To authorize other members:
```
Send member handle of the member you wish to allow to authorize
transactions for [company]
```

Confirmation:
```
Do you wish to allow member [member] to perform transactions
for [company]?

1. ✅ Authorize
2. ❌ Cancel
```

## 3. Transaction Flows

### Offering Credex
To make an offer:
```
To issue a secured credex, enter the details of the transfer
into this form.

Alternative commands:
Secured: 0.5=>recipientHandle
Unsecured: 0.5->recipientHandle
```

### Confirmation
For secured credex:
```
Offer $[amount] [currency] secured credex to [party]
```

For unsecured credex:
```
Offer $[amount] [currency] unsecured credex to [party]
Due Date: [date]
```

### Transaction Results
Success message:
```
Transaction Complete!!

You have successfully offered $[amount] [currency] [type] to
[recipient].
From: [source]
```

## 4. Navigation Commands

- `menu` - Return to main menu
- `x` or `c` - Cancel current operation
- `home` - Return to account dashboard

## 5. Error Handling

Session expiry:
```
Invalid option selected.
Your session may have expired.
Send "hi" to log back in.
```

Failed operations show specific error messages with instructions to retry or return to menu.

## 6. Notifications

Users can manage notification settings:
```
[name] currently receives notifications of incoming offers.

Change to:
[list of members]
```

## Security Notes

1. Session Management
- 5-minute session timeout
- Automatic logout on expiry
- Secure state management

2. Authorization
- Member-level permissions
- Transaction authorization
- Account access control

3. Input Validation
- Amount validation
- Handle verification
- Date validation for unsecured credex
