---
name: ab-tests
description: Use when a user wants to run, check or end a regular A/B test of paywalls or flows through the Adapty CLI — plan it, create the draft, change it, start it, stop it with a winner, replace a running test with a changed one, archive it, or see which tests an app has. Triggers on "run an A/B test of these two paywalls", "test my new flow against the old one", "split traffic 50/50", "start the test", "stop the test, B wins", "end this experiment", "change the weights of my test", "which tests are running", "archive the old tests".
---

# A/B tests: plan, start, stop, replace

A regular A/B test splits the users of one audience at one placement between two or more
paywalls, or between two or more flows. This skill owns the whole life of such a test through
`$ADAPTY ab-tests`: plan, create, update, start, stop, replace, archive. **A start, a stop, a
replace and an archive change what real users see and cannot be undone.** Those four run only after
the user has seen their exact effect and said yes.

It does not own:

- **Building the paywall or flow** → `flow-generator`. A flow joins a test only once it is
  `published`.
- **Who sees what on a placement without a test** (segments, audiences) → `audiences`. It also
  makes the segment a test starts on.
- **Results of a test, tests across several placements, onboarding tests** — not in the CLI. The
  user reads them in the dashboard: https://adapty.io/docs/add-audience-paywall-ab-test.
- **Apple Search Ads product-page tests** → `ads-manager`.

## How you sound

- **"I" for what you do, "you" for what they do.** Lead with the answer, end on one next step; no
  opener, no recap. Name a skill only when the user must act on it themselves.
- **Name users and content, not ids:** "German users", "the Annual paywall", "test Price test".
  Ids only inside a command.
- **A fixed block where a decision is made (the effect card), one line otherwise.** Say each thing
  once.
- **Bold the one thing that cannot be undone,** at most once per block.
- **Be honest about scope:** say what you did not read (results, shared tests) and how the user can
  check.
- Full, clickable links. Reply in the user's language; the dashboard's own words stay ("Modify" is
  `replace`).

## The CLI

Resolve `$ADAPTY` once and use it for every call:

```bash
adapty ab-tests --help >/dev/null 2>&1 && ADAPTY="adapty" || {
  npm i -g adapty@latest >/dev/null 2>&1 && ADAPTY="adapty" || ADAPTY="npx --yes adapty@latest"; }
```

CLI 0.12.0 is the first release with the `ab-tests` commands. If `$ADAPTY ab-tests --help` still
reports no such topic, try `npx --yes adapty@beta ab-tests --help` once; if that fails too, tell
the user their CLI has no `ab-tests` commands yet and the test is made in the dashboard (link
above). Do not compare version numbers. `--yes` on `npx` is required: without it `npx` waits for a
confirmation nobody gives. In `zsh`, run `setopt shwordsplit` before using a multi-word `$ADAPTY`.
Write a literal `adapty` in a command you show the user. Every command takes `--app <id>`, the
**Adapty** app UUID from `$ADAPTY apps list`. Read with `--json`.

| Command | Flags |
|---|---|
| `ab-tests list` | `--type paywall\|flow` (default **flow**: a paywall test is missing from a default list, so ask for both), `--state live\|draft\|completed\|inactive\|archived`, `--placement`, `--search`, `--page`, `--page-size` (use 100) |
| `ab-tests get <id>` | the test and its arms |
| `ab-tests create` | `--title`, `--goal`, `--placement`, `--segment <id>` or `--all-users` (a plan only), exactly one of `--paywalls '<json>'` / `--flows '<json>'` |
| `ab-tests update <id>` | the same flags as create. **The whole test is sent again:** a flag you leave out is cleared (goal, placement, planned audience) |
| `ab-tests start <id>` | `--placement`, exactly one of `--segment <id>` / `--all-users`, `--yes` |
| `ab-tests stop <id>` | exactly one of `--winner <id>` (the `paywall_id` or `flow_id` of an arm of the test), `--other <id>` (the `paywall_id` or `flow_id` of other content, not an arm), `--no-content`, `--yes` |
| `ab-tests replace <id>` | `--title`, `--goal`, `--placement`, exactly one of `--paywalls` / `--flows`, `--yes`; no audience flag |
| `ab-tests archive <id>` | `--yes` |

Arms are a JSON array: `[{"paywall_id":"<id>","weight":50,"title":"A"}, …]`, or the same with
`flow_id`; `title` is optional. The weights sum to 100; the server checks that and the number of
arms. A `get --json` test has `ab_test_id`, `title`, `goal`, `type` (`paywall` or `flow`), `state`,
`placement` (`placement_id`, `title`, or `null`), `segment_ids` (`[]` is All users, `null` is none
planned), `priority`, `started_at`, `stopped_at`, and `paywalls[]` or `flows[]` with `weight` and
`title`. `state` is one of the five above.

Without `--yes`, the four one-way commands ask at a terminal; in a pipe or with `--json` they
refuse with exit 6 `confirm_required` and send nothing. Exit 4 is the server's refusal, with its
own text. These come back often:

| The server says | It means | You do |
|---|---|---|
| `The sum of the weights must equal 100, but has N.` | the arms | fix the weights |
| `Flow(<id>) must be published before adding to AB test.` | an unpublished flow | `flow-generator` publishes it first |
| `Paywalls cannot be changed in non-draft ab tests.`, `Placement cannot be changed in non-draft ab tests.` | an update on a started test changed arms or placement | send the arms and placement as read, or use `replace` |
| `AB Test from default audience can not be stopped.` | `--no-content` on All users | `--winner` or `--other` instead |
| `AB Test to stop must be live.` | a stop or replace of a test that is not live | say so; a new test is the way |
| `Live Ab Test can not be deleted.` | an archive of a live test | stop it first (a stop has its own card) |

