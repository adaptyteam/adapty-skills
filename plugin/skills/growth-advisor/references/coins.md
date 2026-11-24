# Coins: virtual currency numbers and coin products

Open this when the app sells a virtual currency (coins, gems, credits: a currency maps the
products that give it) and the question is about coins or the products that give them: how many
were bought, spent or expired, which coin pack sells, packs against a coin subscription, which
coin amounts to test. A currency's mappings, one user's balance and the ledger rows are the
`virtual-currencies` skill's; invoke it on the user's yes for any of them.

## Reading the currency first

1. **The codes:** `$ADAPTY analytics values --app <APP_ID> --dimension virtual_currency --json`.
   Each value is a currency code; `no-virtual-currency` is every product that gives no coins.
2. **The coins of each product** (reads, no yes):

   ```bash
   $ADAPTY virtual-currencies list --app <APP_ID> --json
   $ADAPTY virtual-currencies get <currency_id> --app <APP_ID> --json
   ```

   Over MCP, `virtual_currencies_list` and `virtual_currencies_get`. A mapping gives a one-time
   product its coins for each purchase (`credit_per_purchase`) and a subscription its coins for
   each paid period (`credit_per_cycle`), with `expiring` and the trial coins. Name products from
   `products list`. With the CLI, probe `virtual-currencies list --help` first; no such topic after
   one `npx --yes adapty@beta … --help` try and no MCP tool: ask the user how many coins each
   product gives.
3. **Coins per dollar** of each product: its coins over its price in the price CSV
   (`pricing.md`, "Reading the app's prices"), per paid period for a subscription.

These reads change nothing. A mapping change is the `virtual-currencies` skill's, on the user's
yes; never write one here.

## The coin charts

Every coin chart counts coins of one currency, never money, and takes `--filter
virtual_currency=<code>` on every call: without it the server answers `one_currency_required`
with the codes it knows. No coin chart groups by product.

| Chart | Counts | Groupings |
|---|---|---|
| `vc_purchased` | coins bought: store purchases and renewals, without trial coins | `source`, `store` |
| `vc_trial` | coins of trial starts | `store` |
| `vc_granted` | rewards, less their reversals, dashboard rows included | `source`, `feature` |
| `vc_spent` | coins spent | `feature`, `customer_placement_id` |
| `vc_net_spent` | coins spent, less the spends given back | `feature`, `customer_placement_id` |
| `vc_expired` | coins that expired | none |
| `vc_refunded` | coins taken back by store refunds (only the coins that were left) | `store` |
| `vc_credited`, `vc_debited`, `vc_net_change` | every row in, every row out, and the difference | `operation` (`vc_credited` also `source`) |
| `vc_on_hand` | the coins users hold at the end of each period | none |

- **`vc_on_hand` is a balance:** the window's number is the balance at its end, never a sum of its
  points.
- **`vc_spent` at 0 while `vc_debited` is not** means the app sends spends without an operation:
  read `vc_debited`, say the spend charts are empty for that reason, and that the server should
  label each spend ([Label transactions](https://adapty.io/docs/virtual-currencies#label-transactions)).
- **Testers leave the coin charts:** a user with any sandbox row is out of every coin chart with
  all their rows, and past numbers can move when one more tester appears. The ledger keeps them,
  so a sum of ledger rows never matches a chart: never add rows up.
- A row counts on the day Adapty processed it; the newest rows can lag.

## Coin products in money

Products are compared in money, with the money charts filtered to the currency:

- **Revenue from coin products:** `revenue` with `--filter virtual_currency=<code>`; the same with
  `no-virtual-currency` is the revenue of the rest. Their share is how much of the app's money
  coins bring.
- **Each product:** `revenue`, `non_subscriptions` (one-time purchases), `subscriptions_new`,
  `arppu` and `refund_events`, each grouped by `store_product_id` and filtered to the currency.
- **Where each one sells:** the same chart filtered to one product
  (`store_product_id=<store>:<store product id>`) and grouped by `placement_id`, `paywall_id` or
  `flow_id`; `view-paid` grouped by `store_product_id` on one paywall.

## "Why does this pack sell better than that one?"

Read both packs over the same window (the last 12 months, or since the newer one launched), and
lay the differences side by side:

1. Purchases and revenue of each pack, and its refunds.
2. Coins per dollar of each pack.
3. Where each is offered: a pack on every paywall against one on a single flow is not a fair
   race; say so before comparing.
4. How each is shown: its position, the selected card, a badge, from the paywall or the flow
   (`levers.md`, Paywall design; `paywall-teardown` for the screen).

The numbers are facts; why buyers prefer one pack is a hypothesis, under "Before you state a
conclusion" in `diagnosis.md`. End with the A/B test that would tell.

## "Are coin packs better than a coin subscription?"

Compare them in money per paying user over the same horizon, as for any plan (`diagnosis.md`), then
add what only coins show:

- **Coins per dollar** of the subscription against the packs: a subscription that gives fewer
  coins per dollar than a pack at the same price competes on habit, not value.
- **Coin use:** `vc_purchased` grouped by `source` splits the coins of subscriptions from those of
  packs. A rising `vc_on_hand` with a flat `vc_spent` means buyers hold coins they do not use; a
  high `vc_expired` on an `expiring` subscription means subscribers lose coins, a reason to cancel.

Answer in the shape of "Should I change X?" (`diagnosis.md`). `evidence.md` has no entry for
coins: Expected is untested.

## Hypotheses from coins

- **A coin amount cannot be A/B tested on one product:** a mapping applies to every buyer at once,
  with no control. A test of amounts needs a second product with its own mapping, created like a
  price test's copy (`pricing.md`, "Setting up a price A/B test"), mapped by `virtual-currencies`
  on the user's yes, and shown in a second paywall or flow arm through `ab-tests`.
- **Changing a live mapping** with no test goes through `virtual-currencies` on the user's yes. A
  before and after is not a test: say so.
- **Coins that expire on the subscription:** when the coins of a subscription stay
  (`expiring: false`) and `vc_on_hand` grows, the allowance stops being a reason to renew and heavy
  users spend a stockpile instead of buying packs; making them expire is a mapping change on a yes
  (`virtual-currencies`), and a high `vc_expired` with falling renewals is the opposite signal.
- Common shapes, each with Expected untested: more coins per dollar on bigger packs, or a bigger
  pack on top; a coin subscription next to the packs; trial coins on the subscription; a top-up
  flow at the moment a user runs out (`flow-generator` builds it; the app opens it), or on a
  placement for users with a low balance (a segment by balance through `audiences`).
