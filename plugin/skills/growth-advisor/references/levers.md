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
| Title | Four slots: [verb] [what, by its name in their data] [from → to] on [placement][, for whom]. SKILL.md, "What a hypothesis needs". Use the type's template when it has one. |
| Target | What it changes: a product, a plan length, a country, a paywall or a placement. |
| Why | One sentence about this app only: where, what you saw, how the change acts on it. See "Writing the why". |
| Pattern | 1-2 sentences on the market pattern or user behaviour behind it. Said when the user picks the hypothesis or asks why, not in the audit. |
| Rests on | The numbers it depends on, and where each came from: the CLI or the user. |
| Judged on | The one metric that decides the winner. |
| Rules out | What a win and what a loss take off the table (see "After a test"). |
| Expected | A range from `evidence.md`, or "untested". |
| How to run it | "I can build it" (a flow, A/B tested or shown on a placement), "I can set it up" (a segment, new or existing, and its audience on a placement, through `audiences`), or "you do it in the dashboard", with the steps. |

## Known hypothesis types

| Type | Title template | Judged on | After a win, rule out | After a loss, rule out |
|---|---|---|---|---|
| Add a plan length | Add a [weekly/monthly/annual] plan next to [products] on [placement] | Purchase conversion and revenue per user | Removing that length | Adding that length |
| Remove a plan length | Remove [product] from [paywall] on [placement] | Revenue per user | Adding that length back | Removing that length |
| Swap a plan length | Replace [product] with a [length] plan on [placement] | Purchase conversion and revenue per user | The reverse swap | This swap |
| Add a trial | Add a [N]-day trial to [product] on [placement] | Trial conversion and trial-to-paid together | Adding it again | Adding it on that product |
| Move a trial | Move the [N]-day trial from [product] to [product] on [placement] | Trial conversion and trial-to-paid together | Every trial test on that paywall | This move |
| Change trial length | Change the trial on [product] from [N] to [M] days on [placement] | Trial conversion and trial-to-paid together | This change | This change |
| Follow-up offer | Show [offer] when [paywall] closes on [placement] | Revenue per user across the placement | This offer on that placement | This offer on that placement |
| Audience split | Show [paywall or change] instead of [current] on [placement], for [segment] | The change's own metric, in that segment | That change for that segment | That change for that segment |
| Win-back offer | Replace [current paywall] with a [offer] paywall on [placement], for [former subscribers / lapsed trials] | Revenue per user in that segment | This offer for that segment | This offer for that segment |
| Seasonal paywall | Show a [event] paywall instead of [current] on [placement] from [date] to [date] | Revenue in the window | — (re-run next season) | That design for that event |
| New placement | Show [paywall] at [moment], on a new placement | Purchases from that placement, and total revenue | — | That moment |
| Localization | Translate [paywall] into [language] on [placement], for [countries] | Revenue per user in that language's countries | That language on that paywall | That language on that paywall |
| Paywall design | [Verb] [element] on [paywall] from [now] to [new], on [placement]; the change from `paywall-teardown` | Purchase conversion | That change on that paywall | That change on that paywall |
| Onboarding change | [Verb] [screen or step] in [flow] from [now] to [new]; the change from `onboarding-teardown` | Conversion to purchase | That change on that flow | That change on that flow |

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
   - conversion fine, revenue per user low → plan structure: push buyers toward the leading length
   - conversion low, revenue per user low → plan structure and the paywall itself
   - both fine → localization, plan mix and placements
4. **Context that changes the answer.**
   - How many products the paywall sells. One and two-or-more call for different first moves.
   - What was tested before. Ask; the CLI has no test history. A recent loss is off the table.
   - App size. Under about 200 purchases in two weeks, a test takes weeks to settle: recommend
     fewer, bolder changes, and say a small tweak will not reach a clear result.
5. **Priority.** The offer before the look: localization, trials and plan structure win more
   often than visual changes (`market.md`, Testing). Then the paywall design, then small tweaks.
   One test per audience at a time, 2-4 weeks each.
6. **Main market.** If one market holds 50% or more of revenue, or 40% or more and five times the
   next country's, treat it as the main market for the whole audit.

## The step that loses users

Read the conversions step by step (`diagnosis.md`, reads 9 and 10) before you rank anything. Two
weak steps are not paywall tests:

