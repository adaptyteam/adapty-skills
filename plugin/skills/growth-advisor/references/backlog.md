# The backlog: saving, starting, linking, results

Open this when you save hypotheses, start one, link its A/B test, put one live without a test, or
come back to an app that has a backlog. Every command here is `$ADAPTY hypotheses <command> --app
<APP_ID>`; each answer prints `Allowed Actions`, the only actions the server takes next for that
hypothesis. Run nothing it does not list.

## The create body

One JSON object per hypothesis, all in one file (`drafts.json`), the same file `reads.py backlog
--drafts` checks:

| Field | From |
|---|---|
| `placement_id` | The placement the hypothesis runs on. One that does not exist yet is created with the hypothesis's published flow, and the hypothesis saved after it (SKILL.md, "The backlog") |
| `subject` | `type` and ids from `levers.md`, "Saved as": `flow` with `flow_id`; a paywall screen is `flow_screen` with `flow_id` and `flow_screen_id`, the screen's id in the flow config; `audience` with `segment_id`; `paywall` alone for a legacy or custom paywall |
| `type` | `levers.md`, "Saved as" |
| `title` | The hypothesis title, at most 80 characters: keep the verb, what and the placement, drop the rest |
| `rationale` | The Why line |
| `action` | The full title, then the Who line |
| `expected` | `metric`, `low_pct` and `high_pct` from the Expected range, and `evidence_text`, where the range comes from. No range: `evidence_text` alone |
| `metrics_impact` | Any second metric it moves (`cr_to_paid` next to `cr_to_trial`) |
| `products` | A plan, trial or price change only: one row per product it adds or changes, with `duration_type` (`weekly`, `monthly`, `annual`, ...), `trial_duration` in days, `country` for a price in one country, `product_id` of the product it changes. The new price itself goes in the title and rationale: a row has no price |

A draft `reads.py backlog` marks as needing force gets `"force": true`. `reads.py` gives every
draft a `hypothesis_id` and keeps it in the file: if a create fails halfway, send the same file
again, and the saved ones answer `Already stored` instead of saving twice. Edit a draft only before
its create: a saved hypothesis never changes, and a changed draft under a saved id is refused.

## Starting one

1. Build what the A/B test needs ("From hypothesis to A/B test" in SKILL.md). A product it needs
   that does not exist yet is created first (`pricing.md`, "Adding a plan length", or "Setting up
   a price A/B test").
2. `hypotheses accept <ID>`, with what the hypothesis carries:
   - a flow change: `--variant-flow <the copy's flow id>` once the copy is published; before
     that, accept without it, and the linked test fills it;
   - each product row (`hypotheses get <ID>` lists them with their `hypothesis_product_id`):
     `--product <HYPOTHESIS_PRODUCT_ID>=<PRODUCT_ID>`;
   - an audience split put live: `--placement-audience <the audience's id>` from `placements get`.
3. Once `ab-tests` returns the draft test: `hypotheses link <ID> --ab-test <TEST_ID>`, then
   `hypotheses by-ab-test <TEST_ID>` shows the hypothesis on it. A flow hypothesis links only to a
   flow test whose two arms are exactly the flow the placement shows and the copy, on the same
   placement; a refused link (`hypothesis_link_failed`, `hypothesis_variant_mismatch`) is said as
   the arm that differs, then fixed with `ab-tests` or the copy, never by linking another test.
   An audience split, or a hypothesis on a legacy or custom paywall, has no link: say its test result is read with
   `ab-tests metrics` and resolved on the user's word.
4. After any start, stop or replace through `ab-tests`, run `by-ab-test` again. A link gone is one
   line to the user and a `link` to the test that replaced it.

## Live without a test

When the user wants the change live now: accept it, change the placement through "Changing a
live placement", and say once that without an A/B test nobody can tell what the change did, so its
result is a before-and-after reading. An audience split accepted with `--placement-audience` shows
as live in the backlog; a flow change shows as accepted.

## Coming back

`reads.py backlog` prints what is due before anything new is suggested. Act on each:

- **A test running:** read `ab-tests metrics` and say where it stands. When its leader settles
  (the `ab-tests` skill's "Results and the leader") or its planned time is up, offer the stop
  through `ab-tests`. A stop with a winner resolves the hypothesis by itself.
- **A test stopped without a result,** or a result the server suggests: show what the metrics
  said and ask the user. Then `hypotheses resolve <ID> --result won|lost|inconclusive`, only on
  their word. A wrong result is changed with `reresolve`, also on their word.
- **Put live without a test:** once as much time has passed as its Time line gave, compare the
  weeks before and after (`reads.py health` and the placement's metrics), say what a
  before-and-after cannot prove, ask the user, then `resolve`.
- **Stale** (its flow, version or placement is gone): one line, and an offer to dismiss it.

`hypotheses dismiss` runs only on the user's word, never because a hypothesis looks old.
