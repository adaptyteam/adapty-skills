# Prices

How to read the app's prices, place them against the market, choose a price hypothesis, test it
on a copy, and change a live price. Expected ranges still come only from `evidence.md`.

## Where the numbers come from

- **The app's prices:** the price CSV of each product (below).
- **The market's prices:** `price-index.csv`, from Adapty's
  [State of In-App Subscriptions report](https://adapty.io/state-of-in-app-subscriptions-report/):
  2025 prices in USD by country, category and plan, as the average and the 10th to 90th
  percentile across apps, with the 2023 average beside them. Rows with `country` `All` are
  regions.
- **How price levels behave:** `price-response.csv`, the same report: conversion, value per
  paying subscriber after 380 days and renewal rates at four price levels (the quartiles), by
  region, category and plan.

Both files are long; search them, never read them whole:

```bash
grep -i '^Germany,DE,[^,]*,Photo & Video,' references/price-index.csv
grep -i '^Europe,Photo & Video,annual,' references/price-response.csv
```

**These tables compare different apps, not one app changing its price.** In them, weekly plans
in the most expensive quarter convert better, because stronger apps charge more. A claim from them
has this shape: "your annual is in the cheapest tenth of photo apps in the US; an A/B test on a
copy will show whether a higher price earns more" (the form, not words to copy). Where the app stands is the finding; what
buyers would pay is the test's answer. What a change does comes from `evidence.md`, or it is
untested.

**The app's category** is not in the CLI. Infer it from the app's name and paywall, say which
row you used, and let the user correct it. When no row fits, use `All`; never borrow a neighbouring
category.

**Coverage.** 22 countries: US, CA, GB, DE, FR, IT, ES, AR, MX, CL, BR, CO, SA, AE, ZA, QA, TR,
AU, JP, KR, IN, ID. Categories: Education, Entertainment, Graphics & Design, Health & Fitness,
Lifestyle, Photo & Video, Productivity, Utilities, and All, spelled exactly so in the file. **Grep
the category row first** (`'^United States,US,[^,]*,Photo & Video,annual,'`) and use it when it
comes back. Use the country's `All` row only when that grep is empty or the row is thin (its
25th, 50th and 75th percentiles are equal), and say which of the two it was.

**A country's numbers exist only when its grep returns a row.** When the grep for a country is
empty (the Netherlands, Sweden, Poland and every other country not listed above), the reply says
"Adapty's index has no data for <country>", and any comparison for it uses its region's row,
named as the region ("Europe overall"), or only its own past. Never give it a percentile, a
median or a ratio of its own, and never fold it into a figure for several countries.

## Reading the app's prices

The price CSV is the product card's Download in the Adapty dashboard: one file per product,
App Store and Google Play only. Find the command in `$ADAPTY products --help`. When the CLI has
none, ask the user to download the file from the product's card in the dashboard and attach it.

Its columns, in order:

`region_name, region_code, app_store_currency, app_store_requested_price,
app_store_synced_price, app_store_sync_status, play_store_currency,
play_store_requested_price, play_store_synced_price, play_store_sync_status`

`region_code` is the two-letter country code, currency the three-letter code. The price buyers
pay is `*_synced_price`. Stripe, web and offer prices are not in it; for those, ask.

Read the products that sell in the countries carrying 80% of revenue in the last full month,
store by store. To compare with the index, convert each price to USD at the rate the app's own
revenue implies, for one product, store and country:

```bash
$ADAPTY analytics chart --app <APP_ID> --chart revenue --date-from $FROM --date-to $TO --group-by country --filter store=<STORE> --filter store_product_id=<VALUE> --filter offer_category=<NO_OFFER>,<FREE_TRIAL> --filter renewal_status=<NEW> --json
$ADAPTY analytics chart --app <APP_ID> --chart subscriptions_new --date-from $FROM --date-to $TO --group-by country --filter store=<STORE> --filter store_product_id=<VALUE> --filter offer_category=<NO_OFFER>,<FREE_TRIAL> --json
```

Take the filter values from `analytics values`. The two offer categories are the first payments
at full price (straight away, or after a free trial); a paid intro offer would lower the result.
Revenue ÷ new subscriptions is the USD price there. When either number is empty, ask the user for the rate rather than guess.

## Placing a price

For each plan in each top country, write down:

1. **Its percentile:** where the USD price falls among the country's 10th to 90th percentile for
   the app's category and plan.
2. **Its ratio to the main market** (the country with the most revenue), against the market's
   ratio: the country's `avg_2025` ÷ the main market's `avg_2025`, same category and plan.
3. **That country's own conversion, refunds and purchases,** from the audit reads.

**Tier-1 markets:** US, Canada, UK, Ireland, Australia, New Zealand, Germany, France, Italy,
Spain, Portugal, the Netherlands, Belgium, Luxembourg, Austria, Switzerland, Denmark, Sweden,
Norway, Finland, Iceland, Japan, South Korea. `evidence.md` splits price results on this line;
this list is the line.

## Which price hypothesis

| Type | Suggest it when | Expected |
|---|---|---|
| Raise the core price | The main market is Tier-1, the plan is below the 50th percentile, and the app's conversion is at or above the market median (`market.md`) | `evidence.md`'s Tier-1 price-increase range |
| Lower the core price | The plan is above the 75th percentile, conversion is below the median, and the main market is not Tier-1 | Untested |
| Raise in a country | Tier-1, and the app's ratio to the main market is 15% or more below the market's | `evidence.md`'s Tier-1 range |
| Lower in a country | Not Tier-1, the app's ratio is 15% or more above the market's, and the country converts below its own past | Untested |
| Plan ladder | The app's annual ÷ weekly or annual ÷ monthly differs from the category's 50th-percentile ratio by 20% or more (when that row is thin, from 7× weekly or 5× monthly) | Untested |

