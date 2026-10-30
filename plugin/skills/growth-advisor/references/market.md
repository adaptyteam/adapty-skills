# Market medians

Where the typical subscription app sits, from Adapty's State of Paywalls 2026: 78,000+ paywalls
from 30,000+ apps, App Store only, October 2025 to September 2026. Revenue is in USD after
refunds and before store fees. Most numbers are medians, computed
app by app so the largest apps do not skew them.

This file owns market medians and how often each kind of test wins. `evidence.md` owns the uplift
ranges from winning tests. When you use a number from here, name it as the market median from
Adapty's State of Paywalls 2026, except Renewals, Refunds and Trial or direct, which come from
Adapty's State of In-App Subscriptions 2026. Never call it the user's category average unless the row is for
their category, and never present a median as their target.

## Read this before comparing

- **Paywall view → paid is not install → paid.** The report counts conversion from paywall
  views. Compare it with the app's `view-paid` conversion (`diagnosis.md`), never with install →
  paid. It is rough: the report counts purchases within 30 days of a view, and the per-view
  onboarding and later-paywall rows under Timing are a different count from the Conversion table.
- **Trial → paid is comparable.** Use the app's `trial-paid` conversion.
- **The median is not the goal.** The top 10% convert 4-5× the median outside the US. Being at
  the median says the app is typical, not that it is done.
- **App Store only.** For a Google Play question, say there is no market median here.

## The full grid

`market-grid.csv`, next to this file, holds the report's own tables: one row per measure, plan,
region and category, with the median, the 25th, 75th and 90th percentiles, and for `view-paid`
the number of apps behind it. The headline numbers on this page come from it.

- **Measures:** `view-paid`, `view-trial` and `trial-paid` match the app's conversions of the same
  id. `trial-cancelled-1h` and `trial-cancelled-24h` are the share of trials with auto-renew
  turned off within an hour and a day; the CLI has no read that matches them, so they are context
  only.
- **Pick the row:**
  - the plan the rate is about (`Weekly`, `Monthly`, `Annual`), or `All plans` for the app's
    rate across plans;
  - the main market's region: `US` on its own, or `Europe`, `APAC`, `LATAM` or `MEA` by the
    main market's country; `All regions` when no market leads;
  - the app's App Store primary category when it is one of the eight (Education, Entertainment,
    Graphics & Design, Health & Fitness, Lifestyle, Photo & Video, Productivity, Utilities),
    `All categories` otherwise. The CLI does not show the category: use the one the user or the
    app's code names, else `All categories`, and say which row you used.

  ```bash
  grep '^trial-paid,Annual,US,' <skill>/references/market-grid.csv
  ```
- **An empty cell** means fewer than 20 apps qualified: step up to `All categories`, then
  `All plans`, and say so.
- **Grade a rate by its row:** below p25 is weak, above p75 strong, in between typical. Name the
  row in the reply ("the US median for annual plans in Photo & Video, 22.2%"), never the grade's
  cutoffs.

## Conversion

| Measure | Median | Notes |
|---|---|---|
| Paywall view → paid, US | 2.75% | Within 30 days |
| Paywall view → paid, Europe | 1.38% | About half the US |
| Top 10% start at | 3.30% (MEA) to 5.71% (Europe) | Above the typical US app in every region |
| Trial → paid, US | 26.2% | |
| Trial → paid, MEA | 15.1% | |
| Trial → paid, Health & Fitness | 19.8% (MEA) to 33.3% (US) | Highest of any category in every region |
| Paywall view → trial start, Health & Fitness | 1.46% (LATAM, MEA) to 2.93% (Europe) | Lowest category outside the US |

US paywall view → paid by category: Graphics & Design 3.50%, Education 3.28%, Lifestyle 3.20%,
Health & Fitness 2.86%, Entertainment 2.44%. Category ranks change by region; a US ranking does
not carry over.

## Plans

