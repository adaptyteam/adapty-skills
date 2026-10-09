# Diagnosis

The commands that answer each question, and how to read what they return. Every command here is
a read. Run them one at a time: `analytics chart` is sent once and never retried, and on a `429`
you wait `retry_after_seconds` and run it once more, never in a loop.

## Before the first chart

```bash
$ADAPTY apps list --json
$ADAPTY analytics charts --app <APP_ID> --json
$ADAPTY analytics values duration --app <APP_ID> --json
$ADAPTY analytics values country --app <APP_ID> --json
```

- Take chart ids, breakdowns and filters from `analytics charts`; each chart accepts only the
  breakdowns and filters its entry lists. Read it once per session.
- Take filter values from `analytics values`; pass the `value`, not the `label`.
- If `analytics charts` says the topic does not exist, try `npx --yes adapty@beta analytics
  charts --help` once. If that fails too, the user's CLI has no analytics yet: ask them for the
  numbers below from the dashboard's Analytics page, and say which ones you need.

Rules for reading any chart:

- `null` means the value cannot be computed. Never read it as zero, and never fill it in.
- Dates are whole days in the app's reporting timezone (`meta.query.timezone`). The last few days
  can still change as late store events arrive, so end the window a few days back.
- `meta.definitions` says what a value counts. Quote it when a number could be misread.
- A segment's `key` is the raw value to filter by; `title` is what the dashboard shows. Use
  titles when you write to the user.

## The audit reads

For an audit, read the last six full months at `--granularity month`. Set `FROM` and `TO` once.

```bash
# 1. New vs renewal revenue
$ADAPTY analytics chart revenue --app <APP_ID> --date-from $FROM --date-to $TO --segment-by renewal_status --json
# 2. Revenue by plan length: one call per value of `values duration`
$ADAPTY analytics chart revenue --app <APP_ID> --date-from $FROM --date-to $TO --filter duration=<value> --json
# 3. Installs by country
$ADAPTY analytics chart installs --app <APP_ID> --date-from $FROM --date-to $TO --segment-by country --json
# 4. New paid subscriptions, split by trial vs no offer
$ADAPTY analytics chart subscriptions_new --app <APP_ID> --date-from $FROM --date-to $TO --segment-by offer_category --json
# 5. New trials
$ADAPTY analytics chart trials_new --app <APP_ID> --date-from $FROM --date-to $TO --json
# 6. Endings, by reason
$ADAPTY analytics chart subscriptions_expired --app <APP_ID> --date-from $FROM --date-to $TO --segment-by cancellation_reason --json
# 7. Refunds
$ADAPTY analytics chart refund_money --app <APP_ID> --date-from $FROM --date-to $TO --json
```

```bash
# 8. Where purchases happen: by placement, then by paywall or flow
$ADAPTY analytics chart subscriptions_new --app <APP_ID> --date-from $FROM --date-to $TO --segment-by placement_id --json
$ADAPTY analytics chart revenue --app <APP_ID> --date-from $FROM --date-to $TO --segment-by paywall_id --json   # or flow_id
```

The segment `key` is the placement's, paywall's or flow's id; match it to the names from
`placements list`, `paywalls list` and `flows list`. This shows which placement and which screen
earn the money, and how much starts outside onboarding. It is a share, not a conversion rate:
the CLI has no paywall views. A flow also breaks down by `flow_screen_id`, which shows the
screen a purchase came from.

Then the top countries: chart 1 with `--filter country=<code>` for the largest three to five
countries by installs, and chart 4 with the same filter. Add `--filter store=<value>` to any of
these when the app sells on both stores and the question is about one of them.

What to compute from them, and how much to trust each:

| Number | From | Caveat to state |
|---|---|---|
| Install → paid | new subscriptions ÷ installs, same months | Same-period ratio, not a cohort |
| Trial uptake | new trials ÷ installs | Same-period ratio |
| Trial → paid | new subscriptions with a trial offer ÷ new trials, shifted by the trial length | Rough; a cohort chart in the dashboard is exact |
| Revenue per install | revenue ÷ installs, per country | Revenue includes renewals from older users |
| Share by plan length | each length's revenue ÷ total; same for new subscriptions | |
| Renewal share | renewal revenue ÷ total | |
| Country share | a country's revenue ÷ total | |
| Purchases in two weeks | new subscriptions ÷ 2 per month | Decides test size (`levers.md`) |
| Share by placement | a placement's new subscriptions ÷ total | Purchases, not a rate: no paywall views |

Then read the setup the numbers come from:

```bash
$ADAPTY placements list --app <APP_ID> --page-size 100 --json
$ADAPTY placements get <PLACEMENT_ID> --app <APP_ID> --json   # one per placement
$ADAPTY paywalls list --app <APP_ID> --json
$ADAPTY products list --app <APP_ID> --json
$ADAPTY flows list --app <APP_ID> --json
```

