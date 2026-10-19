# Diagnosis

The commands that answer each question, and how to read what they return. Every command here is
a read. Run them one at a time: each analytics command allows 2 requests per second per app (and
360 per minute across everyone calling it), a data command is sent once and never retried, and
over a limit it exits 4 with the wait as `retry_after_seconds` in the `--json` error. Wait that
long and run it once more, never in a loop.

## Before the first read

```bash
$ADAPTY apps list --page-size 100 --json
$ADAPTY analytics catalog --app <APP_ID> --json
$ADAPTY analytics values --app <APP_ID> --dimension duration --json
$ADAPTY analytics values --app <APP_ID> --dimension country --json
```

- `apps list` is paged: when `meta.pagination.pages` is above 1, read every page before saying
  an app is not in the account. Never run `apps get`: it prints the app's secret key.
- `analytics catalog` lists the six operations (`chart`, `conversion`, `funnel`, `retention`,
  `ltv`, `cohort`) with their options, every chart id and conversion id, and the groupings and
  filters each one accepts. Read it once per session. Take groupings and filter keys from it: they
  differ per chart and per operation (`installs` takes no purchase filters, for example).
- To narrow a read to one group, take the filter key from the catalog and the value from
  `analytics values --dimension <key>`, matched to the group by its title. A group's `key` is not
  a filter value; never pass it to `--filter`.
- Take filter values from `analytics values`; pass the `value`, not the `label`. A value is sent
  exactly as written, spaces included; an empty one (`--filter country=`) selects the "No Data"
  group.
- If `analytics catalog` says the command does not exist, try `npx --yes adapty@beta analytics
  catalog --help` once. If that fails too, the user's CLI has no analytics yet: ask them for the
  numbers below from the dashboard's Analytics page, and say which ones you need.

Rules for reading any answer:

- Every data command answers in one shape: `data.value` is the number of the whole period,
  `data.segments` starts with the total, then one segment per group. Tell the total from a group
  by `is_total` alone: a group's `key` can be null too.
- `null` means the value cannot be computed (an LTV period the cohort has not reached, a cohort
  that cannot be predicted). Never read it as zero, and never fill it in. `segments: []` means no
  data for that window, which is not the same as zeros.
- Dates are whole days in the app's time zone (`meta.query.timezone`). The last few days can
  still change as late store events arrive, so end the window a few days back.
- A segment's `key` is the raw value the backend gives for the group; `title` is what the
  dashboard shows. Use titles when you write to the user. The "No Data" group is a real group, and
  its key can be `null`, `""`, `"None"` or the zero UUID. A funnel group's key is its title and can
  repeat: keep each group as its own row.
- Exit 2 is a bad flag (nothing was sent; the message names it), exit 3 is no token or no access
  to the app, exit 4 is a server refusal: an unknown chart, conversion, grouping or filter. On 4,
  re-read the catalog instead of guessing another name.
- `chart` and `conversion` take a compared period (`--compare-from`, `--compare-to`), answered in
  `data.compare`. The funnel, retention, LTV and cohort cannot compare; run them twice instead.
- For the funnel and retention, read a group's number from the grouped answer. The same query
  filtered to that group can give a different number (a `0` becomes `null`, a `no_offer` group
  loses its paid steps). Charts agree both ways.
