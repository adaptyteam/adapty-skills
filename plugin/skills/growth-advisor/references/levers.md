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
| Title | The action, with the user's real values: "Add 3-day trial to annual". Use the type's template when it has one, a plain sentence otherwise. |
| Target | What it changes: a product, a plan length, a country, a paywall or a placement. |
| Why | One sentence about this app only: where, what you saw, how the change acts on it. See "Writing the why". |
| Pattern | 1-2 sentences on the market pattern or user behaviour behind it. Said when the user picks the hypothesis or asks why, not in the audit. |
| Rests on | The numbers it depends on, and where each came from: the CLI or the user. |
| Judged on | The one metric that decides the winner. |
| Rules out | What a win and what a loss take off the table (see "After a test"). |
| Expected | A range from `evidence.md`, or "untested". |
| How to run it | "I can build it" (a flow, A/B tested or shown on a placement), "I can set it up" (a segment's audience on a placement), or "you do it in the dashboard", with the steps. |

## Known hypothesis types

| Type | Title template | Judged on | After a win, rule out | After a loss, rule out |
|---|---|---|---|---|
| Add a plan length | Add [weekly/monthly/annual] | Purchase conversion and revenue per user | Removing that length | Adding that length |
| Remove a plan length | Remove [weekly/monthly/annual] | Revenue per user | Adding that length back | Removing that length |
| Swap a plan length | Replace [length] with [length] | Purchase conversion and revenue per user | The reverse swap | This swap |
| Add a trial | Add [N]-day trial to [length] | Trial conversion and trial-to-paid together | Adding it again | Adding it on that product |
| Move a trial | Move trial from [length] to [length] | Trial conversion and trial-to-paid together | Every trial test on that paywall | This move |
| Change trial length | Change trial on [length] from [N] to [M] days | Trial conversion and trial-to-paid together | This change | This change |
| Follow-up offer | Show a discount when the [placement] paywall closes | Revenue per user across the placement | This offer on that placement | This offer on that placement |
| Seasonal paywall | Run a [event] paywall from [date] to [date] | Revenue in the window | — (re-run next season) | That design for that event |
| New placement | Show a paywall at [moment] | Purchases from that placement, and total revenue | — | That moment |
| Localization | Translate [placement] paywall into [language] | Revenue per user in that language's countries | That language on that paywall | That language on that paywall |
| Paywall design | Free text, from `paywall-teardown` | Purchase conversion | That change on that paywall | That change on that paywall |
| Onboarding change | Free text, from `onboarding-teardown` | Conversion to purchase | That change on that flow | That change on that flow |

A rule-out is keyed to its target. Adding a trial to annual and losing rules out a trial on
annual; it says nothing about a trial on monthly. A ruled-out idea is not deleted: say
it was tried recently, and it can come back after about a year or when the app's situation
changes.

## Where to look first

1. **Split revenue before reading it.** For any question about a drop or a trend, split revenue
   into new users and renewals first. New-user revenue down points to traffic, the funnel or the
   paywall. Renewal revenue down points to an older change hurting renewals, such as a cohort that
   stopped renewing after a plan or offer change. Never diagnose from total revenue alone.
2. **Read the steps** (next section) before you rank anything.
3. **Conversion against revenue per user.** Use install → paid and revenue per install (see
   `diagnosis.md`). Compare the app against its own past, and against `market.md` only where the
   measure is the same (paywall view → paid, trial → paid, plan mix; never install → paid against
   a paywall conversion):
   - conversion fine, revenue per user low → plan structure: push buyers toward the longer plan
   - conversion low, revenue per user low → plan structure and the paywall itself
   - both fine → localization, plan mix and placements
4. **Context that changes the answer.**
   - How many products the paywall sells. One and two-or-more call for different first moves.
   - What was tested before. Ask; the CLI has no test history. A recent loss is off the table.
   - App size. Under about 200 purchases in two weeks, a test takes weeks to settle: recommend
     fewer, bolder changes, and say a small tweak will not reach a clear result.
5. **Priority.** The offer before the look: localization, trials and plan structure win more
   often than visual changes (`market.md`, Testing). Then the paywall design, then small tweaks.
   One test per placement at a time, 2-4 weeks each.
6. **Main market.** If one market holds 50% or more of revenue, treat it as the main market for
   the whole audit.

## The step that loses users

Read the conversions step by step (`diagnosis.md`, reads 9 and 10) before you rank anything. Two
weak steps are not paywall tests:

| Weakest step | What to propose |
|---|---|
| Paid → 2nd period and later | Plan structure: push buyers toward the longer plan |
| Billing issue → paid | No test: grace period and billing retry in the dashboard, as dashboard steps |

**Split before you blame a step.** A weak step in one store, country or channel is that segment's
problem. Run the step by `store` and `attribution_channel` first; a channel that converts far worse
is traffic, which `adapty-attribution` owns.

## Which placement to test first

One test per placement at a time, so the order of placements is the order of tests. For each
active placement with about 200 purchases in two weeks or more (smaller ones cannot settle a test;
say so), read its view → paid and its views (`diagnosis.md`, read 13):

1. **Set a target.** The paywall view → paid median for the app's main region in `market.md`, for
   an onboarding placement. A later placement converts about a quarter as well as onboarding in
   the report (0.23% against 0.85% per view), so its target is a quarter of that median. Use the
   placement's own rate over the same months a year earlier instead when it was higher.
2. **Count what the gap costs.** Missed purchases = views × (target − rate). A placement at or
   above its target costs nothing; leave it for later.
3. **Test the placement that misses the most purchases first.** Say the ranking in one line: "The onboarding paywall misses about 400 purchases
   a month against the market; the settings paywall about 30."

The targets are rough: the report covers the App Store only and counts purchases within 30 days of
a view. Filter the reads to `store=app_store` when you compare, and call the target "the market
median", never the user's goal.

## Plan structure

- The core lengths are weekly, monthly and annual. Weekly plus annual is the most common pair.
- **One product on the paywall:** add a second length first; nothing can be optimised without a
  comparison. Then a trial if the category uses one.
- **Two or more products:** find the leading length (by LTV from `analytics ltv`, otherwise by
  revenue share) and push purchases toward it: the trial on it, preselected, a badge.
- **Four or more products:** simplify to three before anything else.
- **Removing a length** is a candidate only when it earns under 30% of the paywall's revenue,
  and is judged on revenue per user: cutting plans has lost on revenue in `evidence.md`.
- "Remove X and add Y" is one swap test, not two.
- Never propose a 2-, 3- or 6-month plan; nothing here can justify one.
- A lifetime option next to annual is a legitimate test (see `evidence.md`).

## Trials

- End state: at most one product carries a trial.
- The trial goes on the leading length; with no clear leader, on the longest.
- A trial that exists is changed (its length) or moved (to another length). Removing a trial
  outright is a test only where trial-to-paid is very low; see `evidence.md`.
- Testing a trial on two different lengths is two tests run one after the other.

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
- **Escalating discounts** over days after a close are a growth-team estimate with no A/B
  evidence here: label them untested.
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
- **Say what it rests on:** the teardown's reading of the screen and the evidence library, plus
  this paywall's view → paid rate and its purchases per screen (reads 8 and 9 in `diagnosis.md`).

## After a test

- **The user decides the winner.** You cannot see A/B results through the CLI; ask which variant
  won. Inconclusive counts as a loss.
- **Check it was a test first.** Roughly 200 purchases per variant. Stopped after a few days or
  a few dozen purchases → inconclusive, not a loss; do not change the plan because of it.
- **Judge by type** (table above). A plan test on conversion alone is the commonest misread.
  A conversion drop of around half is a loss even when revenue per user rose.
- **Rule out by target** (table above), then propose the next test on that placement.
- After adding a plan length, suggest checking in a couple of months that its buyers renew.
- When a lever stops producing lifts, say further tests on it will likely return little, and
  move to another lever. Never invent rounds to fill a plan.

## Writing the why

The why is what makes a hypothesis this app's and not a general tip. It is the hypothesis's
Why line, and it carries three parts, in one sentence:

1. **Where:** the placement by name, and the plan, country or screen when the change targets one.
2. **What you saw:** one of the user's numbers with its period ("71% of purchases since April",
   "about 24 purchases a month"), or one fact from the render ("nothing on the screen mentions
   the trial"). Name which it is when that is not obvious.
3. **How the change acts on it:** the link from that observation to the change, in plain words.

Check it before sending: swap in another app's name. If the sentence still holds, it has no
observation from this app in it, so find one or drop the hypothesis.

- Problem first, in their setup; then the reason it matters.
- Two numbers side by side, never "baseline": "Brazil converts at 0.4% against your 1.5%
  overall".
- A market median from `market.md` is named as one, never as their category unless it is that
  category's row.
- The action is already in the title: no "we recommend", no "therefore".
- Different countries or products get different text.
- The pattern sentence does not repeat the why.

Shape of a good why (an example of the form, not words to copy):

> On your onboarding paywall, weekly brings 4% of revenue from about 24 purchases a month, while
> it shares the 3-day trial with annual, so moving the trial to annual alone puts it where the
> money is.

Weak: "Annual plans earn more, so preselecting annual raises revenue." True of every app: no
placement, nothing you saw, no number of theirs.
