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
  group. A product's value is `<store>:<store product id>` (`app_store:com.app.weekly`), never
  the Adapty product id from `products list`.
- To compare every product, store or country on one conversion, group instead of looping over
  filters: conversions take `--group-by store_product_id` (and the other groupings the catalog
  lists), so one call answers every group.
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
  its key can be `null`, `""`, `"None"` or the zero UUID. Grouped by `flow_id`, "No Data" is the
  purchases made outside any flow (an old paywall); say that rather than leaving it unnamed. A
  funnel group's key is its title and can repeat: keep each group as its own row.
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
`reads.py audit` runs every read below and prints them; the commands are here for a read it does
not cover or a different filter.
Run every read below, 11 and 12 included: retention and LTV are what tell a plan that sells from a
plan that pays.

```bash
# 1. First payments vs renewals: Activation is first payments, Renewal 1, 2… the later ones
#    (renewal_status is auto-renew on or off, not new vs renewal)
$ADAPTY analytics chart --app <APP_ID> --chart revenue --date-from $FROM --date-to $TO --group-by period --json
# 2. Revenue by plan length
$ADAPTY analytics chart --app <APP_ID> --chart revenue --date-from $FROM --date-to $TO --group-by duration --json
# 3. Installs by country
$ADAPTY analytics chart --app <APP_ID> --chart installs --date-from $FROM --date-to $TO --group-by country --json
# 4. New paid subscriptions, split by the offer on the first payment (a trial that converts counts as No Offer)
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

A conversion answer's `data.value` is the rate in percent, `value_to` of `value_from` (for
`view-paid`, `value_to` is not new buyers: "Before you state a conclusion"); if the
window has none, `meta.recommended_period` can name one that has. `view-paid` and `view-trial`
are the conversion rate of a paywall: filter them by `paywall_id` (or `placement_id`, `flow_id`)
with a value from `analytics values`, one call per paywall, or group them by it when the catalog lists that
grouping for conversions. Compare paywalls only inside one placement: a paywall shown at
onboarding and one shown on a feature limit see different users. An LTV
point the cohort has not reached is `null`: compare lengths only at a point every one of them
reached. `analytics cohort` gives revenue per install cohort with a prediction; read it when the
question is whether a recent month's users are worth less.

The subscription path per plan is one grouped call per step, never a loop of filters:

```bash
# Each renewal step by product: run it for paid-2period, then 2period-3period, 3period-4period, 4period-5period
$ADAPTY analytics conversion --app <APP_ID> --conversion paid-2period --date-from $FROM --date-to $TO --granularity month --group-by store_product_id --json
```

Each group is one product; `trial-paid` grouped the same way gives the step before. **An annual
plan's renewals are in the data even when the data starts less than a year ago:** a renewal in
the window belongs to someone who bought the year before. Run the step for the annual product over
the last 12 months before saying its renewals are not in yet; only an empty answer says so. Leave out a
product whose step has under about 20 subscriptions behind it. An empty answer can mean the
window's subscribers have not reached that step yet: widen `FROM`, or take
`meta.recommended_period`.

Then the main market and the top countries:

```bash
$ADAPTY analytics chart --app <APP_ID> --chart revenue --date-from $FROM --date-to $TO --group-by country --json
```

The main market is a country with 50% or more of revenue, or with 40% or more and at least five
times the revenue of the next country. Compute every country's share of the total; when none
qualifies, the app has no main market: say so, and work from the spread. The
top countries are the three to five that hold most of it. Installs by country (read 3) do not
make a main market: a country can bring a quarter of the installs and almost none of the money.
Read chart 2, chart 4 and read 9 filtered to each top country (`--filter country=<value>`): which
plans sell there, how its conversion moved over the window, and where it loses users. Read each
country against its own past, not against the US or another country ("Before you state a
conclusion"). The main market decides which country's stakes come first and
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
$ADAPTY product-offers list --app <APP_ID> --product <PRODUCT_ID> --json   # each product with offers_count above 0
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
by `store_product_id`, or ask the user. `product-offers list` shows the offers added to a product
in Adapty, by type (`promotional`, `win_back`, `introductory`) and store: an offer there is
available to a paywall, not proof that one shows it. An App Store trial applies without being
added, so a product with no `introductory` offer listed may still have one: chart 4 settles it. Prices are out of scope; do not look them up.

## What the app already tried

Read this in every audit; the user will rarely tell you. Use 12 months, not six. `reads.py audit`
prints which paywalls sold on which placement over 13 months and notes a paywall that sold on
several: a promo, a seasonal offer or a test can run through a placement other than the one named
for it, so read that table before saying something did not run or was never tried. It also lists the
app's paywall and flow A/B tests (`reads.py placement`, the ones on that placement): each with its
placement, audience, dates and arms, and what that audience shows now.

```bash
# A/B tests in every state, one type per call: --type paywall, then --type flow (add --placement <ID> for one)
$ADAPTY ab-tests list --app <APP_ID> --type paywall --page-size 100 --json
# One test's arms and their weights
$ADAPTY ab-tests get <AB_TEST_ID> --app <APP_ID> --json
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
| A test in the A/B test list | A test they ran, with its dates and arms. The arm its audience shows now is the one they kept; say "kept", not "won". One that ran under a week is not a result. |
| Two paywalls or flows selling on one placement in the same weeks, then one stops | The test the list shows there then: name it. With none listed, a test across placements or a change of audiences: say what sold when, never that a test ran. The one still selling is the one they kept. |
| One paywall stops and another starts the same week | A change they made and kept. |
| A paywall in `paywalls list` that no placement shows | Something tried and dropped. Its name often says what it tried. |
| A flow on no placement | The audit's flows table says whether users ever started it. With viewers it ran and was dropped, and its name often says what it tried; with none it never reached users. |
| A placement, paywall, flow or product whose name names a change ("No Free Trial", "Exit Offer Test", "ex-Winback", "Weekly Trial And Yearly") | That change was tried, whatever its numbers. Say "it looks like you tested X; what came out?", never that it was never tried. |
| Two paywalls or flows both selling on one placement in the last full month | An A/B test or two audiences, if `placements get` shows one. A running test shows there as an audience of its own kind with its title: name it and never describe it in the past tense. With neither there, the two ran side by side earlier in the month: the test the list shows there then, or a change they made, and the one live now is the one they kept. |
| A product with purchases earlier and none lately | A plan or trial they dropped. |
| An offer with purchases in one stretch only | A past promo or intro offer, and when it ran. |
| Audiences and segments on placements now | Targeting they already do. |
| A placement with segment audiences and no All users audience | Either an A/B test the CLI did not return or users outside the segments see nothing there. The CLI cannot tell which: name it as a finding and ask them to check the placement's page. Never call it "probably an A/B test". |

