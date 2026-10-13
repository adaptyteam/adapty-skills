# Diagnosis

The commands that answer each question, and how to read what they return. Every command here is
a read. Run them one at a time: all analytics calls of one app share a limit of 2 requests per
second, a data command is sent once and never retried, and on a `429` you wait
`retry_after_seconds` (in the `--json` error) and run it once more, never in a loop.

## Before the first read

```bash
$ADAPTY apps list --json
$ADAPTY analytics catalog --app <APP_ID> --json
$ADAPTY analytics values --app <APP_ID> --dimension duration --json
$ADAPTY analytics values --app <APP_ID> --dimension country --json
```

- `analytics catalog` lists the six operations (`chart`, `conversion`, `funnel`, `retention`,
  `ltv`, `cohort`) with their options, every chart id and conversion id, and the groupings and
  filters each one accepts. Read it once per session. Take groupings and filter keys from it: they
  differ per chart and per operation (`installs` takes no purchase filters, for example).
- Each grouping names its `filter`: the filter key that selects one of its groups. To drill into
  a group, pass `--filter <that filter>=<the group's key>`. `null` means that grouping has no
  drill-down. The filter is not always the grouping's own name.
- Take filter values from `analytics values`; pass the `value`, not the `label`.
- If `analytics catalog` says the command does not exist, try `npx --yes adapty@beta analytics
  catalog --help` once. If that fails too, the user's CLI has no analytics yet: ask them for the
  numbers below from the dashboard's Analytics page, and say which ones you need.

Rules for reading any answer:

- Every data command answers in one shape: `data.value` is the number of the whole period,
  `data.segments` starts with the total (`is_total` true, `key` null), then one segment per group.
- `null` means the value cannot be computed (an LTV period the cohort has not reached, a cohort
  that cannot be predicted). Never read it as zero, and never fill it in. `segments: []` means no
  data for that window, which is not the same as zeros.
- Dates are whole days in the app's time zone (`meta.query.timezone`). The last few days can
  still change as late store events arrive, so end the window a few days back.
- A segment's `key` is the raw value to filter by; `title` is what the dashboard shows. Use
  titles when you write to the user. The "No Data" group is a real group: the zero UUID for an id
  grouping, `no_offer` for offers, `Uncategorized` for duration, `""` for text.
- Exit 2 is a bad flag (nothing was sent; the message names it), exit 3 is no token or no access
  to the app, exit 4 is a server refusal: an unknown chart, conversion, grouping or filter. On 4,
  re-read the catalog instead of guessing another name.
- `chart` and `conversion` take a compared period (`--compare-from`, `--compare-to`), answered in
  `data.compare`. The funnel, retention, LTV and cohort cannot compare; run them twice instead.
- For the funnel and retention, read a group's number from the grouped answer. The same query
  filtered to that group can give a different number (a `0` becomes `null`, a `no_offer` group
  loses its paid steps). Charts agree both ways.

The conversion ids, as the dashboard titles them:

| Id | Pair |
|---|---|
| `install-trial`, `install-paid` | Install → Trial, Install → Paid |
| `view-trial`, `view-paid` | Paywall view → Trial, Paywall view → Paid |
| `trial-paid` | Trial → Paid |
| `paid-2period`, `2period-3period`, `3period-4period`, `4period-5period` | Each renewal step |
| `paid-6month`, `paid-1year`, `paid-2year` | Paid → still paying after 6, 12, 24 months |
| `billing-issue-paid`, `grace-period-paid` | Recovered after a billing issue or a grace period |

## The audit reads

For an audit, read the last six full months at `--granularity month`. Set `FROM` and `TO` once.

```bash
# 1. New vs renewal revenue
$ADAPTY analytics chart --app <APP_ID> --chart revenue --date-from $FROM --date-to $TO --group-by renewal_status --json
# 2. Revenue by plan length
$ADAPTY analytics chart --app <APP_ID> --chart revenue --date-from $FROM --date-to $TO --group-by duration --json
# 3. Installs by country
$ADAPTY analytics chart --app <APP_ID> --chart installs --date-from $FROM --date-to $TO --group-by country --json
# 4. New paid subscriptions, split by trial vs no offer
$ADAPTY analytics chart --app <APP_ID> --chart subscriptions_new --date-from $FROM --date-to $TO --group-by offer_category --json
# 5. New trials
$ADAPTY analytics chart --app <APP_ID> --chart trials_new --date-from $FROM --date-to $TO --json
# 6. Endings, by reason
$ADAPTY analytics chart --app <APP_ID> --chart subscriptions_expired --date-from $FROM --date-to $TO --group-by cancellation_reason --json
# 7. Refunds
$ADAPTY analytics chart --app <APP_ID> --chart refund_money --date-from $FROM --date-to $TO --json
```