- Two reads differ from the dashboard on purpose. The funnel applies a `cancellation_reason`
  filter, which the dashboard's funnel ignores, so with that filter its numbers will not match the
  dashboard. Retention groups by the backend's list of groupings, which is not the dashboard's, so
  take retention groupings from the catalog, never from the dashboard's menu. Say so when the
  user compares a number with what they see there.

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
Run every read below, 11 and 12 included: retention and LTV are what tell a plan that sells from a
plan that pays.

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
# 6. Endings, by reason, then the same per store when the app sells on both
$ADAPTY analytics chart --app <APP_ID> --chart subscriptions_expired --date-from $FROM --date-to $TO --group-by cancellation_reason --json
$ADAPTY analytics chart --app <APP_ID> --chart subscriptions_expired --date-from $FROM --date-to $TO --group-by cancellation_reason --filter store=<VALUE> --json
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
# 13. Conversion per placement: one call per active placement, the value from `analytics values --dimension placement_id`
$ADAPTY analytics conversion --app <APP_ID> --conversion view-paid --date-from $FROM --date-to $TO --filter placement_id=<VALUE> --json
```

A conversion answer's `data.value` is the rate in percent, `value_to` of `value_from`; if the
window has none, `meta.recommended_period` can name one that has. `view-paid` and `view-trial`
are the conversion rate of a paywall: filter them by `paywall_id` (or `placement_id`, `flow_id`)
with a value from `analytics values`, one call per paywall, or group them by it when the catalog lists that
grouping for conversions. Compare paywalls only inside one placement: a paywall shown at
onboarding and one shown on a feature limit see different users. An LTV
point the cohort has not reached is `null`: compare lengths only at a point every one of them
reached. `analytics cohort` gives revenue per install cohort with a prediction; read it when the
question is whether a recent month's users are worth less.

Then the main market and the top countries:

```bash
$ADAPTY analytics chart --app <APP_ID> --chart revenue --date-from $FROM --date-to $TO --group-by country --json
```

The main market is the country with the most revenue; the top countries are the three to five
that hold most of it. Read chart 2, chart 4 and read 9 filtered to each (`--filter
country=<value>`): which plans sell there, how its conversion moved over the window, and where it
loses users. Read each country against its own past, not against the US or another country
("Before you state a conclusion"). The main market decides which country's stakes come first and
which region's median applies (`market.md` has US, Europe, MEA and LATAM rows where the report
gives them; say when it has none). Name the main market in the reply when it is not the US. Add
`--filter store=<value>` to any of these when the app sells on both stores and the question is
about one of them.

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

Segments are the app's own user groups. Group by `segment_id`, or filter to one with a value
from `analytics values --dimension segment_id`, so an existing segment can split any number in
this file. A new segment is created through `audiences`, on the user's yes.

From these: which placements exist and are active, what each one shows (a paywall or a flow, per
audience), which products each paywall sells, and whether there is anything after the onboarding
paywall. Trials are set in the store, not in Adapty: read which products carry one from chart 4
by `store_product_id`, or ask the user. Prices are out of scope; do not look them up.

## What the app already tried

Read this in every audit; the user will rarely tell you. Use 12 months, not six.

```bash
# Paywalls and flows week by week, one call per active placement
$ADAPTY analytics chart --app <APP_ID> --chart subscriptions_new --date-from $FROM12 --date-to $TO --granularity week --group-by paywall_id --filter placement_id=<VALUE> --json
# (or --group-by flow_id for a flow placement)
# Offers over time
$ADAPTY analytics chart --app <APP_ID> --chart subscriptions_new --date-from $FROM12 --date-to $TO --granularity month --group-by offer_id --json
# Products over time
$ADAPTY analytics chart --app <APP_ID> --chart subscriptions_new --date-from $FROM12 --date-to $TO --granularity month --group-by store_product_id --json
```

| What you see | What it means |
|---|---|
| Two paywalls or flows selling on one placement in the same weeks, then one stops | A past A/B test. The one still selling is the one they kept; say "kept", not "won". |
| One paywall stops and another starts the same week | A change they made and kept. |
| A paywall or flow in `paywalls list` / `flows list` that no placement shows | Something tried and dropped. Its name often says what it tried. |
| A product with purchases earlier and none lately | A plan or trial they dropped. |
| An offer with purchases in one stretch only | A past promo or intro offer, and when it ran. |
| Audiences and segments on placements now | Targeting they already do. |

Say it as facts with the dates, and say what the data cannot show: the winner of a test whose
variants both stopped, and ideas they discussed but never ran.

Then sort what you found by kind of change, from `paywalls list` (which products each paywall
sells):

| Kind | How it shows |
|---|---|
| Visual or copy | Two paywalls that sell the same products |
| Plan set | Two paywalls that sell different products, or a product added or dropped |
| Trial or offer | A product with a trial added or dropped; an offer that ran |
| Localization | Not visible in the numbers; read the paywall or ask |
| Placement or audience | A placement or audience that appeared or went |

Name the kinds the app has never tried, with how often each wins (`market.md`, Testing): an
app that has only ever changed the look has its likelier wins in kinds it has not touched.
Knowing what was tried is enough; you do not need the winner for this.

## Before you state a conclusion

Most wrong answers come from a true number compared with the wrong thing. Check each claim
against these before it goes in a reply:

- **One window and one baseline for the whole reply.** When the user names a period ("the last
  couple of months"), that is the window. "Held", "the same as before" and "fell" each compare the
  same two periods as every other number in the reply, at the same granularity. Never disprove
  the user's premise with a different period: if they say traffic held since summer, check
  summer, not January.
- **Date a change from the data, not from your window.** When you find a break, read the series
  back to a stable stretch: 12 months at month grain, then week grain around each step. A drop
  often comes in steps; name every step with its date. The start of the window you happened to
  read is not when anything started.
- **Split by channel before you blame the product.** A rate that falls because a channel that
  converted well stopped sending traffic is a change of mix, not a broken paywall or release.
  Read the rate by `attribution_channel` and check whether it fell inside a channel whose traffic
  held. Say which part of the fall is mix and which part happened inside a channel.
- **"Everywhere" needs every group checked.** Before saying a fall is in all stores, countries or
  channels, read each large one; name the exceptions.
- **Countries are read against their own past.** Prices and buying power differ by market, so
  a country's conversion or revenue per install is not ranked against the US or against another
  country. What a country's numbers mean: its trend over the window, which plans sell there, and
  where its funnel loses users. Call a market healthy only from its own trend.
- **A market median is compared on its own slice.** The State of Paywalls numbers are App Store
  only and per region: filter the app's read to `store=app_store` and to that region's countries
  before putting the two side by side.
- **A retention or LTV period is the plan's billing period** (point 6 of a weekly plan is six
  weeks), and a cohort younger than a plan's period cannot show its renewals.

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
| Offers | `revenue` and `subscriptions_new` by `offer_id`, then the same filtered to that offer and grouped by `country` and `store` | Whether an intro or win-back offer pays for itself, and where: an offer that loses money overall can still pay in some countries. |
| Refunds | `refund_money` by `store_product_id` or `country`, against revenue for the same split | Purchases that come back. A win with heavy refunds is not a win. |
| Screen | `subscriptions_new --group-by flow_screen_id` | Which screen of a flow the purchases come from. |

Stop when a split shows one value carrying the effect, or when two splits in a row change
nothing. Name the split that explained it in the reply, and the one that did not if the user would
have guessed it.

### From a split to a segment

A group that carries the effect can become the target of a hypothesis (`levers.md`, Segments).
Some analytics splits have a segment field, so the group can be targeted as you read it:

| Analytics split | Segment field |
|---|---|
| `store` | `store` |
| `attribution_channel`, `_campaign`, `_adgroup`, `_adset`, `_creative`, `_source`, `_status` | `channel`, `campaign`, `ad_group`, `ad_set`, `creative`, `source`, `status` |
| `country` | `store_country` or `ip_country`. Analytics uses the store country where it is known and the IP country otherwise, so neither matches it exactly; `audiences` asks which one |
| `segment_id` | the segment itself |

Plan length, offer, renewal period and the placement, paywall and flow ids have no segment field:
they describe a purchase, not a user.

Many segment fields have no analytics split: subscription state, paid access level, total
revenue, app version (current or on install), language, platform, OS, device, age, gender, how
long ago the user installed, and custom attributes. To read numbers for such a group, the segment
has to exist:

1. **Look for it first** in `segments list`; `segments get` shows its filters.
2. **Otherwise offer to create it** through `audiences`, on the user's yes, and say why: "to see
   how former subscribers convert, I need a segment for them." The CLI cannot delete a segment;
   the user can, in the dashboard, while no placement or A/B test uses it.
3. **Read it.** `segments get` returns `profile_count`. Filter any read with
   `--filter segment_id=<id>` (the value from `analytics values --dimension segment_id`). A new
   segment applies to past events within about a minute, so it splits the last six months at once.
   Charts can also group by `segment_id`; the funnel and conversions only filter, one call per
   segment.

How the past is judged differs by field. Paid access level, total revenue, the subscription's
product and its expiration date are today's values, applied to every past event: a user who paid
last week counts as a payer in January too. Country, app version, language, device, install date
and custom attributes are as they were at each event. Say so when it changes the reading.

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

1. Chart 1 (new vs renewal) over the period the user means and the months before it, at
   `month`, or `week` for a drop under two months. The bold answer names the side that carries
   most of the fall; when it is renewals, say plainly that the paywall is not the main cause.
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