Say it as facts with the dates, and say what the data cannot show: which arm of a test won (the
one its audience shows now is only the one they kept), and ideas they discussed but never ran.

Then sort what you found by kind of change, from `paywalls list` (which products each paywall
sells):

| Kind | How it shows |
|---|---|
| Visual or copy | Two paywalls that sell the same products |
| Plan set | Two paywalls that sell different products, or a product added or dropped |
| Trial or offer | A product with a trial added or dropped; an offer that ran |
| Localization | Not visible in the numbers; read the paywall or ask |
| Placement or audience | A placement or audience that appeared or went |

The data cannot show that a kind was never tried: a test can run outside Adapty or under a name
that says nothing. Read every name in `placements list`, `paywalls list`, `flows list` and
`products list`, every page, first. A kind with no sign anywhere is "no sign of it in your data",
never "you have never tried it", and the reply asks whether they did. Name those kinds with how
often each wins (`market.md`, Testing): an app that has only ever changed the look has its
likelier wins in kinds it has not touched.
Knowing what was tried is enough; you do not need the winner for this.

## Before you state a conclusion

Most wrong answers come from a true number compared with the wrong thing. Check each claim
against these before it goes in a reply:

- **One window and one baseline for the whole reply.** When the user names a period ("the last
  couple of months"), that is the window. "Held", "the same as before" and "fell" each compare the
  same two periods as every other number in the reply, at the same granularity. Never disprove
  the user's premise with a different period: if they say traffic held since summer, check
  summer, not January.
- **A break before the window that never recovered is still live.** `reads.py audit` reads each
  store's conversions over 12 months and prints a `STILL DOWN` line for every rate that fell a
  quarter and stayed down. The bold answer still comes from the user's window ("Why did revenue
  drop?", step 1); after it, one paragraph names each `STILL DOWN` line with its store, month and
  size. Under those lines it splits each store's fall in new subscriptions into fewer installs and
  lower conversion: a break is the main cause only in a store where conversion carries the larger
  share, and the reply gives both shares.
- **A conversion's size comes from month grain.** A conversion counts each user once per bucket,
  so the same months read by week and by month give different rates, and different drops. Find
  the week with week grain, then read the same months at `--granularity month` and give that
  drop. A fall measured from the best month also says where it stands against the months before
  it ("down from the July peak, still above January to May").
- **Older cohorts and recent ones are both read.** When you compare cohorts old enough to be
  complete (90-day revenue, LTV), read the same rate for the last three full months too. If the
  recent months tell a different story, the reply says so next to the conclusion.
- **Groups are compared month by month.** Before saying two channels, placements, plans or
  countries perform the same or differently, read the rate for each at `--granularity month`
  and line the months up. A gap that opened or closed inside the window is the finding: give the
  last three full months next to the window's figure, never the window's average alone.
- **"None", "only N", "you kept X" and "nothing after Y" are counts.** Before the reply says how
  many paywalls sell on a placement, that one stopped, that a placement or flow has no purchases
  or that nothing shows after a paywall, count every group in a read that covers that placement
  through the last full month and give the number, never "more than N", and read the whole answer, never through `head` or a cut-off
  print. An active placement with audiences is something, however few purchases it brings: say
  what it sells and ask where it is shown. When no read covers it, say "until <date> I see…" or
  ask.
- **What is live now comes from the last full month, never the window's average.** Which plans a
  paywall sells, which placement or paywall brings the purchases, what is running for former
  subscribers: read it month by month and state the last full month. A six-month share can
  describe a plan dropped in June or a placement that stopped getting traffic in September. When
  the picture changed inside the window, name the month, say the earlier numbers describe a setup
  that is gone, and never aim a hypothesis at a placement, paywall or plan with almost nothing in
  the last month.
- **Date a change from the data, not from your window.** When you find a break, read the series
  back to a stable stretch: 12 months at month grain, then week grain around each step. Never
  date a change from quarter grain: a September switch read by quarter looks like July. A drop
  often comes in steps; name every step with its date. The start of the window you happened to
  read is not when anything started. `reads.py` prints an `onset:` line under each conversion: the
  peak and the first month 15% or more below it. Date the fall from that line, and when it says the
  peak is the start of the window, read further back before naming a month.
- **A fall back to the level before a spike is the end of the spike.** When a store, channel or
  country ran far above its own usual level for a stretch and then came back to it, compare with
  the level before the spike, give the weeks it rose and fell, and ask what drove it (a campaign,
  a promo, a feature). Never call it something that broke or stopped.
- **Before and after inside one store.** Compare a placement or paywall with the one it replaced
  per store: when one store converts far lower, a combined rate moves with the store mix. Read
  the old one's own trend up to the switch too; if it was already falling, say how much of the
  gap came before the change. The size of the change is against the old one's level over the
  months before it started falling, not its lowest month. When both ran in the same month, compare
  them at `--granularity day` over the days both had full traffic; a month that holds one
  side's leftover traffic after the switch is not the comparison. `reads.py placement` prints
  these numbers for every switch it finds (the old level before its share fell, the month both
  sold, the whole placement's rate): the reply gives them, and says when the whole placement fell.
  `reads.py audit` prints the last three months against the same months a year earlier, per store,
  and a NOTE when a store launched: name a launch next to any before/after that crosses it, and
  read each store against its own past year before calling one of them steady.
- **Split by channel before you blame the product.** A rate that falls because a channel that
  converted well stopped sending traffic is a change of mix, not a broken paywall or release.
  Read the rate by `attribution_channel` and check whether it fell inside a channel whose traffic
  held. Say which part of the fall is mix and which part happened inside a channel.
- **A total that held can be one channel replacing another.** Before calling traffic flat,
  steady or "the same", read installs by `attribution_channel` month by month. `reads.py audit`
  prints a `moved in` line under that read (every channel that moved a tenth of the total in the
  last full month) and a `started or stopped` line: the reply names each channel on those lines
  with its month, next to the total.
- **A weak point is measured in money per view, not in a rate.** A rate that fell after a price
  rise is not weak when first-payment revenue per view held. `reads.py audit` ranks the top
  placements per store, inside the country with the most revenue, by first-payment revenue per
  paywall view against the other store and against their own best months, and prints the gaps as
  `WEAKEST` lines in dollars a month.
- **Dollars go only to a slice that was read.** "That's the $9k" or "this costs $X a month" needs a
  read of that slice's own revenue. Without one, give the slice's own numbers and say how much of
  the drop they leave unexplained.
- **A span quotes its lowest and highest month.** "Stable at 4.7–4.9%" is wrong when one month in
  that span read 4.2%: give the range over every month the sentence covers, or name the months.
- **Who sees a paywall comes from its audience.** `reads.py audit` prints each audience's segment
  filters, and for a country filter which of the app's top revenue countries it takes in. A
  hypothesis that changes a paywall for a group of users names a paywall that group's audience
  shows; when the audience points elsewhere, the hypothesis changes that paywall instead.
- **A placement is called a placement.** Names come from `placements list` and `paywalls list`;
  "the Settings placement", never "the Settings paywall" when Settings is a placement.
- **"It's the traffic" needs the rate inside traffic that held.** Before saying a fall is mix
  (a store, country or channel that converts worse grew), read the same rate over the same months
  inside one store and in its largest countries by revenue, the main market first, and in
  unattributed traffic. Pick those countries by size, never by whether they moved. If the rate
  fell there too, the reply says mix explains part and the rate also fell on steady traffic, with
  that slice's numbers, and never "the paywall is not broken" or "this is traffic, not the
  paywall".
- **A change is a cause only where it acted.** Before naming a change as the cause of a rise or
  fall (a new product, paywall, placement, price, release, offer or store launch), read the same
  rate over the same weeks for what the change did not touch: the old product, the other store,
  another placement or country. If that moved the same way, the change is not the cause: say so,
  with both numbers, and look for what the two share. This is the Cause check in "Follow the
  signal down".
- **"Everywhere" needs every group checked.** Before saying a fall is in all stores, countries or
  channels, read each large one; name the exceptions.
- **"All" sums every group.** A share for "all non-English countries" or "all of Android" adds up
  every group in the answer, not the top ones you read; if you summed the top seven, say "the top
  seven". A list of what sells now ("the three paywalls that sell") is every group with a sale in
  the last month, one sale included.
- **`subscriptions_new` includes subscriptions that started after a trial, and `offer_category`
  does not show them.** A trial that converts lands in No Offer, like a straight purchase; the
  categories mark only a discounted or promotional first payment. Whether a plan has a trial, and
  how many buyers came through one, comes from `trials_new` by `store_product_id` and trial → paid,
  never from No Offer.
- **`view-paid` counts any purchase after a view, not new buyers.** Its second number is everyone
  who saw a paywall that day and paid at any time after: renewals of people already subscribed and
  one-time purchases count too (install → paid counts the first subscription only). Never call it
  purchases or buyers. New buyers are `subscriptions_new` on the same placement and store: before
  saying a placement or paywall sells less or stopped selling, check that count fell too, and give
  it next to the rate.
- **Small numbers are noise.** A rate with fewer than about 20 purchases or trials behind it, per
  group or per month, cannot rank two groups, date a change or name its cause: give the counts
  ("4 of 644 installs, against 1 of 415"), say they are too few to tell, and never call a group
  one that "barely buys". `reads.py` marks such rows with `~`. Traffic that grew while purchases did
  not is evidence against "traffic is what limits you": say what the extra traffic did not change.
- **"Most" and "biggest" need the comparison.** "Most money is lost on renewals" compares what
  is lost at renewal with what is lost at the paywall, in the same window, and you compute both.
  A rate with nothing to compare it to (`market.md` has no renewal median) is stated as what it
  is, never as the biggest loss or as low. "One of the lowest" or "mostly Europe" ranks every
  group in the answer, not the ones you looked at; and "74% are weekly with a trial" counts every
  product of that kind, or names the one product it is.
- **Countries are read against their own past.** Prices and buying power differ by market, so
  a country's conversion or revenue per install is not ranked against the US or against another
  country. What a country's numbers mean: its trend over the window, which plans sell there, and
  where its funnel loses users. Call a market healthy only from its own trend.
- **A premise about the market is checked, not adopted.** When the user says most users come
  from one country, compute each country's share of revenue and of installs. If no country has
  50% or more of either, the bold answer corrects it with the real split ("There is no single
  market: Brazil and Mexico bring a third of installs each, and revenue is spread over five
  countries", an example of the shape, not words to copy), and the rest of the reply is built on
  that split, never on the user's picture.
- **A country is not a language.** Analytics has no language split, so the numbers show where
  users are, never what language they speak. Say "users in Mexico", not "Spanish speakers";
  a claim about language needs the paywall's locales or the user's word. That includes ruling
  language out: "the market speaks English" is a language claim too.
- **A market median is compared on its own slice.** The State of Paywalls numbers are App Store
  only and per region: filter the app's read to `store=app_store` and to that region's countries
  before putting the two side by side.
- **What the CLI does not show is asked, not stated.** Which plan a paywall preselects or lists
  first, its prices and its trial copy are not in any read; a paywall's or product's name only
  hints at them. When to expect renewals comes from the data: read revenue by product and
  `renewal_status` before saying when a plan's renewals start.
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
| Channel | `trials_new` and `subscriptions_new` by `attribution_channel`, then `installs --filter attribution_channel=<value>` | Whether one channel's traffic converts far worse. Then that channel's part of the fall is traffic: say so and offer `adapty-attribution` for its campaigns. Whether the rest is traffic too: "It's the traffic" in "Before you state a conclusion". The `No Data` channel is unattributed traffic, not organic. |
| Cause check | The same rate, the same weeks, for what the change did not touch: the old product or paywall, the other store, another placement or country | Required before a reply names a change as the cause. If the untouched group rose or fell the same way, the change is not the cause: give both numbers. |
| Mix check | The rate that fell, `--granularity month`, `--filter store=<the store with the most revenue>` and `--filter country=<value>`, one call per country for the three largest by revenue; then the same rate with `--filter attribution_channel=<the No Data value>` | Required before a reply calls the fall traffic or mix. If the rate fell in those countries too, it fell on steady traffic: say so, with the main market's numbers. |
| When | `--granularity week` over the eight weeks around a change | The week it started, to match against a release, a price change or a campaign. |
| Before and after | `chart` or `conversion` with `--compare-from`/`--compare-to` set to the same length before the change | How much moved, in one call. |
| Where in the funnel | `funnel` by the split that moved, against the total | Which step the split loses users at. |
| Who is leaving | `trials_renewal_cancelled` and `subscriptions_renewal_cancelled` by `duration`, `country` or `attribution_channel` | Who switched off renewal before revenue shows it. |
| Offers | `revenue` and `subscriptions_new` by `offer_id`, then the same filtered to that offer and grouped by `country` and `store` | Whether an intro or win-back offer pays for itself, and where: an offer that loses money overall can still pay in some countries. |
| Refunds | `refund_money` by `store_product_id` or `country`, against revenue for the same split | Purchases that come back. A win with heavy refunds is not a win. Read refunds both as a share of purchases and as a share of revenue; they can disagree. The data shows where refunds come from, never why: name no reason the reads do not show (a surprise charge after a trial, a missing translation), and build no hypothesis on one. |
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
- **Its languages are `localization.locales`.** The top-level `locales` can be empty on a newer
  flow. Count them per flow; the CLI does not show the languages of a paywall (only of a flow), so
  for a paywall say so and ask.

Read 8 by `flow_screen_id` shows which screen of the flow the purchases came from. Never write
to the flow from this skill; a change is a copy (`levers.md`, Paywall design).

## Flow placement metrics

On a flow placement, `reads.py placement` also prints the dashboard's metrics in one call: each
audience, A/B test arm and store, with viewers, the share who finish the flow, purchases, trials,
revenue per viewer, and purchases by product. Only flow placements have them.

```bash
$ADAPTY placements metrics get <PLACEMENT_ID> --app <APP_ID> --type flow --based-on audience --group-by store --date-from $FROM --date-to $TO --date-type purchase_date --json
```

- **Viewers are unique users who started the flow,** the count view → paid starts from (read 9).
  In an onboarding flow that is everyone who began onboarding, not only those who reached its
  paywall.
- **Revenue here counts renewals.** A hypothesis's base stays first-payment revenue, and the Time
  line stays the weekly purchase count, both from the analytics reads.
- **A running test's arms show progress, not a result.** Read them in the section that starts on
  the test's start date: over the whole window an arm also holds what its audience sold before
  the test. Say how far each arm is from about 200 purchases; never which one leads or wins.
- **Finished is the share of viewers who reach the flow's last screen.** Where the others leave is
  on the flow's [Funnel tab](https://adapty.io/docs/flow-funnel.md), which the CLI does not read:
  when a low share would change a hypothesis, ask for a screenshot of it. A screen row's views in
  this answer are not that funnel: they count only users who started the flow on that screen.
- **A flow on several placements, or two flows compared:** `flows metrics list --ids <FLOW_ID>,…`
  gives lifetime rows, and `flows metrics get <FLOW_ID> --based-on placement --date-from … --date-to
  … --date-type purchase_date` splits one flow by placement (the dates are required). Compare
  placements inside it, never one placement's number with another flow's total.

## "Why did revenue drop?"

1. Chart 1 (new vs renewal) over the period the user means and the months before it, at
   `month`, or `week` for a drop under two months. Compute how many dollars of the fall each side
   carries. The bold answer names the side that carries most of it, whatever the user suspected
   (the paywall, traffic), and the first fact after it is that split, with dollars: "of the $2.9k
   drop since May, $2.2k is renewals from long-time subscribers" (the shape, not the numbers).
   When it is renewals, say plainly that the paywall is not the main cause. Installs, countries
   and the paywall come after, and a side that is a small share of revenue (new purchases at 3%)
   cannot be the cause of a larger fall: say so in one sentence.
2. **Renewals fell:** chart 6 by reason. Cancelled by the user points to the cohort that came up
   for renewal (a past promo, a change to the plans, a weak acquisition month a year earlier for
   annual). Billing issues point to grace period and payment retries: `billing-issue-paid` and
   `grace-period-paid` say how many are recovered. Read the renewal-step conversions
   (`paid-2period` and on) by `duration`, or by product (the grouped call after read 13), read 11
   and `analytics cohort` to find the cohort that renews worse. Ask what changed then; the CLI shows no release
   history.
3. **New revenue fell:** chart 3 and chart 4. Installs down is traffic (`adapty-attribution` owns
   campaigns). Installs flat and new subscriptions down is the funnel or the paywall: read 9 with
   a compared period and read 10 to find the step that fell.
4. Split the falling side by country and by store before naming a cause. A drop in one country
   is a different story from the same percentage everywhere.

## "Should I change X?" (one idea)

Answer in three parts: the verdict (test it / a fair bet / skip it / already a strong default),
why (the user's numbers, then what `evidence.md` says, with the split if results were mixed), and
the one trap to avoid. An idea about a plan (push annual, add monthly, drop weekly) names the
main product by revenue over the last 12 months, with its share, before the verdict: the user may
be asking about a plan that is not where their money is. Read only what the idea depends on
(numbers are the audit reads):

| Idea | Reads |
|---|---|
| A plan length | chart 2 and chart 4 per length, read 12 |
| A trial | charts 4 and 5, read 9 (trial pairs), read 11 with and without `--use-trial` |
| A country | charts 1 and 4 filtered to it, chart 3 |
| A new placement or offer | chart 8 by placement; the setup reads; ask where users hit limits in the app |
| Winning back users who left | chart 6 by reason, per store; `subscriptions_renewal_cancelled`; `trial-paid`; `billing-issue-paid` and `grace-period-paid` |
| A paywall or flow's design | read 8 by paywall or flow, `view-paid` for that paywall, then the screen itself (`levers.md`, Paywall design) |

## "My test ended, what next?"

Find the test in the A/B test list first (`reads.py placement` on its placement): its name, arms,
audience and dates, so the user is not asked what you can read. The CLI shows no A/B results.
Ask, in one message: which variant won (or inconclusive) and roughly how many purchases each
variant had, and which test it was only when the list leaves it unclear. Until you know,
never tell them to roll the winner out: the bold answer is conditional ("roll B out if each
variant had about 200 purchases; with fewer, it has not won yet"). Then apply `levers.md`, "After
a test", and propose the next test for that placement. The same questions come first when the
user says a test failed.