```bash
# 8. Where purchases happen: by placement, then by paywall or flow
$ADAPTY analytics chart --app <APP_ID> --chart subscriptions_new --date-from $FROM --date-to $TO --group-by placement_id --json
$ADAPTY analytics chart --app <APP_ID> --chart revenue --date-from $FROM --date-to $TO --group-by paywall_id --json   # or flow_id
```

The segment `key` is the placement's, paywall's or flow's id; match it to the names from
`placements list`, `paywalls list` and `flows list`. This shows which placement and which screen
earn the money, and how much starts outside onboarding. A flow also breaks down by
`flow_screen_id`, which shows the screen a purchase came from. On its own it is a share of
purchases, not a conversion rate: see 9 for the rate.

```bash
# 9. Conversion rates: one call per pair (install-trial, trial-paid, install-paid, view-paid)
$ADAPTY analytics conversion --app <APP_ID> --conversion <CONVERSION_ID> --date-from $FROM --date-to $TO --granularity month --json
# 10. The funnel from install on, by store
$ADAPTY analytics funnel --app <APP_ID> --date-from $FROM --date-to $TO --group-by store --json
# 11. Retention of subscribers by plan length (add --use-trial to count from the trial)
$ADAPTY analytics retention --app <APP_ID> --date-from $FROM --date-to $TO --group-by duration --json
# 12. LTV by plan length
$ADAPTY analytics ltv --app <APP_ID> --date-from $FROM --date-to $TO --group-by duration --json
# 13. Conversion per placement: one call per active placement
$ADAPTY analytics conversion --app <APP_ID> --conversion view-paid --date-from $FROM --date-to $TO --filter placement_id=<PLACEMENT_ID> --json
```

A conversion answer's `data.value` is the rate in percent, `value_to` of `value_from`; if the
window has none, `meta.recommended_period` can name one that has. `view-paid` and `view-trial`
are the conversion rate of a paywall: filter them with `--filter paywall_id=<id>` (or
`placement_id`, `flow_id`), one call per paywall, or group them by it when the catalog lists that
grouping for conversions. Compare paywalls only inside one placement: a paywall shown at
onboarding and one shown on a feature limit see different users. An LTV
point the cohort has not reached is `null`: compare lengths only at a point every one of them
reached. `analytics cohort` gives revenue per install cohort with a prediction; read it when the
question is whether a recent month's users are worth less.

Then the top countries: chart 1 with `--filter country=<code>` for the largest three to five
countries by installs, and chart 4 with the same filter. Add `--filter store=<value>` to any of
these when the app sells on both stores and the question is about one of them.

What to compute from them, and how much to trust each:

| Number | From | Caveat to state |
|---|---|---|
| Install → paid, trial uptake, trial → paid | read 9 | The dashboard's own rate; name the pair |
| Conversion per paywall | read 9 with `view-paid`, filtered per paywall | Compare inside one placement only |
| Conversion and views per placement | read 13: `value` and `value_from` | Ranks placements (`levers.md`) |
| Where users drop | read 10, the step with the largest fall | |
| Revenue per install | revenue ÷ installs, per country | Revenue includes renewals from older users |
| Share by plan length | each length's revenue ÷ total; same for new subscriptions | |
| Leading length | read 12 at a period every length reached; read 11 for why | |
| Renewal share | renewal revenue ÷ total | |
| Country share | a country's revenue ÷ total | |
| Purchases in two weeks | new subscriptions ÷ 2 per month | Decides test size (`levers.md`) |
| Share by placement | a placement's new subscriptions ÷ total | Purchases, not a rate: the rate is the row above |

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

Segments are the app's own user groups. Group by `segment_id`, or drill into one with the
filter the catalog names for that grouping, so an existing segment can split any number in this
file. The CLI cannot
create one.

