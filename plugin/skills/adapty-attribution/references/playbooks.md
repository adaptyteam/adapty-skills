# Attribution playbooks

One playbook per common question: when it applies, the calls, how to read them, and what the reply
leads with. Every call is read-only. `APP` is the app id from `$ADAPTY apps list`; dates are
`YYYY-MM-DD` in the app's reporting timezone, which every report echoes as `meta.query.timezone`.

| # | The user asks | Playbook |
|---|---|---|
| 1 | Which channel or campaign paid back best? Where should budget go? | [Payback and budget](#1-payback-and-budget) |
| 2 | Should we keep or kill this new campaign? | [Keep or kill a young campaign](#2-keep-or-kill-a-young-campaign) |
| 3 | Which campaigns bring trials that actually pay? | [Trial quality](#3-trial-quality) |
| 4 | How did last week go? Anything unusual? | [Weekly digest](#4-weekly-digest) |
| 5 | Which countries or stores should we push? | [Countries and stores](#5-countries-and-stores) |
| 6 | Which ads or ad sets are winning inside a campaign? | [Winners inside a campaign](#6-winners-inside-a-campaign) |
| 7 | Is some traffic refunding or churning? | [Low-quality traffic](#7-low-quality-traffic) |
| 8 | When will this campaign pay back? | [Predicted payback](#8-predicted-payback) |
| 9 | Meta, TikTok or Google says X, Adapty says Y | [Numbers that disagree](#9-numbers-that-disagree) |
| 10 | Installs dropped or are missing | [Installs dropped](#10-installs-dropped) |

## Reading any report

- `null` means the value cannot be computed, never zero. Leave it out of sums, averages and
  rankings, and say why it is missing.
- ROAS and rates are on a 0–100 scale: `roas` 150 is 150%, or 1.5x.
- Money is USD. The revenue basis defaults to `gross`; pass `--revenue-basis proceeds` when the user
  means money received after the store's cut, and name the basis beside every revenue figure.
- A `d{N}_` value is what the install cohort has done so far. Compare campaigns only at a horizon
  every cohort in the period has lived through.
- `rate_<event>` divides by installs. Trial-to-paid is `count_trial_converted` over
  `count_trial_started`, which you compute.
- A window is capped by its finest date grouping: 31 days by day, 180 by week, 366 by month or
  coarser, 92 with no date grouping. Too wide means a coarser grouping, not more calls.

## 1. Payback and budget

When: "which channel paid back best", "where should the extra budget go", "rank our campaigns".

```bash
$ADAPTY attribution report --app APP --date-from 2026-08-01 --date-to 2026-08-31 \
  --metrics spend,installs,cpi,total_revenue,roas,d7_roas,d30_roas --group-by channel \
  --revenue-basis proceeds --sort roas:desc --json
```

Then the same with `--group-by channel,campaign` to see which campaign drives each channel. For
the trend behind a channel, group by `date` with `--granularity week`.

Apple Search Ads rows have revenue and `null` spend. Get its numbers from Ads Manager and keep them
on their own line:

```bash
$ADAPTY asa whoami                       # is Apple Ads connected, and is there access?
$ADAPTY asa orgs list                    # the campaign group's currency
$ADAPTY asa metrics --entity campaign --date-from 2026-08-01 --date-to 2026-08-31 \
  --metric spend --metric roas --by-days 30 --order-by proceeds_roas --order-by-day 30
```

Reply: the ranking by ROAS on the named basis, the Apple Search Ads line labelled as Ads Manager
figures in their own currency, then the budget move. Recommend steps (for example raise a
campaign's budget weekly and stop when its D7 ROAS falls below a stated floor) rather than one
jump, because past spend says nothing about how a campaign behaves at a larger budget.

## 2. Keep or kill a young campaign

When: a campaign launched recently and someone wants to judge it on D30 or D90.

The youngest cohort has lived from `--date-to` to today. A campaign that started two weeks ago has
no D30 yet: its `d30_roas` is two weeks of revenue and will keep rising.

```bash
# the young campaign, only cohorts old enough for D7
$ADAPTY attribution report --app APP --date-from 2026-09-15 --date-to 2026-09-21 \
  --metrics spend,installs,cpi,d7_roas,d14_roas --group-by campaign --filter campaign=ID_NEW --json
# the benchmark campaign at the same horizons, on mature cohorts
$ADAPTY attribution report --app APP --date-from 2026-06-01 --date-to 2026-08-31 \
  --metrics spend,installs,cpi,d7_roas,d14_roas,d30_roas --group-by campaign --filter campaign=ID_OLD --json
# Adapty's forecast for the young campaign
$ADAPTY attribution report --app APP --date-from 2026-09-15 --date-to 2026-09-29 \
  --metrics spend,d30_predict_roas --group-by date --granularity day --filter campaign=ID_NEW --json
```

Reply: the verdict first ("too early for D30; at D7 it is ahead of X"), the matched-horizon
comparison, the prediction labelled as a prediction, and the date its first cohort reaches the
horizon the rule uses. If the rule's revenue basis is unstated, give the answer on both gross and
proceeds.

## 3. Trial quality

When: "which campaigns bring trials that never convert", "cost per paying user", "is TikTok's cheap
traffic any good".

```bash
$ADAPTY attribution report --app APP --date-from 2026-07-01 --date-to 2026-08-15 \
  --metrics spend,installs,count_trial_started,d14_count_trial_converted,cost_per_trial,d30_arpu,d30_roas \
  --group-by campaign --revenue-basis proceeds --json
```

End the period two weeks or more before today so every trial has had time to convert. Compute per
campaign: trial-to-paid (`d14_count_trial_converted` / `count_trial_started`) and cost per paying
trial (`spend` / `d14_count_trial_converted`).

Reply: the campaigns ranked by cost per paying trial, with the cheapest-per-install campaign called
out when it is not the cheapest per payer. This is what Adapty sees and an ad network cannot: which
trials turned into renewals.

## 4. Weekly digest

When: "how did last week go", "anything unusual", a recurring Monday report.

```bash
$ADAPTY attribution report --app APP --date-from 2026-08-31 --date-to 2026-09-27 \
  --metrics spend,installs,cpi,count_trial_started,cost_per_trial,d7_roas --group-by date,channel \
  --granularity week --json
```

Use full weeks. Compare the last week with the three before it per channel, and flag a move of 20%
or more in spend, installs, CPI or cost per trial. `d7_roas` is final only for cohorts at least 7
days old, so read it on the week before last.

Reply: one line per channel with a flag, then the one or two flags that need action, each with the
likely cause to check (a budget change, a new creative, a tracking change, a release).

## 5. Countries and stores

When: "where should we expand", "is Germany worth it", iOS vs Android.

```bash
$ADAPTY attribution report --app APP --date-from 2026-06-01 --date-to 2026-08-31 \
  --metrics spend,installs,cpi,d30_arpu,d30_roas --group-by country,channel --revenue-basis proceeds \
  --sort spend:desc --json
```

Use `--group-by store` for App Store vs Google Play. Countries filter by upper-case ISO codes
(`--filter country=US,GB`). Drop rows with too few installs to judge, and say where you drew the
line.

Reply: the countries worth more budget and the ones to cap, each with its CPI and D30 ROAS.

## 6. Winners inside a campaign

When: "which ads are working", "which ad set should we scale".

```bash
$ADAPTY attribution values --app APP --date-from 2026-08-01 --date-to 2026-08-31 --dimension campaign --json
$ADAPTY attribution report --app APP --date-from 2026-08-01 --date-to 2026-08-31 \
  --metrics spend,installs,cpi,ctr,count_trial_started,cost_per_trial,d7_roas \
  --group-by adset,ad --filter campaign=ID --sort cost_per_trial:asc --json
```

Not every channel reports keywords; run `values --dimension keyword` before grouping by `keyword`.

Reply: the top and bottom ads with spend large enough to trust, and which to pause or feed.

## 7. Low-quality traffic

When: refunds or chargebacks spike, "is this network sending bad users", fraud worries.

```bash
$ADAPTY attribution report --app APP --date-from 2026-07-01 --date-to 2026-08-31 \
  --metrics installs,payers,count_subscription_refunded,count_subscription_chargeback,d30_count_subscription_renewed,total_revenue \
  --group-by channel,campaign --json
```

Compute refunds and chargebacks per payer by campaign and compare with the app's average. A
campaign far above it is the one to check: low-quality inventory, a misleading creative, or a
promo that pulls in people who refund.

Reply: the campaigns above the app's average, by how much, and what to check first.

## 8. Predicted payback

When: "when will this pay back", "what's the LTV of these users", setting a CPI target.

```bash
$ADAPTY attribution report --app APP --date-from 2026-09-01 --date-to 2026-09-29 \
  --metrics spend,d7_revenue,d90_predict_roas,d180_predict_roas,d365_predict_roas \
  --group-by date,campaign --granularity day --json
```

Predictions need `--group-by date --granularity day`, at most two other dimensions, at most four
horizons, and N up to 365. A column of `null` predictions can mean the model did not run, not that
the value is low: report the realized value, say the prediction is unavailable, and try later.

Reply: the predicted ROAS at each horizon, labelled as predicted, and the first horizon where it
passes 100%. For a CPI target: the predicted revenue per install at the chosen horizon is the most
a campaign can pay per install and break even.

## 9. Numbers that disagree

When: an ad network's dashboard says one ROAS or install count and Adapty says another.

Pull the same campaign, period and basis from Adapty first, then go through the causes in this
order:

1. **Units and basis.** Adapty's ROAS is a percent (113.5 is 1.14x); networks usually show a
   multiple. Adapty defaults to gross; show gross, proceeds and net side by side.
2. **Who gets credit.** A network credits its own clicks within its window and, by default for
   Meta, views within a day, and adds modeled conversions on iOS. Adapty gives each install to one
   source through the tracking link and its matching windows. Users Adapty assigns to organic or
   another channel can still count in the network's number.
3. **What value the network receives.** It counts the value of the events Adapty sends. If trial
   starts are sent with a value, the network books revenue for trials that never pay. Point the
   user to their campaign configuration's events mapping and revenue override in the dashboard.
4. **Dates.** Adapty groups by install date; a network usually reports by conversion or click
   date, so a period in one covers some users from the neighbouring period in the other.
5. **Duplicates.** Another tool sending purchases to the same pixel doubles the network's count.

Reply: neither number is simply wrong; say what each measures, which to use for budget (Adapty's,
on proceeds) and which for comparing ads inside the network (the network's), plus the one setting
to check. Useful pages: [Meta Ads](https://adapty.io/docs/ua-facebook.md),
[TikTok for Business](https://adapty.io/docs/ua-tiktok.md),
[Google Ads](https://adapty.io/docs/ua-google-ads.md), [Metrics](https://adapty.io/docs/ua-metrics.md).

## 10. Installs dropped

When: installs fall or never appear, on one channel or all of them.

```bash
$ADAPTY attribution report --app APP --date-from 2026-09-08 --date-to 2026-09-28 \
  --metrics spend,clicks,clicks_attributed,installs --group-by date,channel --granularity day --json
```

Read the pattern:

| Pattern | Most likely cause |
|---|---|
| Every channel, organic too, from one day | The app stopped registering installs. Check the release that went out that day: from SDK 4.1, Attribution is off until the app enables it ([iOS](https://adapty.io/docs/migration-to-ios-sdk-41.md), [Android](https://adapty.io/docs/migration-to-android-sdk-41.md)). The code change belongs to the `adapty-integration` skill |
| One channel; spend and clicks steady, `clicks_attributed` near 0 | The ads no longer go through the tracking link, or the link was edited or re-generated and not re-copied into the ads |
| One channel; spend stops too | The network connection expired or the campaigns were paused; check the integration in the dashboard |
| Web purchases never appear | A test-mode payment key, or the click id not attached to the purchase: [Stripe](https://adapty.io/docs/ua-stripe.md), [Paddle](https://adapty.io/docs/ua-paddle.md) |

Reply: the pattern you see with dates and numbers, the cause it points to, and the check that
confirms it.
