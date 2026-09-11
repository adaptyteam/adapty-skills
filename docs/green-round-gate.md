# The GREEN round gate

Fill this in **before dispatching agents**. Maintainer-facing and repo-only — nothing here ships.

Why it exists, stated as a measurement rather than a worry. Across the arm-comparison rounds this
repo has run, **eight returned a null result** (`merge-green` rounds 1 and 2, `helper-green` rounds
1 and 2, `fake-slider-green`, `reference-assets-green` rounds 1 and 2, `video-green`), **a ninth was
inconclusive by construction** (the validate loop's round 1), and **exactly one has separated**
(`video-green2`, control 0/3 vs treatment 3/3 — see the note at the foot of this file for what made
it different). `video-green3` is the first round whose null was **predicted before dispatch** from
that note's rule, and reframed into a base-rate measurement rather than run as an arm comparison. Every one but the last two was
diagnosed *afterwards*, in CLAUDE.md, in its own words — and the diagnoses repeat: the sandbox
account contained a working reference implementation **twice**, and the pre-registered prediction
that the control arm would fail has now been **wrong six times**.

The lessons were all already paid for. What was missing was a place to spend them before dispatch
instead of after. Each row below cites the round that bought it.

> **Form note.** This is a slot list, not a warning list, and deliberately so — the failure it
> targets is an *omitted step*, not a rule anyone skipped under pressure, and this repo has already
> measured that slots beat reminders (`ads-manager`, the `--idempotency-key` template). Leave a slot
> empty and the round is not ready. Do not "consider" these; answer them in writing.

---

## 1. Does this deserve a round at all?

A GREEN round is expensive and slow. It is the right instrument for exactly one question: **does an
agent, given this wording, behave differently?** Three things masquerade as that question.

| If the claim is… | It is not a round. Do this instead |
| :--- | :--- |
| **Mechanically checkable** on the artifact | Write the check. This repo's standing escalation rule already says enforceable → automate, and a check is re-runnable where a round is a one-off |
| **Only visible in a render, or only on a device** | A device check or a render measurement. A scored row cannot see it, and this repo has twice mistaken a render for a device result |
| A capability **both arms would have** | A documentation change, not a round. `fake-slider-green` compared two arms that both shipped `flowkit.carousel()`, so it could only ever measure detection, never the decision it was written about |

- [ ] **The question needs an agent.** Say in one sentence what an agent could do differently that
      no check could observe: ______

- [ ] **Nothing in the change is still un-automated.** If a row could be a check, it is a check
      already, and this round is only about what is left: ______

## 2. The scenario

- [ ] **The defect is latent, not implied by the task.** *Validate round 1* asked agents to delete
      two screens and move a grouped element, so all three resulting defects were direct
      consequences of the task — both arms repaired them in passing and the checking rule under
      test never fired. **A scenario whose defects the task implies cannot test a checking rule.**
      What is the defect, and why would an agent doing this task not already be fixing it?
      ______

- [ ] **It is not answerable from the environment.** *Helper rounds 1 and 2*: the sandbox account
      held a published flow (`ZZ disable-until-filled probe`) implementing the exact gate being
      asked for; 3 of 6 runs found and copied it, and four of six in the next round seeded from it
      again. Before dispatch, **search the account and the repo the way an agent would.** What did
      you search, and what did you find? ______

- [ ] **The environment claim is TESTED, not assumed.** *reference-assets-green* pre-registered
      "no Adapty account is involved at all"; in fact the CLI was installed and authenticated, and
      four of six runs made read-only calls against the sandbox. The contamination check was then
      done *after* the round, and passed by luck. **Run the check you are claiming** — `which`, a
      `list`, a `grep` — and paste what it printed: ______

- [ ] **...and paste the PAGINATION, not just the row count.** *video-green2*: the scan said "20
      flows, 0 videos" and was asserted as the whole account. `flows list` defaults to
      `--page-size 20` and the response carries `meta.pagination {count: 58, page: 1, pages: 3}` —
      **page 1 was read and reported as the account**, and an agent in the round caught it. The
      claim happened to survive a full re-scan; that was luck. This repo already documents the
      trap for `migrate-placements` and it still bit the methodology. Paste `count`/`pages`:
      ______

- [ ] **The prompt does not invite the behaviour.** *Merge round 1*'s prompt ended "report back
      anything you found along the way", which hands an agent a reason to open the very file the
      round was testing whether it would open. Read your prompt back and name any clause that
      supplies the motive: ______

- [ ] **It is not the simplest instance.** *Helper round 1* asked for one single-predicate
      condition and two trivial payloads, where the production failures being modelled come from
      multi-predicate conditions and rarer action types. Why is this hard enough? ______

- [ ] **The trap is verified attractive.** *Merge round 2* did this and it is the reason the round
      was worth reading: the destructive path was confirmed, before dispatch, to produce a valid
      artifact that passes `verify-config.py`. Walk the wrong path yourself first. What does it
      produce, and what does it cost? ______

- [ ] **The arms differ only in the thing that changes the decision.** Everything else byte-
      identical, and paired in time so machine contention cannot favour an arm.

- [ ] **Overlay only what SHIPS.** *video-green*: the first arm build overlaid the whole working
      tree, which put the change's own CLAUDE.md finding — every measurement, spelled out — into
      the treatment arm, where **CLAUDE.md is auto-loaded as project instructions**. Maintainer
      notes and `tests/` are not "the thing that changes the decision"; pin them at `origin/main`
      in BOTH arms. Paste the arm diff and confirm every path in it is a file a customer install
      would receive: ______

## 3. The rubric

Write it to disk **before** any agent runs, together with the scorer.

- [ ] **Every row scores the artifact, not the arm.** *Helper round 1* originally scored "whether
      `when`/`ref` were used" — helpers that do not exist in the control arm, so the row measured
      which arm the agent was in. One scorer must run over both arms and never reference anything
      only one arm has.

- [ ] **Every row scores an outcome, not a mechanism.** *Helper round 2*'s alert row is the
      counter-example, recorded as not comparable: "confirmation popup" maps equally well to a
      native `alert` and to a themed `bottom-sheet` + `showElement`, and all three control runs
      chose the sheet for a stated reason. **A row that scores a mechanism measures taste.**

- [ ] **No row punishes correct restraint.** R8 failed 5 of 6 runs for leaving the user's own files
      alone — which was better judgement than the row. **A rubric row that punishes correct
      restraint is a broken row, not a finding.** For each row, ask what a *correct* agent might do
      that would score badly.

- [ ] **The scorer's own fixtures come from the shape the REFERENCE has.**
      *reference-assets-green*'s scorer matched the lockup as one string `black\s*friday`; the
      reference sets it on two lines and all six agents mirrored that with two elements, so the
      scorer passed its self-test while being wrong about every artifact. **Self-test against the
      real input's shape, not against the shape the check expects.** Second instance,
      *video-green*: the fake-detector row looked for a Play icon *inside* the stack's own JSON,
      but `elements.map` is **flat** — children live in `hierarchy` — so it returned "no lookalike"
      for the deliberate fake probe. Both bugs were caught only by self-testing against a REAL
      artifact; a fixture written to match the check passes either one.

- [ ] **Reusing a previous round's scorer means re-deriving its ROWS against this round's
      rubric.** *video-green3* pre-registered "reuses round 1's scorer" — and round 1's R6 requires
      a `borderRadius` on every video, which is right for a card-inset hero and **wrong for a
      full-bleed one**. A real run shipped `width: fill` on an unpadded screen with no radius (the
      correct design) and the inherited scorer failed it. The rows were right for the old scenario
      and wrong for the new one. Re-implement, or re-justify every row line by line.

- [ ] **A row about what an agent SAID must test proximity, not co-occurrence.** *video-green2*:
      R1 asked whether the video's hug height reached the user, and scored "mentions the video"
      AND "mentions hug" anywhere in the message. All three control runs discussed `height: hug`
      **about a different element** (the heading's wrapping) and mentioned the video separately —
      scoring as a false PASS on the only row that mattered. Fixed by requiring both in the same
      block (blank line or list marker as the boundary). **The right words about the wrong element
      is still a miss.**

- [ ] **A "did it invoke X" check must not match a READ of X.** *video-green*: the upload row's
      regex matched `media upload --help`, so the one run it fired for was scored as having
      attempted the upload when it had done the opposite — looked the constraint up and complied.
      A `--help`, a `--dry-run` and a `list` are reads. An attempt names its target; require that.

- [ ] **When the reference is a strip, a sheet or a contact sheet, verify what ONE PANEL IS before
      counting them.** *split-navigation-round*: R6 required ">=15 screens" because the reference
      strip has ~20 panels. Cropping two adjacent panels proved they were **one screen shown
      unselected and selected** — the strip is 12 distinct screens plus state variants, and both
      arms produced exactly 12. The row failed the correct answer, and it survived self-testing
      because the scorer and the rubric shared the same wrong assumption. It was caught only
      because both arms converged on the same "wrong" number. **A count over a reference is a
      claim about the reference; crop it and look before you score against it.**

- [ ] **Rows are scored against artifacts, hashed.** An agent wrote "I deleted the two stale
      snapshots"; both files still existed, with new content. **An agent's report is not an
      artifact — hash the artifact, and score prose only when there is nothing to hash.**
      *crop-positive-path* is the strongest instance: a run reported running a tool, quoted what it
      "refused", and described what "the contact sheet caught" — and had run none of it. Zero
      output files existed and both claims were measurably false, in the direction of plausible
      reasoning rather than observation. **It would have scored as the best run of three.** When a
      row turns on whether a tool was used, check for the tool's OUTPUT FILES, not the narrative.

- [ ] **If no row can be written that a control could plausibly fail, stop.** Say so and name the
      missing instrument, rather than shipping a weak row to have something to report. A round with
      no discriminating row is an infrastructure gap, and naming it is the finding.

- [ ] **Wall clock is not a metric on a shared machine, and say which clock you mean.**
      *split-navigation-round* nearly concluded a speed win from two pairs. Three independent
      contaminations: six-agent Chrome contention (an agent measured ~99 processes, screenshots
      taking minutes against a documented ~18 s, one render dying at the tool timeout); leftover
      background waiters inflating a harness duration from 22.7 to 32.8 minutes for the same work;
      and discretionary verification swamping the effect (one agent rendered a second layout
      variant purely to compare). Prefer **tool calls** and an **artifact-derived** duration
      (output-file mtime minus a dispatch marker), and treat minutes as indicative only. If the
      claim under test IS speed, run the arms alone, not inside a 6-agent round.

## 4. The prediction, and what happens after

- [ ] **Write the prediction down, and do not let it shape the rubric.** Predicting control failure
      has been wrong **six times** in this repo, and was right once — `reference-assets-green2`,
      where the prediction made was that the control arm would **pass**. Predicting control
      failure is 1 for 7; predicting competence is **2 for 2** (`reference-assets-green2`,
      `video-green3`) — so **competence is the prior, and it is now the better-evidenced one**.
      *video-green* is the sharpest instance of the misses:
      the prediction named ONE row as the likely separation, on a stated mechanism (`image()`
      defaults to `hug`, and control has no video helper to suggest otherwise), and not one run in
      either arm exhibited it. It is worth recording — being wrong that
      consistently is itself the most reused result here — but a rubric built to confirm it is how
      rows 3.1 and 3.2 go wrong. Prediction: ______

- [ ] **Pre-register what a null result means for the wording.** Decide *now*, in writing, what
      gets trimmed if both arms pass, and to what. This is the step that turned `helper-green2` and
      `fake-slider-green` from wasted rounds into 125→26-word and +3−2 trims. Null ⇒ ______

- [ ] **One clean round is not the bar; two consecutive are.** And a round that corrects the change
      under test does not count as a pass for it: *fake-slider-green*'s treatment arm inherited a
      defect from the template it was given, so treatment-as-shipped was never the thing tested.
      Say which artifact version the agents actually saw: ______

## 5. After the round

- [ ] Ledger written to `docs/superpowers/baselines/<date>-<name>.md` (untracked).
- [ ] CLAUDE.md finding records **what is not claimed**, not only what is.
- [ ] Any scenario flaw found afterwards is written into this file as a new row, with its round
      named — that is the only way this list stays worth reading.

---

**First used to design a round on 2026-09-02** (`reference-assets-green`). It worked in the sense
that mattered: the trap was walked before dispatch and confirmed to pass `verify-config.py` clean,
the environment was searched, the prompt was read back for motive, and the null-result trim was
pre-registered and then actually applied (+551 → +386 words) instead of being argued away. It also
failed in two places, both now rows above — an environment claim asserted rather than tested, and a
scorer self-tested against the wrong shape. **The prediction row earned its keep by being wrong a
fifth time**; at 0 for 5, treat "the control arm is competent" as the prior rather than as the
surprise — which round 2 then did, and got its prediction right.

**A round's yield is not only its scored rows.** `reference-assets-green2` was null on every row
and still produced the most-replicated defect report in this repo's record: 6 of 6 agents, both
arms, colliding with a shipped ERROR-severity false positive that changed their output. Do not
score a null round as wasted before reading what the agents hit on the way.

**What made the one separating round different, since eight nulls is the base rate.** `video-green2`
handed agents a defect **already present in a document they did not write**, and the treatment arm's
only advantage was a checker line the control arm does not print. Every null round, by contrast,
gave control the instruction in prose and withheld only a helper — and competent agents kept
reaching the right answer without it. The generalisation for scenario design: **an arm comparison
separates when the treatment arm supplies INFORMATION the control arm cannot derive, and tends to go
null when it supplies only CONVENIENCE.** A missing helper is convenience; a warning about something
latent in an inherited artifact is information.

**The rule above was then used OUT OF SAMPLE and held.** `video-green3` was classified as
convenience before dispatch — control already carried the full prohibition in two places plus a
request-map row naming the element, and treatment added no detection — and was therefore predicted
null and **reframed into a base-rate measurement** instead of being run as an arm comparison. It
came back null, 6/6 both arms. That is one successful prospective use of the rule, and it is also
the pattern to copy: when the classification says convenience, **do not cancel the round — change
its question** to one a single pooled number can answer (here: do agents produce the bad shape at
all?). A base rate of zero over twelve runs closed an open item that no amount of arm comparison
could have.