| Weakest step | What to propose |
|---|---|
| Paid → 2nd period and later | Plan structure: push buyers toward the longer plan |
| Billing issue → paid | No test: grace period and billing retry in the dashboard, as dashboard steps |

**Split before you blame a step.** A weak step in one store, country or channel is that segment's
problem. Run the step by `store` and `attribution_channel` first; a channel that converts far worse
is traffic for its own part, which `adapty-attribution` owns. Before calling the rest traffic too,
check the step inside traffic that held (`diagnosis.md`, "It's the traffic").

## Which placement to test first

A placement runs one A/B test per audience at a time. Two tests on one placement run side by side
only on different audiences; an audience added above a running test's audience takes those users
out of it mid-test, and a crossplacement test cannot start while those placements run regular
tests. So for the users one test reaches, the order of placements is the order of tests. For each
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
a view. Filter the reads to `store=app_store` and to the median's region (a US median against the
app's US numbers) when you compare, and call the target "the market median", never the user's goal.

## Plan structure

- The core lengths are weekly, monthly and annual. Weekly plus annual is the most common pair.
- **One product on the paywall:** add a second length first; nothing can be optimised without a
  comparison. Then a trial if the category uses one.
- **Two or more products:** find the leading length (by LTV from `analytics ltv`, otherwise by
  revenue share) and push purchases toward it: the trial on it, preselected, a badge. It is
  often weekly, not annual; the evidence library leans annual-first, so check the app's own
  numbers before carrying a library win over.
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

- **A healthy set is about three placements:** the onboarding paywall (push the leading length), an in-app
  paywall at a value moment (a limit hit, a locked feature, settings), and an offer after the
  onboarding paywall closes.
- **Only one placement** is itself an opportunity. A large share of revenue outside onboarding
  (chart 8 in `diagnosis.md`) calls for a dedicated paywall at that moment.
- **Follow-up offer:** a discounted second screen when the onboarding paywall closes. Well
  evidenced after the onboarding paywall, and it loses after the main in-app paywall
  (`evidence.md`, across the flow).
- **Before any win-back plan, say who leaves, with numbers** (the "Winning back users who left"
  reads in `diagnosis.md`): how many endings are users cancelling and how many are billing
  issues, and how many trials end without paying. Billing issues come back through grace period
  and payment retries, with no discount: name that share first. When two reads disagree on billing
  issues (endings by reason against the billing-issue chart), give both numbers and say they
  disagree; do not pick one. Then aim the offer at the group worth the most. Reading it is not
  enough: the first fact after the bold answer is that split, with counts ("of 11,500
  subscriptions that ended since April, 84% were switched off by the user and 13% failed to
  pay", the shape, not the numbers), and each group the plan names carries its size.
- **Win-back offer:** former subscribers (paid before, no active subscription now), or users whose
  trial ended without paying (subscription state "trial cancelled"), get their own
  audience on an in-app placement with a discounted paywall; everyone else keeps the current one.
  A candidate when most endings are users switching off renewal (read 6 in `diagnosis.md`) and no
  placement has an audience for former subscribers. Offers keep far more revenue on returning
  subscribers than on new users (`market.md`, Discounts), which is why the offer must not reach
  new users. It needs a segment, created through `audiences`: subscription state "subscription
  cancelled" is the direct signal, and total revenue above 0 keeps out anyone who never paid. It
  also needs the discount in the store, which each store sets up differently ("By store").
  `evidence.md` has no win-back test: Expected is untested. The size of the discount and the
  discounted price are the user's: never name one, not even as an example ("annual for $29.99",
  "40% off"); ask. An existing product counts as a win-back product only when it has no trial and
  its name says it is the discounted one, or when `product-offers list` shows it a `win_back` offer. Its Time comes from how many of the target group
  come back a month at today's rate, never from a count of shows.
- **Escalating discounts** over days after a close are a growth-team estimate with no A/B
  evidence here: label them untested.
- **A separate in-app paywall:** simpler than the onboarding one, fewer plans, shown at value
  moments.
- **Seasonal paywall:** a real event with a real deadline. A countdown is fine here because the
  deadline is real; on a standing paywall it is fake urgency and raises refunds.
- **Paywall after a short goal quiz,** and **a free taste of the product before the paywall**
  (for games and creative tools): onboarding changes, routed to `onboarding-teardown`.

## Already tried, already live, or standard

Before ranking, drop any hypothesis that:

