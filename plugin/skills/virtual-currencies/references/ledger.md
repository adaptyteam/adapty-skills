# The coin ledger: transactions and balances

Open this when you read coin transactions or a user's balances, answer "why does this user have
N coins", or credit or debit one user's balance. The commands are in `SKILL.md`; totals and trends
are `growth-advisor`'s.

## One page for each call

The transaction reads give one page for each call and never read all pages:

- The answer is `{data, meta}`: `data` are the rows, newest first; `meta.pagination` has
  `has_more` and `next_cursor`; `meta.query` is the period, the time zone and the filters that the
  page used.
- **`has_more: true` means this page is not the whole period.** Say so. The next page is the same
  call with the same period, filters and time zone, plus the cursor (CLI `--cursor
  <next_cursor>`, MCP `cursor`); another set gives 400 `cursor_filters_mismatch`. The CLI table
  ends with the next command to run.
- Page size: 20 unless you give another, at most 100.
- The days of the period are `YYYY-MM-DD`, both included, in the time zone you give (an IANA name
  such as `Europe/Berlin`) or else the app's time zone.
- The app list needs a period of at most 366 days (400 `invalid_date_range` otherwise): for a
  longer span, read windows of at most 366 days one after the other and say which you read. It
  reads a copy that can lag, so a row of the last moments can be missing; the history of one user
  has it at once, and takes the period as optional, with no length limit.
- Filters: the currency code, the operation, the feature and sandbox or production; their flag
  names are in `--help`, their parameter names in the tool's schema.
- Each read allows 2 calls a second for one app. A 429 says when to call again; the CLI waits and
  tries 3 times.

## One user: by profile or by customer user id

`profiles transactions list` and `profiles balances get` take the user by exactly one of the
Adapty profile id (CLI `--profile`) and the app's customer user id (CLI `--customer-user-id`).
Both or neither: the CLI exits 2 and the tool refuses, with nothing sent. 404
`profile_does_not_exist`: the app has no such user, or, by customer user id, the app deleted the
user (by profile id a deleted user still answers). A 404 with another code says nothing about the
user: give the server's text and say this read is not available there.

## A transaction row

`transaction_id`, `profile_id`, `transaction_type`, `items[]` (`currency_code`, `amount`: positive
for a credit, negative for a debit; `balance_after`: that currency's balance right after the row;
`expires_at`: when the coins of a credit expire, `null` when they do not), `operation`, `feature`,
`customer_placement_id`, `reference_id`, `metadata`, `is_sandbox`, `store`,
`store_transaction_id`, `created_at` (UTC).

What wrote the row, `transaction_type`:

| Value | Meaning |
|---|---|
| `store_purchase` | a purchase of a mapped product |
| `subscription_renewal` | a renewal of a mapped subscription |
| `trial_start` | a trial start of a subscription with trial coins |
| `api_transaction` | a write through the Server API |
| `sdk_debit` | a spend from the app through the SDK |
| `dashboard_transaction` | a manual adjustment: in the dashboard (`metadata.comment` when given), or through the CLI or MCP (`metadata.source`: `cli` for a developer token, also through the MCP server; `mcp` for the Adapty MCP connector; `unknown` for another connector) |
| `hold_confirm` | the confirmation of a hold |
| `refund` | a store refund that takes back credited coins |
| `expiry` | coins removed because they expired |

`operation` is the business meaning, `null` when the writer gave none: `top_up`, `refund`,
`spend`, `spend_reversal`, `reward`, `reward_reversal`, `exchange`, `expiry`, `migration`,
`adjustment`.

## A user's balances

`profiles balances get` returns one entry for each currency of the app: `code`, `name`, `balance`
(all coins, held ones too), `held` (reserved by active holds), `available` (what the user can spend
now) and `expiry`: `non_expiring`, `expiring[]` (`amount`, `expires_at`, soonest first, at most
10), `expiring_later` (expiring coins the list does not show) and `expired` (past expiry, normally
0, gone from `balance` within minutes).

## Why a user has N coins