```bash
$ADAPTY segments list --app <APP_ID> --json
```

Segments are the app's own user groups. A chart accepts `--filter segment=<id>` and installs
break down by segment, so an existing segment can split any number in this file. The CLI cannot
create one.

From these: which placements exist and are active, what each one shows (a paywall or a flow, per
audience), which products each paywall sells, and whether there is anything after the onboarding
paywall. Prices and trials are set in the store, not in Adapty: take the app's own prices from its
App Store page (`competitors.md`, step 2) or ask the user.

## Follow the signal down

The audit reads find a symptom. Before you name a cause, split the biggest one until the split
stops changing the picture. Every chart but `installs` takes these breakdowns: `store`, `country`,
`duration`, `store_product_id`, `placement_id`, `paywall_id`, `flow_id`, `segment_id` and the
attribution ones (`attribution_channel`, `attribution_campaign` and the rest). `installs` breaks
down by `country`, `store` and `segment_id`, and takes attribution as a filter.

| Split | Command shape | What it tells you |
|---|---|---|
| Store | `--segment-by store` | Whether it is one platform. Test results differ by platform more often than not. |
| Channel | `trials_new` and `subscriptions_new` by `attribution_channel`, then `installs --filter attribution_channel=<value>` | Whether one channel's traffic converts far worse. Then it is traffic, not the paywall: say so and offer `adapty-attribution`. |
| When | `--granularity week` over the eight weeks around a change | The week it started, to match against a release, a price change or a campaign. |
| Who is leaving | `trials_renewal_cancelled` and `subscriptions_renewal_cancelled` by `duration`, `country` or `attribution_channel` | Who switched off renewal before revenue shows it. |
| Offers | `revenue` and `subscriptions_new` by `offer_id` | Whether an intro or win-back offer pays for itself. |
| Refunds | `refund_money` by `store_product_id` or `country`, against revenue for the same split | Purchases that come back. A win with heavy refunds is not a win. |
| Screen | `subscriptions_new --segment-by flow_screen_id` | Which screen of a flow the purchases come from. |

Stop when a split shows one value carrying the effect, or when two splits in a row change
nothing. Name the split that explained it in the reply, and the one that did not if the user would
have guessed it.

## Reading a flow

```bash
$ADAPTY flows config get <FLOW_ID> --app <APP_ID> --json > flow.json
```

The config is the flow's screens, copy and products. Before any claim about a screen:

- **Render it** with `flow-generator`'s preview recipe (`flows config preview`, then a
  screenshot). A render shows what users see, which the JSON cannot. Check it against the
  numbers yourself: a label the data disproves, a plan the paywall hides, a price typed as text.
- **For design hypotheses, hand the render to `paywall-teardown` or `onboarding-teardown`.** Never
  propose a layout, copy or visual change from your own reading.
- **Hand the config itself** to the teardown only when the preview cannot run, and say the screen
  was read from its config, not seen.

Chart 8 by `flow_screen_id` shows which screen of the flow the purchases came from. Never write
to the flow from this skill; a change is a copy (`levers.md`, Paywall design).

## "Why did revenue drop?"

1. Chart 1 (new vs renewal) over the drop and the months before it, at `month`, or `week` for a
   drop under two months.
2. **Renewals fell:** chart 6 by reason. Cancelled by the user points to the cohort that came up
   for renewal (a past promo, a price change, a weak acquisition month a year earlier for annual).
   Billing issues point to grace period and payment retries. Ask what changed then; the CLI shows
   neither releases nor store price history.
3. **New revenue fell:** chart 3 and chart 4. Installs down is traffic (`adapty-attribution` owns
   campaigns). Installs flat and new subscriptions down is the funnel or the paywall.
4. Split the falling side by country and by store before naming a cause. A drop in one country
   is a different story from the same percentage everywhere.

## "Should I change X?" (one idea)

Answer in three parts: the verdict (test it / a fair bet / skip it / already a strong default),
why (the user's numbers, then what `evidence.md` says, with the split if results were mixed), and
the one trap to avoid. Read only the charts the idea depends on:

| Idea | Charts |
|---|---|
| A price | chart 4 by `duration` filter, and the plan's share; competitor prices |
| A plan length | chart 2 and chart 4 per length |
| A trial | charts 4 and 5 |
| A country | charts 1 and 4 filtered to it, chart 3 |
| A new placement or offer | chart 8 by placement; the setup reads; ask where users hit limits in the app |
| A paywall or flow's design | chart 8 by paywall or flow, then the screen itself (`levers.md`, Paywall design) |

## "My test ended, what next?"

The CLI shows no A/B results. Ask, in one message: which test it was, which variant won (or
inconclusive), and roughly how many purchases each variant had. Then apply `levers.md`, "After a
test", and propose the next test for that placement.