- matches what is live now (a trial already on that plan, an offer already shown on close, a
  placement that already exists). A default plan counts as live when any paywall that sold on
  that placement in the last full month has it: check every paywall's name and plans, not the
  top ones. When some paywalls have it and others not, say "N of your paywalls there already
  preselect X" and drop the hypothesis, or turn it into comparing those paywalls' numbers. An
  audience counts as live when the placement already has a segment for that group with its own
  paywall or flow (former subscribers on a discount paywall, a country on its own screen), and a
  change a selling paywall's name names (a badge, an offer, a default) counts as live: read both
  in `reads.py placement` before suggesting it;
- repeats a past test, whichever way it went, unless its loss failed the check in "After a test";
- repeats a past promo without a reason it would go differently this time. A discounted or
  promo product that sold on that placement in the window is a past promo: never write that no
  discount was tried there; read the placement's purchases by product before saying so.

A hypothesis that is sensible but standard (what most paywalls already do, `market.md`, How
paywalls look) stays only when the app does not do it yet, labelled as the standard move, and an
untried bet with a similar stake ranks above it. At a similar stake, a kind of change the data shows
no sign of also ranks above one more test of a kind it keeps running (`diagnosis.md`, What the
app already tried).

A discount or promo the app runs all the time (an onboarding offer, a win-back paywall, an
always-on LTO) is not a reason to suggest more of it. The bet is a holdout: part of the same users
kept from it, judged by revenue per user, with the dollars the discount gives up a month as the
stake. It questions money they already spend, which a dashboard never shows them.

## When nothing stands out

When no split shows one group carrying a gap and no step of the funnel is clearly weak, say so in
the bold answer ("nothing is broken; these are bets"). Then suggest growth bets, still ranked by
purchases at stake: a lever the app has not touched (a placement at a value moment, a win-back
audience, a plan length or lifetime it does not sell), something rare in the market with evidence
behind it (`market.md`, How paywalls look; `evidence.md`), a bet aimed at a segment, and at least
one bolder change sized to their traffic. Never fill the list with standard moves the app already
makes.

## Segments

