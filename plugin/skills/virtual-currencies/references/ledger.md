# The coin ledger: transactions and balances

Open this when you read coin transactions or a user's balances, or answer "why does this user have
N coins". The commands are in `SKILL.md`; totals and trends are `growth-advisor`'s.

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
| `dashboard_transaction` | a change made in the dashboard |
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
   trial, the app's server, the dashboard), each spend with its `feature`, each refund and expiry.
   Read the next page only while the rows do not yet explain it, and say how far back you read.
3. **When the user expected another number,** read the currency (`get`) and compare: a purchase
   credits the mapping of that moment; a product with no mapping credits nothing and leaves no row;
   coins of an `expiring` subscription expire when it ends or renews.
4. **Sandbox rows** (`is_sandbox: true`) come from sandbox purchases and sandbox calls; say when
   the rows you explain are sandbox ones.

Example of the answer's shape, not words to copy:

> They have **40 gems**, all available.
> - Nov 3: +30, the Annual plan purchase
> - Nov 10: +20, a change made in the dashboard
> - Nov 12: −10, spent on "unlock level"
>
> I read their transactions back to Nov 1; nothing before that changes this number.