- **Revenue by plan length:** weekly 62%, annual 21%, monthly 12% overall. Weekly is 76% in LATAM
  and 50% in Europe. Health & Fitness gets 62% from annual; Utilities 90% from weekly. Judge an
  app's mix against its category, not the overall split.
- **Number of plan lengths:** 41% of apps offer one, 39% two, 20% three or more. Apps with two
  lengths convert 67% higher than apps with one. In A/B tests, adding products won only 53% of
  the time.
- **Preselection:** 90% of buyers keep weekly when it is preselected, 46% keep annual.
  Preselecting annual does not hurt conversion.
- **Lifetime:** 14% of apps offer it, and it brings 5.6% of revenue where sold.

## Trials

- 79% of trial starts are 1-3 days; 20% are 4-7 days.
- 32% of trials are cancelled within the first hour, 44% within 24 hours (55% in Europe, 40% in
  the US). Fewer early cancellations go with higher trial → paid.
- Longer trials get fewer day-one cancellations, but convert better only on monthly and annual
  plans. On weekly plans, 3-day trials do better.

## Renewals

`renewals.csv`, next to this file, holds the share of annual subscriptions that renew at the end of
their first year, from Adapty's [State of In-App Subscriptions
2026](https://adapty.io/state-of-in-app-subscriptions-report/): one rate per category, region and
start (after a trial, or a direct purchase). Name it as that report's, never as State of Paywalls.

- **Compare it with** the app's `paid-2period` rate for the annual plan over the last 12 months
  (`reads.py audit` prints it as "first renewal by plan length").
- **Pick the row:** the app's category when it is one of the eight, `All categories` otherwise;
  the main market's region (`North America` for the US), `All regions` when no market leads; and
  the start most of the annual plan's buyers have (read 4).

  ```bash
  grep '^Photo & Video,North America,after trial,' <skill>/references/renewals.csv
  ```
- **Grade it by the ratio:** under about two thirds of the row's rate is weak, over about one and a
  half times is strong, typical between. The file has no percentiles, so say the grade is rough.
- **Annual only.** First renewals of different plan lengths are not comparable: an annual plan's
  first renewal sits far below a weekly's or monthly's by nature. Never grade annual against the
  app's other plans.

## Refunds

`refunds.csv`, next to this file, holds the share of revenue lost to refunds, from the same State
of In-App Subscriptions 2026: one share per category, region and start (after a trial, or a direct
purchase).

- **Compare it with** the app's refunds as a share of its revenue over the same months: read 7's
  total over read 2's (`reads.py audit` prints the share).
- **Pick the row** as for Renewals: the category, the main market's region, and the start most of
  the app's buyers have.

  ```bash
  grep '^Lifestyle,Europe,direct,' <skill>/references/refunds.csv
  ```
- **Grade it by the ratio, lower is better:** over about one and a half times the row's share is
  weak, under about two thirds strong, typical between. The file has no percentiles, so say the
  grade is rough.
- A weak grade says how much money comes back, not why. Refunds concentrated in one market take
  the pricing sentence in `SKILL.md`; otherwise name no reason (`diagnosis.md`, the Refunds row).
- **A weak grade is a scorecard line and one "You:" Next step, never the bold answer or a
  hypothesis:** check that [Refund Saver](https://adapty.io/docs/refund-saver.md) is on in the
  dashboard. It answers Apple's questions about a refund request, and Google Play's about a
  chargeback, with how the user used the app, so unfair ones get disputed; the store still
  decides. The CLI cannot see whether it is on, so the step asks the user to check, and gives no
  expected cut in refunds.

  > You: check that [Refund Saver](https://adapty.io/docs/refund-saver.md) is on in the Adapty
  > dashboard. It answers the store's questions about each refund request with how the user used
  > the app, so unfair ones get disputed.

  (The shape of the step, not words to copy.)

## Trial or direct

`trials.csv`, next to this file, compares subscribers who started with a free trial with those who
paid at once, on the same plan length, from the same report. `trial_to_direct` is what a trial
starter brought in over their first year divided by what a direct buyer brought in: 2.00 means
trial starters were worth twice as much, under 1 means direct buyers were worth more.

- **Pick the row:** the category and region as for Renewals, and the plan length the trial is on
  or would go on. No row means one side had no data: step up to `All regions`, then
  `All categories`, and say so.

  ```bash
  grep '^Lifestyle,Europe,' <skill>/references/trials.csv
  ```
- **It is who stays, not what a trial adds.** Apps that use trials differ from apps that do not,
  so the ratio never becomes an Expected range or a gain in dollars. Say it as what happened in
  the market, in words and never the bare ratio: "in Lifestyle in Europe, weekly subscribers who
  started with a trial brought in about twice as much in their first year as those who paid at
  once" (2.06); 0.77 is "about a quarter less".
- **Where it counts** is `levers.md`, Trials: which length a trial goes on, and the Why of a trial
  hypothesis.

## Discounts

Six-month revenue per subscriber, against full price:

| Discount on the first payment | Revenue kept |
|---|---|
| Up to 30% off | 90% |
| 31-60% off | 70% |
| Over 60% off | 46% |

Discounted subscribers also renew less: 6.3 points below full price up to 30% off, 7.9 points at
31-60%, 10.5 points over 60% (same-app comparisons).

Offers work far better for win-back: 56% of returning subscribers who take an offer still pay
three months later, against about 1 in 10 new users who start with one. That is who stays among
the people who took an offer, not what an offer adds: never use it as an expected gain.

## Timing and placements

- 93% of first purchases happen within 24 hours of install, bringing 89% of first-90-day revenue.
- 60% of buyers purchase on the first paywall view, 15% on the second.
- Onboarding paywalls convert 0.85% of views against 0.23% for later paywalls: about $170 per
  1,000 views against $40.
- 7 in 10 paywall views happen after the first session, and subscriptions started there bring
  38% of revenue (48% in Lifestyle and Utilities, 47% of monthly revenue).
- Only 4% of apps show a second paywall right after the first is closed. Those convert at 0.88×
  the main paywall and beat it in 45% of apps. The typical discount there is 38%.
- 80% of apps use two or more paywalls; 44% use five or more.

## The close button

- 11% of apps have a paywall with no close button, but these are only 2% of paywall views, and
  57% of their views are in onboarding. An app that uses one tends to use it everywhere: in the
  median such app, 94% of its paywall views have no close button.
- Within the same app, a paywall with no close button starts 48% more trials (4.7% of views
  against 3.2%) and gets 33% fewer direct purchases (0.50% against 0.75%). Counting both, it
  does better in 57% of apps, so there is no general winner.
- 22% of apps delay the close button, usually by 3-5 seconds; 2% of delays run past 10 seconds.

## Testing

Share of A/B tests that increased each metric:

| Kind of change | Raised LTV | Raised conversion |
|---|---|---|
| Localization | 62% | |
| Trial | 60% | |
| Plan length | 59% | |
| Visual or copy | 35% | 31% |

- Change the offer before the look: localization, trials and plan lengths win more often than
  visual changes.
- The most active apps test often: among apps with 50K-500K monthly paywall views, the top
  quarter run 9+ tests a year; above 500K, 21+.
- Only 1 in 4 apps personalize paywalls by audience. Most who do split by country or language
  (61%), app version (44%) or platform (43%); 15% use their own user attributes and 6% the
  acquisition source.

## How paywalls look

From 100 main paywalls of well-known iOS subscription apps. These say what is common, not what
converts.

- 62% show two plans; 73% use plan cards; 67% preselect annual.
- 66% offer a free trial, and 83% of those name it in the button.
- 54% use no image; 27% show social proof; 48% use a feature checklist.
- 62% show the full annual price, 24% a monthly breakdown, 4% a weekly one. 41% use a "Save X%"
  badge, 16% a crossed-out price.
- The typical headline is 5 words; 79% use 6 or fewer.
- 2% of headlines use what the app knows about the user.