- **A price hypothesis's Why ends on what its test settles:** "…, so the A/B test shows whether
  €39.99 earns more per user" (the form, not words to copy). The result is the test's to give; the Why never states it.
- **At most one core-price hypothesis,** on the main market's plan with the most revenue.
- **The new price is set as in "Setting the new price" below.**
- **Never a raise outside Tier-1.** `evidence.md`: the same increase lost badly there.
- **One price change, on one product, per hypothesis,** never together with a trial or offer
  change, and compared inside one store.
- **Judged on revenue per user,** refunds included. A cut that lifts conversion and lowers
  revenue per user lost.
- **Time:** a weekly plan's test runs at least four weeks so renewals show. An annual plan's
  test is judged on first-year revenue and refunds, and the Time line says renewals cannot be
  seen yet.

## Setting the new price

The index decides whether a price moves and by how much. The new price itself always starts from
what the store charges now, in its own currency.

1. **Size the move in percent:** how far the price sits from its target (the next percentile up
   or down for a core price, the market's ratio to the main market for a country, the category's
   ratio for a ladder). Under 5%, there is no hypothesis. Otherwise the move is that gap, at most
   15% when only the market comparison supports it, and at most 30% when the country's own
   install → paid also does (above the app's overall rate for a raise, below it for a cut).
   The cap is decided country by country, also inside a group: a move over 15% in a country
   puts that country's install → paid and the app's overall rate in the reply ("UK 2.4% against
   1.8% app-wide"). Without those two numbers the move is 15% at most.
2. **Apply it to the local price:** the new price is the country's `*_synced_price` × (1 + the
   move), in its currency. USD is only for comparing, never for producing the price. Only a
   country where the product has no price yet starts from the main market's price converted at
   the app's own rate.
3. **Land on a price the store's buyers see,** the nearest one within the cap ending in .99, .49,
   .95, .90, .50 or .00 ("€38.99", "R$ 179,90"). On Google Play these currencies take a whole
   number: BIF, CLP, DJF, GNF, JPY, KMF, KRW, PYG, RWF, UGX, VND, VUV, XAF, XOF, XPF. The preview
   then snaps App Store prices to Apple's price points; quote the previewed price.
4. **Keep the plan ladder:** after the change a shorter plan still costs less than any longer one,
   annual is at least 4× weekly and at least 3× monthly. A move that breaks this is made smaller
   or dropped.

A price the user names is theirs to choose; when it is outside these limits, say so once.

## Setting up a price A/B test

A live price change reaches everyone in that country, so it is never the test. The test runs
on a copy of the product, and only a winning price moves to the original. Each write is on the
user's yes.

1. **You create the new store product.** On the App Store, a new subscription in the same
   group; on Google Play, a new base plan on the same subscription.
   The A/B test starts only after the store approves it.
2. **I create the Adapty product** with `products create` and that store product ID.
3. **I build the copy's price file:** download the original product's CSV, keep `region_code`
   and, for each store the copy is sold in, its `*_currency` and `*_requested_price` columns.
   Each country keeps the original's `*_synced_price`, or its `*_requested_price` where the
   synced cell is empty; then only the test countries change. The copy then matches the
   original everywhere else.
4. **I preview the file** and show the user the prices it will set; the App Store rounds to its
   own price points here. A row error saves nothing: fix the rows and preview again, never
   upload around an error. Then upload to the new product. When the CLI has no price
   commands, give the user the file to upload on the product's card in the dashboard.
5. **I build the paywall or flow copy** that sells the new product, through `flow-generator`.
6. **I set up the country segment** through `audiences`.
7. **You run the A/B test** in the dashboard, against the current paywall on that placement.

## Changing a live price

A winning price moves to the original product, or the user asks for a price change without a
test. When the user asked for the change, the A/B test on a copy is your first Next step and your
pick; this block follows as the alternative they can say yes to. Upload only on an explicit yes to this block, after a preview. "Go ahead" before the block
was shown is not that yes.

1. **Download the product's CSV first** and keep it in the temporary directory: that is the
   rollback. Say where it is.
2. **Preview** the new file, and put the previewed prices in the block.
3. **Existing subscribers keep their price** unless the user asks to move them. If they do, say
   what it means per store: on the App Store they move at renewal, with any consent handled by
   Apple; on Google Play they must accept the increase, and those who do not lapse.
4. **Say when it takes effect, per store in the change:** an approved App Store subscription two
   days after the upload, one not yet approved at once; Google Play at once.

Shape of the ask (the form, not words to copy):

> I'll change the price of **Annual** (`com.app.annual`) on the App Store:
> - Brazil: R$ 149,90 → R$ 99,90
> - Mexico: MXN 649 → MXN 549
>
> New buyers pay it from two days after I upload; current subscribers keep their price. Nothing
> will measure whether it helped; an A/B test on a copy would. To undo it, I re-upload
> `annual.before.csv`. Shall I go ahead?

On a yes: upload, then download again after a few minutes; the stores receive the prices about a
minute after the upload. Report each changed country's `*_sync_status`: `synced` is done,
`pending` is still on its way (check again before calling it failed), and `failed` or
`subscribers_migration_failed` comes with its reason.