From these: which placements exist and are active, what each one shows (a paywall or a flow, per
audience), which products each paywall sells, and whether there is anything after the onboarding
paywall. Trials are set in the store, not in Adapty: read which products carry one from chart 4
by `store_product_id`, or ask the user. Prices are out of scope; do not look them up.

## Follow the signal down

The audit reads find a symptom. Before you name a cause, split the biggest one until the split
stops changing the picture. `--group-by` takes one grouping that the catalog lists for that
chart or operation: usually `store`, `country`, `duration`, `store_product_id`, `placement_id`,
`paywall_id`, `flow_id`, `segment_id` and the attribution ones (`attribution_channel`,
`attribution_campaign` and the rest). `installs` has fewer; the catalog says which.

| Split | Command shape | What it tells you |
|---|---|---|
| Store | `--group-by store` | Whether it is one platform. Test results differ by platform more often than not. |
| Channel | `trials_new` and `subscriptions_new` by `attribution_channel`, then `installs --filter attribution_channel=<value>` | Whether one channel's traffic converts far worse. Then it is traffic, not the paywall: say so and offer `adapty-attribution`. |
| When | `--granularity week` over the eight weeks around a change | The week it started, to match against a release, a price change or a campaign. |
| Before and after | `chart` or `conversion` with `--compare-from`/`--compare-to` set to the same length before the change | How much moved, in one call. |
| Where in the funnel | `funnel` by the split that moved, against the total | Which step the split loses users at. |
| Who is leaving | `trials_renewal_cancelled` and `subscriptions_renewal_cancelled` by `duration`, `country` or `attribution_channel` | Who switched off renewal before revenue shows it. |
| Offers | `revenue` and `subscriptions_new` by `offer_id` | Whether an intro or win-back offer pays for itself. |
| Refunds | `refund_money` by `store_product_id` or `country`, against revenue for the same split | Purchases that come back. A win with heavy refunds is not a win. |
| Screen | `subscriptions_new --group-by flow_screen_id` | Which screen of a flow the purchases come from. |

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

Read 8 by `flow_screen_id` shows which screen of the flow the purchases came from. Never write
to the flow from this skill; a change is a copy (`levers.md`, Paywall design).

## "Why did revenue drop?"

1. Chart 1 (new vs renewal) over the drop and the months before it, at `month`, or `week` for a
   drop under two months.
2. **Renewals fell:** chart 6 by reason. Cancelled by the user points to the cohort that came up
   for renewal (a past promo, a change to the plans, a weak acquisition month a year earlier for
   annual). Billing issues point to grace period and payment retries: `billing-issue-paid` and
   `grace-period-paid` say how many are recovered. Read the renewal-step conversions
   (`paid-2period` and on) by `duration`, read 11 and `analytics cohort` to find the cohort that
   renews worse. Ask what changed then; the CLI shows no release
   history.
3. **New revenue fell:** chart 3 and chart 4. Installs down is traffic (`adapty-attribution` owns
   campaigns). Installs flat and new subscriptions down is the funnel or the paywall: read 9 with
   a compared period and read 10 to find the step that fell.
4. Split the falling side by country and by store before naming a cause. A drop in one country
   is a different story from the same percentage everywhere.

## "Should I change X?" (one idea)

Answer in three parts: the verdict (test it / a fair bet / skip it / already a strong default),
why (the user's numbers, then what `evidence.md` says, with the split if results were mixed), and
the one trap to avoid. Read only what the idea depends on (numbers are the audit reads):

| Idea | Reads |
|---|---|
| A plan length | chart 2 and chart 4 per length, read 12 |
| A trial | charts 4 and 5, read 9 (trial pairs), read 11 with and without `--use-trial` |
| A country | charts 1 and 4 filtered to it, chart 3 |
| A new placement or offer | chart 8 by placement; the setup reads; ask where users hit limits in the app |
| A paywall or flow's design | read 8 by paywall or flow, `view-paid` for that paywall, then the screen itself (`levers.md`, Paywall design) |

## "My test ended, what next?"

The CLI shows no A/B results. Ask, in one message: which test it was, which variant won (or
inconclusive), and roughly how many purchases each variant had. Then apply `levers.md`, "After a
test", and propose the next test for that placement.
