# Currencies and mappings: shapes, the mapping file, refusals

Open this when you read a currency, build a mapping change or a create, or meet a refusal. The
commands and the yes rules are in `SKILL.md`.

## A currency

`list` returns `data[]` and `meta` (`pagination`, and `remaining_count`: how many more currencies
the app can create, out of 20). Each currency: `virtual_currency_id`, `code`, `name`,
`description` (or `null`), `created_at`, `updated_at` and `products_count` (deleted products
included).

`get` adds `mappings[]`, ordered by `product_id`. `updated_at` is an integer in milliseconds and
changes with any change of the currency or of one of its mappings: it is the token of the next
write.

- `code`: letters, digits and `_`, unique in the app, the letter case counts. The app, the Server
  API and the analytics filter know the currency by it. **It never changes after the create.**
- `name`: the display name. `description`: optional.

## A mapping

One product has at most one mapping in a currency. A mapping holds no product name: take the names
from `products list`.

- One-time product: `{"product_id": "<uuid>", "product_type": "one-time", "credit_per_purchase": 30}`.
  `credit_per_purchase`: the coins of each purchase, above 0.
- Subscription: `{"product_id": "<uuid>", "product_type": "subscription", "credit_per_cycle": 50,
  "expiring": true, "credit_on_trial_start": null}`. `credit_per_cycle`: the coins of each paid
  period, above 0. `expiring`: `true`, the coins of a period expire when the subscription ends or
  renews; `false`, they stay. `credit_on_trial_start`: the coins of a trial start, 0 or more;
  `null`, a trial gives none.

`product_type` comes from the product's `period` in `products list`: `weekly`, `monthly`,
`two_months`, `trimonthly`, `semiannual` and `annual` are `subscription`, any other period
(`lifetime`) is `one-time`. It never changes in a mapping. A purchase credits the coins of the mapping at that
moment: a later change does not credit past purchases again. A product with no mapping credits
nothing and writes no ledger row.

## The mapping file and the MCP list

`create` and `mappings upsert` take a list of whole mapping items: the CLI from a JSON file
(`--file`, a JSON array with at least one object), the MCP tool as a list parameter. Up to 200
items in one upsert, one item for each product.

```json
[
  {"product_id": "<annual product uuid>", "product_type": "subscription", "credit_per_cycle": 50, "expiring": true, "credit_on_trial_start": null},
  {"product_id": "<coin pack uuid>", "product_type": "one-time", "credit_per_purchase": 10}
]
```

- **Each item is the whole mapping, with no merge of fields:** to change only the coins of a
  subscription, send `expiring` and `credit_on_trial_start` as the read shows them.
  `credit_on_trial_start` is required in each subscription item (`null` for none).
- The upsert never removes a mapping: a product it does not name keeps its mapping as it is.
- The CLI checks the file before it reads or asks: not JSON, not a list or an empty list is exit
  2, and nothing is sent.
- The answer is the currency with all its mappings and `changes`: `created`, `updated` and
  `unchanged`, each a list of product ids. Name them as products when you read it back.

## Building the card

From the read just before the write, for each item of the change:

| The read has | The item | Card line |
|---|---|---|
| no mapping for the product | any | `<product>: new, <coins> <currency> for each purchase` (or `each paid period`) |
| a mapping with other coins | new coins | `<product>: <old> → <new> <currency> for each purchase` (or `each paid period`) |
| `expiring` or the trial coins | another value | `<product>: <field> <old> → <new>` (trial coins: `none` for `null`) |
| every field the same | the same | leave it out of the card: the server reports it as `unchanged` |

A removal names the product with its coins now → none (`<product>: 30 <currency> for each paid
period → none`) and says its purchases stop giving coins, with no ledger row to show it. A create lists the code, the name and each product with its coins, and says the currency can
never be deleted and its code never changes.

## Refusals the server sends

Say the reason in plain words and ask; never retry with changed values to get a write through.

- **409 `virtual_currency_conflict`:** the currency changed after your read; nothing was written.
  Read again, new card, new yes.
- **400 on create:** the code is used in the app, or the app has 20 currencies. The CLI and the
  tools pass the server's text as it is.
- **400 on a mapping:** the server's text names the item and the reason: an unknown or a missing
  field, coins below the minimum, or a product type that differs from the product or from the
  stored mapping.
- **404 on a removal:** the product has no mapping in the currency (already removed?). Read the
  currency again.
- **403:** the sign-in may read but not write, or the app belongs to another account.
- **429:** too many calls; the CLI waits and tries a read again by itself. Wait a few seconds
  before the next call.