A segment is not a lever of its own: any hypothesis above can be aimed at one group of users
instead of everyone at a placement. Each audience on a placement can then be A/B tested on its
own, in the dashboard ([A/B test on an audience](https://adapty.io/docs/add-audience-paywall-ab-test.md)).

**Look for a target on every hypothesis, unprompted.** A hypothesis is aimed at a segment when
all four hold:

1. **A split shows the group behaving differently** on the metric that judges the change
   (`diagnosis.md`, "Follow the signal down" and "From a split to a segment").
2. **A segment field can describe it** (the `audiences` field list). A group that only an
   onboarding answer describes cannot be targeted until the app saves that answer as a custom
   attribute; that is `adapty-integration`'s change, so say so instead of suggesting the segment.
3. **It is big enough to test:** about 200 purchases per variant inside the group, in under
   about three months.
4. **There is a reason the rest should not get it:** it would hurt them (a discount reaching new
   users), it cannot apply to them (a feature only in newer app versions), or only this group's
   numbers show the problem. Without such a reason, suggest the change for everyone.

**Rank it with everything else, by expected gain only.** For every hypothesis, targeted or not,
count what is at stake in purchases a month: for a placement, its missed purchases ("Which
placement to test first"); for a group, its volume × its gap to the rest ("1,260 trials a month
paying at 13% against 33%: about 250 purchases a month"). Order by that number. An evidence range
narrows how much of it a test is likely to win; an untested hypothesis is uncertain, not worth
zero, so it is not ranked below a well-tested one with a smaller stake. Being targeted earns no
place in the order either way. Say the numbers behind the order in one line.

**A targeted hypothesis does not replace the diagnosis.** When the group is a channel or a
campaign, the reply still says it is traffic and offers the campaign side (`adapty-attribution`);
the hypothesis is what the app can change for those users meanwhile. The Why line names the group and its
number; the Who line names the segment and its filters in words ("a segment: subscription state
is cancelled"), and that `audiences` creates it.

Shapes that come up (the field in brackets):

| Hypothesis | Aimed at |
|---|---|
| Win-back offer | Former subscribers (`subscription_state`, `total_revenue_usd`) |
| Add a plan length | A main market whose plan mix differs from the rest (`store_country`) |
| Add, move or drop a trial | A channel or campaign whose trial → paid is far lower (`channel`, `campaign`) |
| Paywall design | A channel whose ad promises something the paywall does not say (`campaign`, `creative`) |
| New placement or paywall | A feature that exists only from one app version on (`app_version`) |
| Localization | Usually no segment: a flow's locales already follow the device language |

A segment's evidence is the same entry in `evidence.md` as the change itself; the library has
almost no tests split by audience, so say when a range was measured on all users.

## By store

One placement serves both stores, and the stores set up trials and discounts differently. A
hypothesis says which store it is for and how it is built there, and gives steps only for the
stores the app sells on (revenue by `store`, or `products list`). Sources: [Offers in App
Store](https://adapty.io/docs/app-store-offers.md), [Offers in Google
Play](https://adapty.io/docs/google-play-offers.md), [Add offers to
Adapty](https://adapty.io/docs/create-offer.md).

| Change | App Store | Google Play |
|---|---|---|
| Add, change or remove a trial | An introductory offer on the product. It reaches every eligible buyer of that product, so a test needs a second product with or without it | An offer on the product's base plan (at least 3 days). Its offer ID goes on the product in Adapty; the test is a paywall that sells the product with the offer against one without |
| A discount for former subscribers | A win-back offer on the existing product, added to it in Adapty and picked on the paywall. Only churned users are eligible; no new product | An offer on the base plan with "Developer determined" eligibility, shown only to the win-back audience |
| A discount for anyone (an offer on close) | A promotional offer on the existing product, or a second product | An offer on the base plan |

- **The Adapty side of an offer is yours to add.** Once the user has created the offer in the
  store and given its offer ID (never guess one), add it on their yes; a Google Play trial or
  discount is `promotional` with only `--android-offer-id`, and `win_back` takes only
  `--ios-offer-id`. An App Store introductory offer is never added: it applies on its own.

  ```bash
  $ADAPTY product-offers create --app <APP_ID> --product <PRODUCT_ID> --title "<OFFER_TITLE>" \
    --type <promotional|win_back> --ios-offer-id "<STORE_OFFER_ID>"
  ```

  The offer reaches buyers only once a paywall or flow picks it for that product: a flow copy
  through `flow-generator`, a paywall copy in the dashboard.
- **A paywall's products and offers lock** once it has sales or is over 30 days old: a test
  needs a copy of the paywall. A flow can change them at any time.
- **Billing failures differ by store.** When one store has a much larger share of billing-issue
  endings (read 6 in `diagnosis.md`), that is a fix in that store's settings, not a paywall test:
  a longer [grace period](https://adapty.io/docs/grace-period.md) (App Store 3, 16 or 28 days, 3
  or 6 for weekly plans; Google Play set per base plan), given as dashboard steps.

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
- **A paywall from the old Paywall Builder** (the user confirms it; the CLI cannot tell it from a
  custom one) cannot be copied this way. Offer the dashboard's
  **Move to new builder** first ([convert a paywall to a flow](https://adapty.io/docs/convert-paywall-to-flow.md)),
  then the copy.
- **Say what it rests on:** the teardown's reading of the screen and the evidence library, plus
  this paywall's view → paid rate and its purchases per screen (reads 8 and 9 in `diagnosis.md`).

## After a test

- **The user decides the winner.** You cannot see A/B results through the CLI; ask which variant
  won. Inconclusive counts as a loss.
- **Check it was a test first.** Roughly 200 purchases per variant. Stopped after a few days or
  a few dozen purchases → inconclusive, not a loss; do not change the plan because of it.
- **A loss rules nothing out until you check the test ran as meant** (its audience, the store
  product live in its countries, the paywall in their language).
- **Judge by type** (table above). A plan test on conversion alone is the commonest misread.
  A conversion drop of around half is a loss even when revenue per user rose.
- **Rule out by target** (table above), then propose the next test on that placement.
- After adding a plan length, suggest checking in a couple of months that its buyers renew.
- When a lever stops producing lifts, say further tests on it will likely return little, and
  move to another lever. Never invent rounds to fill a plan.

## Ideas the user brings

When the user brings their own ideas, rank theirs by purchases at stake, as in "Segments", and
add at most one of your own, marked as yours.

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

- Lead with the surprise: the contrast in their numbers a growth manager would not have spotted
  in the dashboard.
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
