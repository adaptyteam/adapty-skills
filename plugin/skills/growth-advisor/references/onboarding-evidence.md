# Onboarding and flow evidence

The public measurements behind an onboarding or flow hypothesis: what is measured, what is a
vendor's claim, and what is untested. `evidence.md` owns the uplift ranges of its own library;
this file owns the onboarding and flow figures that it does not hold. Open it with `evidence.md`
when the hypothesis changes the steps before a paywall or the flow around it (`levers.md`,
"The step that loses users"). Each entry has a label and a public link; say which it is.

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
- **Sign-up after a first lesson:** moving account creation to after the first lesson raised
  daily active users by about 20% in one randomized test of a learning app.
  [A growth lead's interview on A/B testing](https://review.firstround.com/the-tenets-of-a-b-testing-from-duolingos-master-growth-hacker).
  **Measured, randomized.** The metric is daily active users, not purchases, and it is one test:
  directional for activity, silent on conversion.
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
| Sign-up later | The only figure is on daily active users, not on purchases |
| A permission prompt after the value screens | No measured effect on purchases |
| An opt-in trial | No measured effect on purchases |
| A multi-page paywall | No measured effect on purchases |

## How to use it

- Expected for an onboarding or flow hypothesis is "untested", or a figure above with its
  label. The about +20% and about +30% are single results: a direction for the Why, never an
  Expected number or range (`SKILL.md` allows a range only).
- A figure on daily active users is not a figure on purchases: say which one it is.
- The metric, the guardrails and the dollars are in `levers.md`, "The step that loses users".
- Never name the app or company behind a result.