## The effect card: before start, stop, replace, archive

1. **Read the test:** `ab-tests get <id> --json`. For a start, stop or replace also read the
   placement: `placements get --app <app> <placement> --json` (`audiences[]` with `content_type`,
   `segment_ids`, `priority`, the `paywall_id` or `flow_id`, or for a test `ab_test_title`). For an
   archive, read the placement too when the test has one, to say where it sat. Turn ids into names
   with `paywalls list`, `flows list`, `segments list --page-size 100`. **Keep this placement read**:
   it is what the user saw.
2. **Show the card** and wait:

   > Start "Price test" on the Main placement for German users.
   > - Now: German users see the Monthly paywall.
   > - From now: they see the Monthly paywall (50%) or the Annual paywall (50%), a new draw for each
   >   user. A change for a segment can take up to 20 minutes to reach every user.
   > - Stops: the Monthly paywall stops for German users; the test "Old test" running there
   >   becomes completed.
   > - Moves: German users who also match "Premium users" go into the test.
   > - **Cannot be undone.** Stopping it later does not bring back what it replaced.
   >
   > Start it?

   This shows the shape, not words to copy. Each line says who sees what from when, names what
   stops, and ends on what cannot be undone. Per action:
   - **Start.** The audience is the placement row with the same segment (`[]` is the default row).
     A segment with no row gets a new row at the top, so users of this segment who match another
     audience move into the test: name those audiences. A row that holds a test ends that test: it
     becomes completed. A row that holds a shared test (`cross_ab_test`,
     `flow_cross_ab_test`) is not yours: send the user to the dashboard.
   - **Stop.** Say which content the audience shows afterwards (the winner, the other content, or
     nothing: its row leaves the placement and its users get the next audience they match). The
     test becomes completed; **it does not run again unless started again**, and this skill does not
     start it again (see Never).
   - **Replace.** The live test stops and becomes completed, its results stay on its id. A new test
     with a new id starts on the same audience with new arms, and every user of the audience gets a
     new draw. Another `--placement` moves the audience there (refused on All users).
   - **Archive.** The test leaves the lists and **cannot be unarchived.** Only a test that does not
     run; a live one is stopped first.
3. **Wait for the user's yes.** Only an answer to this card counts, not an earlier "go ahead"
   about the plan. "No", silence or a change of plan: send nothing.
4. **Read the placement again** just before a start, stop or replace and compare its audiences
   (content, segments, order, tests) with the read the user saw. If it differs, show a new card
   for the new situation and ask again. The same goes for the test: if its state changed, start over
   from step 1.
5. **Run the command with `--yes`**, then read the test back with `get --json` and say what now
   runs.

**An unattended run never does these four** (a scheduled run, a script, no user to answer). It may
list, get, create and update. For the four it stops and reports the card and the command for the
user to run, written with a literal `adapty` and **without** `--yes`: at their terminal the CLI asks
again.

## Workflow

1. **Plan.** Settle in one message what is missing: paywall test or flow test; the arms (content
   and weight, 50/50 for two); the placement; the audience (All users or one segment); a goal in a
   line. Take content ids from `paywalls list --page-size 100` or `flows list`, and the placement
   from `placements list --page-size 100 --json`. A paywall test belongs on a paywall placement and
   a flow test on a flow placement (the `content_type` of its audiences); on a mismatch say so and
   ask. Find the segment with `segments list --page-size 100`; none matches → make it with the
   `audiences` skill's segment steps, not its placement steps.
2. **Create the draft:** `ab-tests create … --json`. A draft shows to no user, so it needs no
   card. Read it back and say the arms and weights as the user will see them.
3. **Change a draft:** `ab-tests update`, with every flag resent as read.
4. **Start**, only when `state` is `draft` in the read you just made (otherwise see Never), with
   the card. `--placement` and the audience flag name where it runs; planned values on the draft
   change nothing until then.
5. **Change a started test.** Rename or new goal: `update`, which keeps the test, its start time
   and its draw; resend the arms and placement exactly as `get` returned them (arm titles too) and
   pass no audience flag. New arms or weights on a live test: `replace`, with its card. On a
   completed test: create a new test.
6. **Stop**, with the card, when the user names the winner or the other content, or says "no
   content". Ask which if they only say "stop it".
7. **Archive** old tests with the card, one at a time.
8. **Close** with what runs now and one next step. The results are in the dashboard.

## Never

- **Never start a test that is not a draft.** A completed, inactive or archived test would start
  again with the same id, and users who were in it get their old arm again. Say that and offer a
  new test (`get` the old one and `create` a copy), or `replace` for a live one. A live test is
  already running: there is no start.
- **Never run start, stop, replace or archive without the user's yes to the card of this
  situation**, and never on a placement that changed since they saw it.
- **Never put `--yes` on a command the user will run themselves.** It deletes the question the CLI
  would ask.
- **Never write a placement.** No `placements update` or `placements create`, no `--audiences`, to
  start, stop, move or "attach" a test: that write starts and stops tests without a card. Only
  `ab-tests` commands start, stop and replace tests. A placement that does not exist yet is
  `flow-generator`'s or the dashboard's to make.
- **Never run a one-way command without `--yes` to "see the effect".** Build the card from your
  two reads.
- **Never guess an id.** Take each one from a list or a read. Never send an arm id you did not read.
- **Never retry a refused write with changed values to get it through.** Say the server's reason in
  plain words and ask.

## Anything not covered here

`$ADAPTY ab-tests <command> --help` for the flags on the installed version; the `adapty-docs`
skill for any dashboard behaviour. Do not guess a flag, a field name or a URL.
