# Onboarding and flow evidence

The public measurements behind an onboarding or flow hypothesis: what is measured, what is a
vendor's claim, and what is untested. `evidence.md` owns the uplift ranges of its own library;
this file owns the onboarding and flow figures that it does not hold, and the benchmarks a flow's
funnel is set against. Open it with `evidence.md` when the hypothesis changes the steps before a
paywall or the flow around it (`levers.md`, "The step that loses users"), and when reading a
flow's funnel (`diagnosis.md`, "Where users leave it: the funnel", read 5). Each entry has a
label and a public link; say which it is.

## The onboarding benchmarks

`onboarding-grid.csv`, next to this file, holds the data tables of Adapty's
[State of Onboarding 2026](https://adapty.io/state-of-onboarding/report/): onboarding flows built
with Adapty, App Store only, November 2025 to October 2026, medians computed app by app, with the
25th, 75th and 90th percentiles where the report gives them. **Measured.** Name it as the median
from Adapty's State of Onboarding 2026, with its region and category. A row exists only where 10
or more apps qualified: with no region × category row, use the category row, then the region row,
and say which you used.

**Only for an onboarding: screens before the first paywall.** Teams call a paywall "onboarding"
(a placement, a flow or a paywall named so), and a paywall is not an onboarding. Use these rows
only when the funnel shows at least one screen with `screen_type` `onboarding` before its first
paywall step, or, with no account, when the screenshots or the code show screens before the
paywall. A flow whose first step is the paywall, or a placement that shows a paywall alone, is
a paywall: none of these rows applies, say so, and read it as a paywall (`market.md` for its
views, `paywall-teardown` for the screen).

Columns: `measure`, `region` (a region, `All regions`, or a country), `category`, `length`
(screens: `1-5`, `6-10`, `11-20`, `21+`, or `All`), `step` (a screen number for `screen-drop`, a
plan for `trial-paid` and `trial-cancelled-24h`), `median`, `p25`, `p75`, `p90`. Rates are in %,
revenue in USD.

| Measure | What it counts | Set the funnel's… against it |
|---|---|---|
| `user-saw-paywall-1d` | Users who saw a paywall within a day of their first open | Paywall reach: the first paywall step's `reached` over `summary.entered` |
| `user-completed` | Users who reached the last screen, across sessions | Nothing in a flow with a paywall inside it (a closed paywall is a drop-off there); the reach of the last screen in a flow with none |
| `user-trial-30d`, `user-paid-30d` | Users who started a trial, or paid, within 30 days of their first open (paid = a direct purchase or a trial conversion) | Trials and purchases over `entered`, read on a period that ended 30 days or more ago |
| `screen-drop` | Of the sessions that reached screen N, the share that ended there (`step` 1 to 10, then `11-20` as the average per screen) | Each step's `drop_off_rate` before the first paywall |
| `left-screen-1`, `left-mid-flow`, `left-second-to-last` | Where users leave, by flow length | The same, for a flow of that length |
| `completion-per-open`, `trial-per-open`, `paid-per-open`, `revenue-per-open` | Per onboarding open, for regions, categories, countries and lengths | Context only: the funnel counts users, not opens. `revenue-per-open` is gross and includes renewals; the funnel's revenue is first purchases only, so never set one against the other |
| `trial-paid`, `trial-cancelled-24h` | Trials started by users who saw an onboarding: converted, or auto-renew off within 24 hours | The app's `trial-paid` conversion for those users |
| `screens`, `seconds-to-complete`, `revenue-per-paid` | The flow's length in screens, its time, revenue per new subscriber | Context for a length hypothesis |

How a number places: below p25 weak, p25 to median below typical, median to p75 above typical,
above p75 strong, at p90 or more top 10%. For a drop rate the order flips: above p75 is the weak
end. The funnel counts users and the drop tables count sessions, so a user-based drop reads a
little low; a step above the session p75 is still a leak.

What the report says alongside the grid, all **Measured**, from the same link:

- **Length goes with revenue, not causally.** Flows of 21+ screens earn $1.39 per open against
  $0.36 for 1–5, and their trials convert about 30% against 19.7%, but long flows are mostly Health
  & Fitness and Education, which sell differently. A length change is tested, never predicted.
- **Completion and paying run opposite ways.** Health & Fitness completes the fewest opens and
  sells the most; Utilities the reverse; the US completes least of any region and pays most. Low
  completion alone is not a weak part.
- **Ad users finish more.** In the same apps, users from ads complete 5 points more often than
  organic users; Meta users 10.7 points more and convert 1.19 points better within 30 days; Apple
  Search Ads users finish more and convert the same. The first screen continues the ad.
- **Few apps keep the answers.** 19% of apps save a new user attribute during the onboarding (41%
  of apps with 10,000+ onboarding opens a month), so most show every user the same paywall.
- **Most apps never test the onboarding.** 56.5% used one onboarding variation all year. Of
  onboarding tests, 72.7% find a clear winner on completion and 16.2% on paid conversion; the median
  variation collects 43 paid conversions, so "no winner" usually means too few purchases.

Labels: **Measured** is a count or a test run by someone who published the method.
**Vendor claim** is a result a seller reports about its own customer, with no method to check.
**Untested** is a lever with no figure here.

## What is known

- **Most trial starts come on the first day.** About 90% of trial starts happen on the day of
  install, in a 2025 count over more than 16,000 apps.
  [Adapty, State of In-App Subscriptions](https://adapty.io/state-of-in-app-subscriptions-report/).
  **Measured.** It puts most trial starts in the first session's flow. It is a share of starts,
  not what any change in the flow will add.
- **The onboarding paywall against a later one** converts at a different rate per view. The
  figures are in `market.md` ("Timing and placements"), which owns them: do not restate them. It
  is a per-view rate across placements, not a per-user rate in a funnel and not what moving a
  paywall does, so never set it against a funnel number.
- **An onboarding rewrite** (value up front, shorter, testimonials) raised purchase conversion
  by about 30% in 11 days for one travel app.
  [Adapty case study](https://adapty.io/case-studies/travel-app/).
  **Vendor claim, bundled changes:** several changes at once, one app, a short window. It cannot
  say which change worked; use it as a direction, never as a range.

## Untested

No figure here, so Expected is "untested" for each:

| Lever | Why untested |
|---|---|
| The paywall earlier or later in the flow | No test of moving it within a flow; the placement figures in `market.md` compare different paywalls, not one paywall moved |
| Sign-up later | No measured effect on purchases |
| A permission prompt after the value screens | No measured effect on purchases |
| An opt-in trial | No measured effect on purchases |
| A multi-page paywall | No measured effect on purchases |

## How to use it

- The benchmarks place the flow and name the step that is out of line; they are never an
  Expected. A median says where typical apps are, not what a change will add.
- Expected for an onboarding or flow hypothesis is "untested", or a figure above with its
  label. The about +30% is a single vendor claim: a direction for the Why, never an Expected
  number or range (`SKILL.md` allows a range only).
- The metric, the guardrails and the dollars are in `levers.md`, "The step that loses users".
- Never name the app or company behind a result.
