# Levers and hypotheses

How to turn what the numbers say into hypotheses: the order you look in, the rules for each
lever, the known hypothesis types, how to write the reasoning, and what a finished test rules out.
Impact ranges are never stated here. Take every range from `evidence.md`, or label the
hypothesis untested.

## The shape every hypothesis has

A hypothesis is complete only when it fills all of these. A known type (table below) fills most
of them for you; a hypothesis outside the table fills them itself.

| Field | What goes in it |
|---|---|
| Title | The action, with the user's real values: "Add 3-day trial to annual $39.99". Use the type's template when it has one, a plain sentence otherwise. |
| Target | What it changes: a product, a plan length, a country, a paywall or a placement. |
| Why | 2-3 sentences from the user's own numbers, problem first. See "Writing the why". |
| Pattern | 1-2 sentences on the market pattern or user behaviour behind it. No prices. Said when the user picks the test or asks why, not in the audit. |
| Rests on | The numbers it depends on, and where each came from: the CLI, the user, or a competitor's App Store page. |
| Judged on | The one metric that decides the winner. |
| Rules out | What a win and what a loss take off the table (see "After a test"). |
| Expected | A range from `evidence.md`, or "untested". |
| How to run it | "I can build it" (a flow, A/B tested or shown on a placement), "I can set it up" (a segment's audience on a placement), or "you do it in the dashboard", with exact values. |

## Known hypothesis types

| Type | Title template | Judged on | After a win, rule out | After a loss, rule out |
|---|---|---|---|---|
| Price up | Increase [weekly/monthly/annual] to $X.XX | Revenue per user, with an eye on conversion | Price down on that product | Price up on that product |
| Price down | Decrease [weekly/monthly/annual] to $X.XX | Revenue per user | Price up on that product | Price down on that product |
| Add a plan length | Add [weekly/monthly/annual] at $X.XX | Purchase conversion and revenue per user | Removing that length | Adding that length |
| Remove a plan length | Remove [weekly/monthly/annual] $X.XX | Revenue per user | Adding that length back | Removing that length |
| Swap a plan length | Replace [length] with [length] at $X.XX | Purchase conversion and revenue per user | The reverse swap | This swap |
| Add a trial | Add [N]-day trial to [length] $X.XX | Trial conversion and trial-to-paid together | Adding it again | Adding it on that product |
| Move a trial | Move trial from [length] to [length] | Trial conversion and trial-to-paid together | Every trial test on that paywall | This move |
| Change trial length | Change trial on [length] from [N] to [M] days | Trial conversion and trial-to-paid together | This change | This change |
| Geo price | [Country]: [Increase/Lower] [length] by X% | Revenue per user in that country | Further geo tests on that country and product | Geo on that country and product |
| Follow-up offer | Show a discount when the [placement] paywall closes | Revenue per user across the placement | This offer on that placement | This offer on that placement |
| Seasonal paywall | Run a [event] paywall from [date] to [date] | Revenue in the window | — (re-run next season) | That design for that event |
| New placement | Show a paywall at [moment] | Purchases from that placement, and total revenue | — | That moment |
| Localization | Translate [placement] paywall into [language] | Revenue per user in that language's countries | That language on that paywall | That language on that paywall |
| Paywall design | Free text, from `paywall-teardown` | Purchase conversion | That change on that paywall | That change on that paywall |
| Onboarding change | Free text, from `onboarding-teardown` | Conversion to purchase | That change on that flow | That change on that flow |

A rule-out is keyed to its target. Raising the annual price and losing rules out raising the
annual price; it says nothing about raising the monthly one. A ruled-out idea is not deleted: say
it was tried recently, and it can come back after about a year or when the app's situation
changes.

## Where to look first

1. **Split revenue before reading it.** For any question about a drop or a trend, split revenue
   into new users and renewals first. New-user revenue down points to traffic, the funnel or the
   paywall. Renewal revenue down points to an older change hurting renewals, such as a cohort that
   stopped renewing after a plan or price change. Never diagnose from total revenue alone.
2. **Conversion against revenue per user.** Use install → paid and revenue per install (see
   `diagnosis.md`). Compare the app against its own past, and against `market.md` only where the
   measure is the same (trial → paid, prices, plan mix; never install → paid against a paywall
   conversion):
   - conversion fine, revenue per user low → price and plan structure
   - conversion low, revenue per user low → plan structure and the paywall itself
   - both fine → geo pricing, plan mix and placements
3. **Context that changes the answer.**
   - How many products the paywall sells. One and two-or-more call for different first moves.
   - What was tested before. Ask; the CLI has no test history. A recent loss is off the table.
   - App size. Under about 200 purchases in two weeks, a test takes weeks to settle: recommend
     fewer, bolder changes, and say a small tweak will not reach a clear result.
4. **Priority.** The offer before the look: localization, trials, plan structure and price
   win more often than visual changes (`market.md`, Testing). Then the paywall design, then
   small tweaks. A
   missing core plan length is fixed before any price test. Geo pricing runs in parallel and
   never blocks the main track. One test per placement at a time, 2-4 weeks each.

If the user does not want to touch prices, a design or geo test is a fair lower-risk start. Say
so; do not push.

## Plan structure

- The core lengths are weekly, monthly and annual. Weekly plus annual is the most common pair.
- **One product on the paywall:** add a second length first; nothing can be optimised without a
  comparison. Then that length's price, then the original price, then a trial if the category
  uses one.
- **Two or more products:** find the leading length (by LTV if the user has it, otherwise by
  revenue share) and push purchases toward it: the trial on it, preselected, a badge, the price
  ratio.
- **Four or more products:** simplify to three before anything else.
- **Removing a length** is a candidate only when both hold: it earns under 30% of the paywall's
  revenue, and fewer than half of the confirmed competitors offer it. A length both the app and
  its competitors offer is anchored: fix its price, never remove it.
- "Remove X and add Y" is one swap test, not two.
- 2-, 3- or 6-month plans only when at least half the confirmed competitors offer that exact
  length, and only as a swap. Never invent one.
- A lifetime option next to annual is a legitimate test (see `evidence.md`).

## Prices

- The direction comes from two comparisons for the same plan length: the app's conversion, and
  its price against the confirmed competitors' average.
  - converts well and is cheaper or level → raise
  - converts poorly and is more expensive → lower toward the average
  - level on both → leave price alone; use a structure or design test
- Compare against the competitors' average, never one expensive outlier.
- No competitor price for a plan length → no price recommendation for it. Never justify one
  length's price with another length's competitors.
- Two price changes in one test are fine on different lengths, never on the same length.
- A plan length with under 5% of purchases: raising its price moves nothing. Lower it, or
  restructure.
- Iterate. Raised and conversion held → raising again is fair. Lowered and conversion did not
  grow → roll back.
- A conversion drop of around half is a loss even when revenue per user rose.

## Trials

- End state: at most one product carries a trial.
- A competitor's trial marks their main plan, so the trial's place follows the competitors. No
  competitor signal → the longest length.
- A trial that exists is changed (its length) or moved (to another length). Removing a trial
  outright is a test only where trial-to-paid is very low; see `evidence.md`.
- Testing a trial on two different lengths is two tests run one after the other.

## Geo pricing

- Only after the base prices are settled.
- A country is worth a geo test when it holds roughly 20% or more of revenue. 10-20% is
  borderline: say so rather than deciding.
- If one market holds 50% or more of revenue, treat it as the main market for the whole audit.
- Decide per country from its install → paid against the app's overall rate. Purchasing-power
  data is not available here; say the decision rests on conversion alone.
- Raising prices tends to win in high-income markets and lose elsewhere (`evidence.md`). Small
  apps price by tier (tier 1 = x, tier 2 = 0.8x, tier 3 = 0.6x); large apps per country.

## Placements and flows

These are the hypotheses this skill can build: a flow, put in front of users by an A/B test, a new placement, or a change to an existing one (`SKILL.md`, "Changing a live placement").

- **A healthy set is about three placements:** the onboarding paywall (push annual), an in-app
  paywall at a value moment (a limit hit, a locked feature, settings), and an offer after the
  onboarding paywall closes.
- **Only one placement** is itself an opportunity. A large share of revenue outside onboarding
  (chart 8 in `diagnosis.md`) calls for a dedicated paywall at that moment.
- **Follow-up offer:** a discounted second screen when the onboarding paywall closes. Well
  evidenced after the onboarding paywall, and it loses after the main in-app paywall
  (`evidence.md`, across the flow).
- **Escalating discounts** over days after a close, and **a higher first price with a later
  "special offer" at the target price,** are growth-team estimates with no A/B evidence here:
  label them untested.
- **A separate in-app paywall:** simpler than the onboarding one, fewer plans, shown at value
  moments.
- **Seasonal paywall:** a real event with a real deadline. A countdown is fine here because the
  deadline is real; on a standing paywall it is fake urgency and raises refunds.
- **Paywall after a short goal quiz,** and **a free taste of the product before the paywall**
  (for games and creative tools): onboarding changes, routed to `onboarding-teardown`.

## Localization

The kind of test that wins most often (`market.md`). A candidate when installs or revenue from
countries in another language are a large share and the paywall shows one language. The CLI
shows which countries the users are in, not which languages the paywall has; check the paywall
or ask. A flow paywall gets its locales from `flow-generator`, which this skill can run.

## Paywall design

Design hypotheses come from the teardown skills, not from your own reading of the screen:
invoke `paywall-teardown` on a paywall (the render, or the config when you have no render) and
`onboarding-teardown` on a multi-screen flow, in their audit direction. Take back at most one
design test, its pattern and its range, and rank it with the others. If neither skill is
installed, say design was not reviewed and suggest installing them.

- **Missing Restore, Terms or Privacy on a paywall is not a side topic.** Say it in one line and
  offer `flow-audit`, which checks a flow before it reaches paying users. Order of leverage: copy and imagery, then structure
(comparison table, badge, preselected plan), then button details. Discounts and timers only when
the offer is real.

- **Which flow:** the one that brings the most purchases first; a placement that brings almost
  none is a question about the moment it shows, not only about its screen.
- **A change to a live flow is a copy.** Offer: "I can build this as a copy of your flow and you
  A/B test it against the current one." `flow-generator` builds the copy as a new flow. Never
  edit the live flow in place: every user gets the change, and nothing measures it.
- **A paywall from the old Paywall Builder** cannot be copied this way. Offer the dashboard's
  **Move to new builder** first ([convert a paywall to a flow](https://adapty.io/docs/convert-paywall-to-flow.md)),
  then the copy.
- **Say what it rests on:** the teardown's reading of the screen and the evidence library, not
  this app's conversion per screen, which the CLI does not have.

## After a test

- **The user decides the winner.** You cannot see A/B results through the CLI; ask which variant
  won. Inconclusive counts as a loss.
- **Check it was a test first.** Roughly 200 purchases per variant. Stopped after a few days or
  a few dozen purchases → inconclusive, not a loss; do not change the plan because of it.
- **Judge by type** (table above). A price test on conversion alone is the commonest misread.
- **Rule out by target** (table above), then propose the next test on that placement.
- After adding a plan length, suggest checking in a couple of months that its buyers renew.
- When price tests stop producing lifts, say further price tests will likely return little, and
  move to another lever. Never invent rounds to fill a plan.

## Writing the why

- Use the user's own prices and numbers ("$59.99", "4% of revenue").
- Problem first, in their setup; then the reason it matters.
- Two numbers side by side, never "baseline": "Brazil converts at 0.4% against your 1.5%
  overall".
- "Your competitors" means the apps the user confirmed. A market median from `market.md` is named
  as one, never as their competitors and never as their category unless it is that category's row.
- The action is already in the title: no "we recommend", no "therefore".
- Different countries or products get different text.
- The pattern sentence carries no prices and does not repeat the why.

Shape of a good why (an example of the form, not words to copy):

> Your weekly plan ($6.99) brings in 4% of revenue from about 24 purchases a month, so changing
> its price cannot move the total. Annual carries the paywall, and it shares the trial with
> weekly.

Weak: "Your conversion is low and your price is high, therefore we recommend lowering it." No
numbers, no app, and a "therefore".