**Coins gone after a reinstall, on another device or after a login:** a balance belongs to one
profile and never moves, so the coins are on the old profile
([Balances, profiles, and devices](https://adapty.io/docs/virtual-currency-balance#balances-profiles-and-devices)).
Read it by profile id when the user can give it; the lasting fix is identifying users in the app.

1. **Read the balances** of the user. Say `balance`, and `available` when it differs: name the
   held coins and the coins about to expire with their dates.
2. **Read the user's transactions** of that currency, newest first, filtered by the `code` of its
   balance entry (the case counts; a code the app does not have gives an empty page, not an
   error). The newest row's `balance_after` is the balance at that moment. Walk back until the
   rows explain the number: each credit with what wrote it (the product's purchase, a renewal, a
   trial, the app's server, a manual adjustment), each spend with its `feature`, each refund and
   expiry. Read the next page only while the rows do not yet explain it, and say how far back you read.
3. **When the user expected another number,** read the currency (`get`) and compare: a purchase
   credits the mapping of that moment; a product with no mapping credits nothing and leaves no row;
   coins of an `expiring` subscription expire when it ends or renews.
4. **Sandbox rows** (`is_sandbox: true`) come from sandbox purchases and sandbox calls; say when
   the rows you explain are sandbox ones.
5. **When the user expected another number or asks for a fix,** end on one next step: the
   adjustment that sets the balance to the number they expect ("I can credit 10 gems to make it
   50"), run by "Adjust one user's balance" after its card. Do not offer it when the number is
   right.

Example of the answer's shape, not words to copy:

> They have **40 gems**, all available.
> - Nov 3: +30, the Annual plan purchase
> - Nov 10: +20, a manual adjustment
> - Nov 12: −10, spent on "unlock level"
>
> I read their transactions back to Nov 1; nothing before that changes this number.

## Adjust one user's balance

`profiles transactions create` (MCP `profiles_transactions_create`) credits or debits one user's
balance in one currency and writes a ledger row of type `dashboard_transaction`. One user and one
currency for each call; many users are the app server's job (`SKILL.md`, "It does not own").

1. **Read the user's balances** (`profiles balances get`) right before the card, by the same
   profile ID or customer user ID the write will use. The currency `code` comes from that read;
   a code the app does not have is refused with `unknown_currency`.
2. **Take each value from the user's words or the read:** the direction (`credit` or `debit`), the
   amount (a whole number above 0: the difference to the number the user wants), the operation and
   the feature. Credit operations: `reward`, `spend_reversal`, `adjustment`; debit:
   `reward_reversal`, `spend`, `adjustment`; `adjustment` is a correction that is neither a reward nor a reversal. The
   feature is what the coins are for: one part, or two joined by a dot, each 1 to 32 letters,
   digits or `_`, such as
   `support_compensation`. A value the user did not give goes on the card as your proposal, so
   their yes covers it. The reason the user gave can go in the comment (up to 200 characters).
3. **Show the card** (`references/mappings.md`, "Building the card", a balance adjustment) and
   wait for the yes. A debit above `available` is refused (`insufficient_balance`): say so before
   the card and ask.
4. **Write:** CLI `$ADAPTY virtual-currencies profiles transactions create --app <id>
   --profile <id>` (or `--customer-user-id <id>`) `--currency-code <code> --direction <d>
   --amount <n> --operation <op> --feature <f> --yes --json`, with `--reference-id` and `--comment` when you
   send them; the rest is in `--help`. Over MCP the same values are the tool's parameters; when you
   can make a UUID v4 (`uuidgen`), send it as `idempotency_key`, so a call that never answers still
   has its key.
5. **Read the answer back:** the new `balance` and `available` of the currency. The answer names
   the `idempotency_key` of the write; keep it until the user has the result.

**Access.** Over MCP the write needs the edit right in the account: owners and admins by default.
A 403 for the missing write right is a refusal, not a failed write: nothing was written, so the
same write with the CLI is not a repeat. A support team member adjusts with the CLI, signed in with
their own login: run the write with the CLI when it is ready, else offer to set it up. A 403
`virtual_currency_adjustment_role_not_allowed` means the role of the signed-in team member
cannot adjust a balance (owner, admin and support can): say so; nothing was written.

**Other refusals** (nothing written): `insufficient_balance`, the debit is above the spendable
coins; `balance_overflow`, the credit goes above the largest balance; a 400 on `amount`,
`operation` or `feature` names the field; 404 `profile_not_found` or `profile_does_not_exist`, no
such user in the app. Say the reason in plain words and ask; never resend with other values on the
old yes.

### A lost answer of an adjustment

The CLI and the tool never repeat a write themselves. A write whose outcome is not known (the CLI
exit 5, or exit 4 with a 5xx; over MCP a 5xx or a lost connection) may have passed. The CLI prints
the key on stderr before it sends; the error text of each failure after the send names it too.

- **Repeat the write once with the same key and the same values,** within one hour of the first
  send: CLI `--idempotency-key <key>`, MCP `idempotency_key`. If the first write passed, the server
  returns its answer and writes nothing again; if it did not, this write runs. The server does not
  compare the values, so a repeat with other values gets the first answer. After that hour the
  server no longer knows the key, so the same key can write the change twice: do not repeat; read
  as for "No key known" below.
- **`idempotency_in_flight` (409):** the first write still runs. Wait a few seconds and send the
  same repeat again, at most 3 times; still in flight, read as for "No key known" below.
- **Never send it with a new key:** a new key can write the change twice. If the repeat gives no
  answer too, read the balances and the user's transactions, tell the user what is there, and
  stop. A new adjustment needs a new request, a new card and a new yes.
- **No key known** (over MCP the call itself never answered and you sent no key): do not repeat.
  Read the balances and the user's newest transactions, compare them with the card, tell the user
  what is there, and stop.
