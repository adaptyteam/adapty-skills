# Prices

How to read the app's prices, place them against the market, choose a price hypothesis, test it
on a copy, add a plan length, and change a live price. Expected ranges still come only from
`evidence.md`.

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

One product's prices in every country, App Store and Google Play, as CSV (the same file as the
Download on the product's card in the dashboard). Save it in the temporary directory:

```bash
$ADAPTY product-prices list --product <PRODUCT_ID> --app <APP_ID> --csv
```

`<PRODUCT_ID>` is the Adapty product's id from `products list`. `--json` gives the same rows
with `app_store_sync_error` and `play_store_sync_error`, the store's reason for a failed row.

**Empty columns, or the header only, usually mean no store connection, and no error says so.**
Adapty imports a store's prices through that store's connection. Check it with
`$ADAPTY product-groups list --app <APP_ID> --store <STORE>`: exit 4 with
`missing_store_credentials` means the connection is missing, and on the App Store that is the
[App Store Connect API key](https://adapty.io/docs/app-store-connection-configuration.md), not the
In-App Purchase key. Tell the user prices cannot be read for that store until it is connected,
and make no price claim for it unless they give you the price.

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

1. **I check the store connection, then create the Adapty product for the copy.** The check
   comes first, because a product created with no store ID cannot be deleted:
   `$ADAPTY product-groups list --app <APP_ID> --store <STORE>` exits 4 with
   `missing_store_credentials` while the connection is missing (the
   [App Store](https://adapty.io/docs/app-store-connection-configuration.md) push needs the App
   Store Connect API key); then the user adds it and nothing is created. The copy has the
   original's period and access level and no store ID; the push adds it. Its title becomes the App Store subscription's reference
   name, which must differ from every other one in the group, and part of the description
   buyers can see, so it is the original's title plus a number ("Annual 2"), never a price. It
   carries the USD price a push
   needs, the original's US price. It is set once and cannot change after; the push spreads it
   to every country, and step 4 replaces those prices.

   ```bash
   $ADAPTY products create --app <APP_ID> --title "<TITLE> <N>" --period <PERIOD> --access-level-id <ACCESS_LEVEL_UUID> --price-usd <PRICE>
   ```
2. **The user approves the new store product ID;** it is permanent.
3. **I push the copy to the store:**

   ```bash
   $ADAPTY products push <COPY_ID> --app <APP_ID> --store app_store --store-product-id <NEW_ID> --group-id <GROUP_ID> --screenshot <FILE> --yes
   $ADAPTY products push <COPY_ID> --app <APP_ID> --store play_store --store-product-id <SUBSCRIPTION_ID> --android-base-plan-id <NEW_BASE_PLAN_ID> --yes
   ```

   - **The user's yes to the new ID is the confirmation,** so the push carries `--yes`: without
     it the CLI stops with exit 6 and pushes nothing.
   - **The copy has no trial or offer:** the push sets none. When the original has one, the user
     adds the same one to the copy in the store after the push (`levers.md`, "By store"), or the
     test changes two things at once.
   - **App Store:** a new subscription in the original's group, from `$ADAPTY product-groups
     list --app <APP_ID> --store app_store --page-size 100` (ask which when there are several). Every App Store
     push carries a review screenshot (below).
   - **Google Play:** a new base plan on the original's subscription; `<SUBSCRIPTION_ID>` is the
     original's Play product ID in `products get`.
   - A lifetime product takes neither `--group-id` nor `--android-base-plan-id`.
   - **After an App Store push, tell the user what it named the product:** the display name is
     the access level's SDK ID (`premium`) and the description "<title> <SDK ID> subscription",
     in en-US only. The push cannot set them; the user changes them in App Store Connect.

   **The review screenshot** is a JPEG at one of Apple's exact screen sizes (current iPhones:
   1320×2868, 1290×2796, 1260×2736, 1206×2622, 1179×2556, 1170×2532). A PNG from a simulator or a
   browser carries an alpha channel even when fully opaque and is refused. It shows the paywall
   the copy will be tested against, which sells the same plan. Get it in this order, and say which
   one you used:
   1. **The iOS Simulator,** when one is already running the app with that paywall on screen:
      `xcrun simctl io booted screenshot --type=jpeg review.jpg`; check the size with
      `sips -g pixelWidth -g pixelHeight review.jpg`. Never boot a simulator only for this: it
      needs several GB of memory.
   2. **`flow-generator`,** when that paywall is a flow: ask it for an App Store review screenshot
      of the screen with the purchase button. It writes a 1170×2532 JPEG.
   3. **The user:** ask for a screenshot of that paywall from an iPhone. Convert a PNG with
      `sips -s format jpeg <file> --out review.jpg` and check its size as in 1.

   A refused push exits 4 with its code in `--json`. `missing_store_credentials`: the app has no
   [App Store](https://adapty.io/docs/app-store-connection-configuration.md) or
   [Google Play](https://adapty.io/docs/google-play-store-connection-configuration.md)
   connection; the user adds it and I push again. `product_already_exists`: the store already
   has that ID, or on the App Store that title in the group; the user picks another ID, or I
   change the title. `duplicate_vendor_product_store`: a product of the app in Adapty already has
   that ID. Another product means the user picks another ID; the copy itself means an earlier
   push went through, so I read its `store_status` instead of pushing again.
   `review_screenshot_validation_error`: the screenshot's size or
   transparency. Any other code: say it as the CLI gives it.

   The answer shows the copy's `store_status`; read it again later with `products get`. On the
   App Store, `in_review` is waiting for Apple; `draft`, `rejected` or `action_required` means
   the user finishes it in App Store Connect. On Google Play, `action_required` means the base
   plan was not activated: the user activates it in Play Console. **The A/B test starts only once it is `approved`.**
4. **I build the copy's price file** from the original's CSV, for the store I pushed to only: in
   each country, that store's `*_requested_price` becomes the original's `*_synced_price` (it
   stays as it is where the synced cell is empty), and the other store's currency and price
   cells are left empty; the CLI skips a row with no requested price. Then only the test
   countries change; the copy matches the original
   everywhere else. Prices keep the CSV's own form, with a dot (`179.90`), never `179,90`.
   `set --file` reads the currency and requested price and ignores the synced and status
   columns.
5. **I preview the file** and show the user the prices it will set; the App Store rounds to its
   own price points here:

   ```bash
   $ADAPTY product-prices set --product <COPY_ID> --app <APP_ID> --file <FILE> --dry-run
   ```

   A row error saves nothing (exit 4): fix the rows and preview again, never work around an
   error. "Missing App Store credentials" or "Missing Play Store credentials" on every row is the
   store connection of step 3. On a yes, the same command without `--dry-run` and with
   `--wait --yes` saves the previewed prices (see "On a yes" below for what its exit codes mean).
6. **I build the paywall or flow copy** that sells the new product, through `flow-generator`.
7. **I set up the country segment** through `audiences`.
8. **I offer to set up the A/B test** ("From hypothesis to A/B test" in `SKILL.md`): the current
   paywall or flow on that placement against the copy's flow, on the country segment's audience,
   once the copy is `approved` and its flow is published.

## Adding a plan length

A new plan length is a new product, made as the copy in steps 1 to 3 of "Setting up a price A/B
test" (the create, the user's yes to the new store product ID, the push with its screenshot,
refusals and `store_status`), with these differences:

- **Its period is the new one,** its access level the one the paywall's other products unlock,
  and its title the plan's name ("Weekly"), unique among the subscriptions in the App Store group.
- **Its USD price is the user's to confirm before the create.** I propose one that keeps the plan
  ladder ("Setting the new price", step 4) and sits at the category's 50th percentile for that
  plan in the main market, in its currency and in USD. A lifetime plan has no index row and no
  ladder rule, so I ask the user for its price. The store derives every country's price from it;
  `product-prices set` changes them only when the user asks.
- **Google Play:** a new base plan on the app's existing subscription (`--store-product-id` from
  `product-groups list --store play_store --page-size 100`, a new `--android-base-plan-id`); a
  new subscription ID only when the app has none.
- **A lifetime plan** is a one-time purchase: a new store product ID in each store, with neither
  `--group-id` nor `--android-base-plan-id`.
- **A trial on it is the user's,** in the store after the push (`levers.md`, "By store"): the
  push sets no offer.

Then the flow copy that sells it, through `flow-generator`, and the A/B test as for any
hypothesis.

## Changing a live price

A winning price moves to the original product, or the user asks for a price change without a
test. When the user asked for the change, the A/B test on a copy is your first Next step and your
pick; this block follows as the alternative they can say yes to. Save only on an explicit yes to
this block, after a preview. "Go ahead" before the block was shown is not that yes.

1. **Save the product's CSV first** (`product-prices list --csv`) in the temporary directory:
   that is the rollback. Say where it is.
2. **Write only the changed countries** into a file with the same header: countries left out
   keep their price, and every row sent goes to the store again, changed or not. One country can
   go as `--country <CODE>` with `--app-store-price` and/or `--play-store-price` instead.
3. **Preview** it with `--dry-run` and put the previewed prices in the block. When the preview
   finds no difference, nothing is saved: tell the user the prices already are that.
4. **Existing subscribers keep their price** unless the user asks to move them
   (`--apply-to-existing-subscribers`). If they do, say what it means per store: on the App
   Store they move at renewal, with any consent handled by Apple; on Google Play they must
   accept the increase, and those who do not lapse.
5. **Say when it takes effect, per store in the change:** an approved App Store subscription two
   days after the save, one not yet approved at once; Google Play at once.

Shape of the ask (the form, not words to copy):

> I'll change the price of **Annual** (`com.app.annual`) on the App Store:
> - Brazil: R$ 149,90 → R$ 99,90
> - Mexico: MXN 649 → MXN 549
>
> New buyers pay it from two days after I save it; current subscribers keep their price. Nothing
> will measure whether it helped; an A/B test on a copy would. To undo it, I set those countries
> back from `annual.before.csv`. Shall I go ahead?

**On a yes:** `$ADAPTY product-prices set --product <PRODUCT_ID> --app <APP_ID> --file <FILE> --wait --yes`.
The user's yes to the block is the confirmation: without `--yes` the CLI stops with exit 6 and
saves nothing. It previews again, saves the previewed prices and waits up to two minutes while
the stores receive them (usually about a minute), then prints each saved row's status.

- **Exit 4 or 5 after "Saved":** the prices are saved; a row is `failed` or
  `subscribers_migration_failed`, printed with its reason, the sync could not be confirmed, or
  the network dropped during the wait.
  Read it with `product-prices list` before I report it; never save again to retry.
- **Exit 0:** nothing failed, which does not mean every row arrived. A row still `pending` when
  the wait ended is read again with `product-prices list` before I report it.

Report each changed country's result.
