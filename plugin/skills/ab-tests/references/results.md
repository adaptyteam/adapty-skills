# What the A/B test numbers mean

Read this when you show results (`ab-tests metrics`). The leader and its reason come from the
section "Results and the leader" of `SKILL.md`: read it too, and say its first matching line with
its reason. Say each point once, where the user needs it.
The examples show the shape, not words to copy.

- **P2BB** is the chance, in percent, that the arm is the best by revenue per viewer. The arms of
  a test add up to 100.
- **P2BB 0 on every arm** means it is not computed: the arms have purchases but no views, more
  payers than viewers, or the model failed. P2BB 0 on one arm beside an arm above 0 is a real value.
- **The same P2BB on every arm with no purchase on any arm** means it is not computed.
- **No views on any arm:** there is no result, whatever the P2BB says. The dashboard may still
  preselect an arm there; this skill names none.
- **P2BB of a period** (`metrics get`): for a paywall test a running total from the start of the
  window, so it holds on a day with no views and never equals the arm's P2BB; for a flow test only
  the value of that period. Neither is a trend and neither names a leader.
- **The interval** is the 99 percent range of revenue per 1,000 unique viewers (`low_boundary`,
  `average_per_1000`, `upper_boundary`). The 50-payer rule is per arm: with fewer than 50 paying
  users in that arm, its range is 0, the mean and two times the mean; with no payers 0, 0 and 0.
  Say it is not modelled, not that the arm earns nothing. Another arm of the same test can have
  a full range.
  A paywall test in `metrics list` carries only the mean: no low and no high.
- **The p-value** is a number only for a flow test with exactly two arms. It is empty for a
  paywall test, for a flow test with three or more arms, and when it is not computed.
- **The type:** the user or you give `--type` (`paywall` or `flow`); take it from `ab-tests get`.
  A wrong type is refused with the test's own type.
- **Date types** of `metrics get`: `purchase_date` or `profile_install_date` (the dashboard's
  "Filter metrics by install date"). Views are counted by the view date with either.
- **Live tests** change between two reads: P2BB, interval and p-value move. Say the numbers are as
  of now.

An arm row, as a shape:

> Annual paywall: weight 50, revenue 1,240.00, chance of being the best (P2BB) 93 %, 99 % range
> 410 to 560 per 1,000 viewers.
> Monthly paywall: weight 50, revenue 980.00, chance of being the best 7 %, range 330 to 470.
> The dashboard highlights the Annual paywall. That is not a verdict: which arm wins?
