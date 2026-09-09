# Apple Search Ads — Metrics and Analytics

No `asa` command takes `--app` to pick which account you are in — the token's company
already fixes that. `--app` appears here in two other roles: a list filter on
`search-terms list` (the full filter set is in `asa-management.md`), and an aggregation
scope on `asa metrics`.

`asa metrics` takes three scope flags — `--app`, `--campaign`, `--ad-group`, each a
repeatable UUID from the matching list. They are not list filters: they narrow the set of
entities the server aggregates, which is the one thing that makes a call cheap, since cost
follows the number of entities aggregated and not the page size. There is no
`--campaign-group`, no `--search` and no `--status` on it.

`asa metrics overview` still takes no scope flag at all. It answers at the account's
`--entity` level for the window you give it; narrow that answer by matching the returned
rows against ids from a scoped list in `asa-management.md`, not by looking for a flag that
isn't there.

`asa-management.md`'s `list` and `get` commands return metadata only — no spend, no ROAS,
no counts of any kind. Every number comes from the commands in this file. To count entities
instead of reading their numbers — "how many active campaigns do I have" — skip metrics
entirely: every list response carries `meta.pagination.count`; pass `--page-size 1` and read
that field.

## Commands

| Command | Flags | Notes |
|---|---|---|
| `asa metrics` | `--entity`, `--date-from`, `--date-to`, `--metric` (repeatable) all **required**; `--app` / `--campaign` / `--ad-group` (repeatable UUIDs, see [Scoping a metrics call](#scoping-a-metrics-call)), `--group-by` (repeatable), `--order` (`asc`/`desc`, default `desc`), `--order-by`, `--by-days` (repeatable, max 16), `--order-by-day`, `--page` (default `1`), `--page-size` (default `100`, max `1000`) optional | One row per entity — `ad`, `ad-group`, `campaign`, or `keyword` — already aggregated over the period and already sorted server-side by `--order-by`. A top-N question is one call, `--order-by X --page-size N`; never paginate and sum yourself, and for a full breakdown take one big page (`--page-size 1000`) instead of looping. `--order` defaults to `desc`; pass `--order asc` for a "worst" question instead of "best." `--group-by` is one of `country`, `day`, `month`, `quarter`, `week`, `year`, and its coarseness sets the date-window cap (see [Date window caps](#date-window-caps)). A page is capped at **5000 breakdown rows** — entities × countries × periods, not the row count you asked for — and over it the call fails `422 cli_response_too_large`; coarsen the grouping, narrow the window, or scope it, rather than reaching for a smaller `--page-size` and looping. Account-level totals are one call to `metrics overview` instead. |
| `asa metrics overview` | `--entity`, `--date-from`, `--date-to` required; `--metric` (repeatable, root names only, and **optional here** — unlike on `asa metrics`, omitting it returns every metric), `--by-days` (repeatable, max 16), `--period-unit` (`day`/`week`/`month`/`quarter`/`year`, default `day`) optional | Returns one response, not a list — totals for the whole entity level plus a per-period series in the same call, no pagination, no client-side summing. That's the one-call answer to a trend question ("today vs. yesterday," "this week vs. last"). Has no `--group-by` and no `--order`/`--order-by`/`--order-by-day`. Shares the 5-per-minute metrics budget with `metrics` (see [The analytics pool](#the-analytics-pool)). Metric names here are root names only — see [Metric vocabulary](#metric-vocabulary). |
| `asa search-terms list` | `--date-from` / `--date-to` (default: today); scope with `--ad-group` / `--campaign`; `--page` (default `1`), `--page-size` (default `100`, max `1000`) | The only list command in the `asa` topic that takes period flags — it draws on the same analytics pool as `metrics` (see [The analytics pool](#the-analytics-pool)), not the metadata store the other lists use. The full scope-filter set (`--app`, `--campaign-group`, `--search` included) is in `asa-management.md`. This file covers *reading* search terms; turning what you find into keywords or negative keywords is in `asa-management.md`. |
| `asa competitors summary` | `--app-ids` (1–5 Apple App Store IDs, comma-separated) | Covers the last full month across every country — there are deliberately no period or country flags. The first call on a cold cache can take tens of seconds. |

## Scoping a metrics call

`asa metrics` takes `--app`, `--campaign` and `--ad-group`, each repeatable and each a UUID
from the matching list command. They are not filters over a printed page: they cut down the
set of entities the server aggregates, and aggregation cost follows that set, not
`--page-size`. Scoping is therefore the cheapest way to make any metrics call fast, and the
first thing to reach for when one is slow or trips the 5000-row page cap.

Two consequences worth separating:

- **Some metrics are refused unscoped.** `subscribers` and `paid_subscribers` — and `arppu`
  and `arpas`, which derive from them — count unique profiles per entity and cost roughly
  seventeen times the rest. Whatever `--entity` you ask for, the call is refused unless
  `--campaign` or `--ad-group` scopes it. `--app` alone does not satisfy this.
- **Every metric you name is computed over the whole entity set.** `--metric` is required
  precisely so that this is a choice rather than a default: ask for the columns you will
  actually read, not for everything.

```sh
$ADAPTY asa metrics --entity keyword --date-from 2026-07-01 --date-to 2026-07-31 \
  --metric arpas --campaign <campaign-uuid>
```

`asa metrics overview` has none of these flags, and none of this applies to it.

## Date window caps

Both commands cap the date window by how coarse the call's period grouping is, but the two
caps are **not** the same table — `asa metrics` is stricter at day grain:

| Grouping | `asa metrics` (`--group-by`) | `asa metrics overview` (`--period-unit`) |
|---|---|---|
| `day` | 28 days | 90 days |
| no period grouping | 90 days | — |
| `week` | 180 days | 180 days |
| `month`, `quarter`, `year` | 365 days | 365 days |

"No period grouping" is a `metrics` call with no `--group-by` at all, and also one grouped
only by `country` — `country` is not a period, so it does not tighten the window. `metrics
overview` always has a period unit, so it has no such row.

A window too wide for the grouping you asked for is fixed by coarsening that flag, never by
splitting the request into more calls — a year of data is one call at `--group-by month` (or
`--period-unit month`), not four 90-day calls. A 90-day question grouped by day is the case
this catches most often: on `metrics` it needs `--group-by week`, or no grouping at all.

## Metric vocabulary

`--metric` and `--order-by` take the dashboard's own metric names — never invent or guess
one. A wrong name fails the call with an error that lists every valid name, so probing for
names costs at most one call and should never be done on purpose. On `asa metrics`
`--metric` is required, and everything you name is computed over the whole entity set — name
the columns you will read, not the whole vocabulary.

Cohort roots — `revenue`, `arpu`, `arppu`, `arpas` (alias `cohort_arpas`), `roas`, `roi` —
expand to `gross_`, `proceeds_`, and `net_` variants (`gross_roas`, `proceeds_revenue`,
`net_arpu`, and so on). To rank by a cohort metric with `--order-by`, use the expanded name
— `--order-by gross_roas`, not `--order-by roas`. There is no `ltv` metric; see [Cohort
windows](#cohort-windows).

`metrics overview` accepts the root names only (`revenue`, `roas`, `arpu`, …) — no
`gross_`/`proceeds_`/`net_` variants, and no keyword-only names.

**Apple spend metrics:** `spend`, `local_spend`, `impressions`, `taps`, `ttr`, `avg_cpt`,
`avg_cpm`, `ipm`, `total_installs`, `total_new_downloads`, `total_redownloads`,
`tap_installs`, `tap_new_downloads`, `tap_redownloads`, `view_installs`,
`view_new_downloads`, `view_redownloads`, `total_avg_cpi`, `total_install_rate`,
`tap_install_cpi`, `tap_install_rate`.

**Adapty attribution metrics:** `adapty_installs`, `trials_started`, `trials_converted`,
`subscriptions_started`, `non_subscriptions`, `paid`, `conversion`, `paid_subscribers`,
`subscribers`, `adapty_install_cr`, `trial_cr`, `trials_converted_cr`,
`subscriptions_started_cr`, `non_subscriptions_cr`, `paid_cr`, `conversion_cr`,
`cost_per_adapty_install`, `cost_per_trial`, `cost_per_trials_converted`,
`cost_per_subscriptions_started`, `cost_per_non_subscriptions`, `cost_per_paid`,
`cost_per_conversion`.

**Cohort (revenue) metrics**, per gross/proceeds/net: `gross_revenue`, `proceeds_revenue`,
`net_revenue`, and the same triple for `arpu`, `arppu`, `arpas`, `roas`, `roi`.

**The four expensive ones:** `subscribers`, `paid_subscribers`, and the `arppu` and `arpas`
families that derive from them. They cost roughly seventeen times the rest and `asa metrics`
refuses them unless `--campaign` or `--ad-group` scopes the call — see [Scoping a metrics
call](#scoping-a-metrics-call).

**Keyword-only:** `rank`, `search_popularity`, `impression_midpoint`.

## Cohort windows

The single most misunderstood part of the surface: there is no `ltv` metric. Lifetime value
is a cohort metric read at a renewal window, so `--by-days` is how you ask for a day-7 or
day-90 value.

- `--by-days` is repeatable, at most 16 windows per call, on both `metrics` and `metrics
  overview`. Omit it entirely to get the dashboard's default figures instead of cohort
  values.
- `--order-by-day` ranks rows by one of those windows — the way to get top campaigns by
  day-90 ROAS in a single call. Its value must be one of the windows passed to `--by-days`.
- Ranking by a cohort metric takes the expanded name — `--order-by gross_roas`, not
  `--order-by roas` — see [Metric vocabulary](#metric-vocabulary).

```sh
$ADAPTY asa metrics --entity campaign --date-from 2026-07-01 --date-to 2026-07-31 \
  --metric roas --by-days 7 --by-days 90 --order-by gross_roas --order-by-day 90
```

## The analytics pool

Four commands draw on one 2-concurrent-query pool per company: `metrics`, `metrics
overview`, `search-terms list`, and `competitors summary`. A slot held by one is a slot the
others can't use. On top of that shared concurrency, each pair also carries its own
per-minute budget:

| Commands | Per-minute budget |
|---|---|
| `metrics`, `metrics overview` | 5/min, burst at most 2 per 10s |
| `search-terms list`, `competitors summary` | 30/min |

Three 429 codes, not one:

- `cli_analytics_busy` — the 2-concurrent pool is full; wait about 5 seconds.
- `cli_rate_limit_exceeded` — the per-minute window (5/min or 30/min, whichever pair) is
  full.
- `cli_cooldown_active` — stop entirely; tell the user when to retry.

Every refusal carries the wait in `Retry-After`. The CLI already absorbs the first 429 of
any single command on its own — it waits the exact `Retry-After` (up to 60s; cool-downs
excluded) and retries once. So a 429 that reaches you is the *second* attempt failing: the
budget is genuinely exhausted for now. Don't loop on it — cut the number of calls in the
plan, or tell the user when to retry.

20 rejections within 5 minutes put the token — not the whole company — into an escalating
cool-down: `cli_cooldown_active`, 5m → 30m → 3h. Retrying during the pause does not extend
it; the fix is calling less, not retrying harder.

These limits are specific to the four commands above. They do not apply to the management
commands in `asa-management.md` — campaigns, ad groups, ads, keywords, negative keywords,
product pages, creatives, automations all run outside this pool. `asa keywords list` looks
like it belongs here (it's the heaviest metadata read in the topic) but runs on its own,
separate 2-concurrent pool with its own 30/min budget — documented in `asa-management.md`,
shared with nothing in this file.
