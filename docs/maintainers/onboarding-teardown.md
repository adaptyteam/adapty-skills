# Maintainer notes: `onboarding-teardown`

Evidence and history behind the rules in `CLAUDE.md`: measurements, test rounds, dated findings. Not loaded into sessions. Read the part you need before changing a rule; add new findings here, never to `CLAUDE.md`.

## Files

- `plugin/skills/onboarding-teardown/SKILL.md` — the onboarding skill's entry point. Adapted from Adapty's growth-team `onboarding-teardown` skill; the upstream half is the six-question interview, the contradiction rules, the seven-part output and the framing rules. The additions here are the **config/render input forms** with the read-the-config-instead-of-interviewing table, the **two directions** (Audit / Design) on the same observable predicate `paywall-teardown` uses, `## Choose the flow skeleton first` (six skeletons gated on observable prerequisites), `## What you cannot invent`, the split of upstream's combined sign-off into a **translated, fixed-meaning disclaimer** plus **a next step chosen by input** (build offer, make-the-changes offer, or the builder pitch), and the two-way link with `flow-generator`. See finding 28.
- `plugin/skills/onboarding-teardown/references/patterns.md` — the pattern library: 8 contradiction rules that fire on *combinations*, patterns by section, and 8 category playbooks. **Vendored byte-for-byte from upstream and kept that way**, the same rule `paywall-teardown/references/patterns.md` follows and for the same reason: a growth-team revision lands as a one-file diff. Every repo-specific fact therefore lives in `SKILL.md` or `references/categories.md`, never here.
- `plugin/skills/onboarding-teardown/references/categories.md` — repo-owned, not vendored: how long each category's onboardings run (fitness and sleep 20–50 screens, photo/AI 5–15, utilities 3–6; education says "long" with no number because no source gives one), how traffic temperature moves length, the screens that fill a long flow without promising a computed plan, and the rhythm (at most three questions in a row; variety comes from changing screen type, never from restyling one).

## Conventions and findings: `onboarding-teardown`

- **This skill is vendored, not authored here**, the same arrangement as `paywall-teardown`. It
  came from the growth team and the library is theirs. `references/patterns.md` is **byte-identical
  to the upstream file** and must stay that way, so their next revision of the contradiction rules,
  the impact tiers or the category playbooks lands as a one-file copy rather than a merge. Every
  repo-specific fact therefore lives in `SKILL.md`. When an impact range or a playbook changes, it
  changes upstream first.
- **The two skills split on one line: `paywall-teardown` owns a SCREEN, this one owns a SEQUENCE
  and the SEAM.** Plan cards, price display, savings framing, CTA and proof placement are theirs;
  flow length, branching, goal capture, the personalization payoff, loader placement, permission
  timing and whether the paywall reflects what onboarding captured are this skill's. Run both on a
  flow that is both, and do not duplicate rows. The boundary is stated in three places at once —
  both scope sections and `flow-generator`'s routing table — because a skill that answers a
  question it cannot see is exactly the failure `paywall-teardown`'s "reason only from what you
  were given" rule already guards.
- **The skeleton table is the mirror of the archetype table, and it exists for the same structural
  reason** — but say what that reason is, because it is not the same evidence. Read forward, the
  library's highest-value entry is the personalization loop, and its contradiction rule fires on
  *every* flow you author, since "no personalized result exists" is true by construction before
  you build anything. So an agent that starts at the pattern list emits quiz → loader → "your plan
  is ready" → paywall every time, **including on apps that cannot back the promise — which is
  rule 1's own failure, built deliberately.** On the paywall side the equivalent inertia was
  *measured*, twice, in unrelated verticals; here it is reasoning about the library's shape, and
  `SKILL.md` says so in a parenthesis rather than borrowing the measurement. Do not upgrade that
  sentence to a claim.
- **The interview must not run inside a build, and that is a wiring rule, not a style note.** The
  six questions are the skill's front door when a user brings it a flow. Invoked from
  `flow-generator` phase 2 there is nobody mid-build to run six turns at, so they are answered from
  the brief, the config and the catalog, and the remainder becomes one batched ask. Both call sites
  say this. Without it, adding the skill to the generator would have made every build stop and
  start a questionnaire — a contradiction introduced by the wiring rather than by either skill.
- **Upstream's sign-off was SPLIT into a disclaimer plus a next step**, matching
  `paywall-teardown` (`## The next step` in both). The disclaimer is unconditional, in the user's
  language, meaning fixed. The next step is chosen by an observable input, not by taste: a config or
  render gets an offer to make the changes and no builder pitch (that user is already inside the
  builder); a description, screens or a competitor gets an offer to build it now with
  `flow-generator` plus a one-sentence pitch; the pitch alone when the agent checks and finds no
  `flow-generator` sibling or no shell. That check is a check, not a belief — measured: told only
  "where you cannot build it", an agent with no `flow-generator` offered to build anyway.
- **A config answers most of the six questions, and asking anyway is the worst version of the
  re-asking failure the interview rules already name** — the answer is in a file you were handed.
  `SKILL.md` carries the field-by-field table. The two things a config genuinely cannot say are the
  **category** and **whether the app really delivers the payoff the flow promises**, and the second
  is rule 1's whole hinge, so it is the one thing that always survives into the asks.

### Finding 28 (2026-09-01): adding the skill exposed two real defects, and both are the class this repo keeps re-learning

**A flow CANNOT request a permission, and that turns contradiction rule 3 into a handoff.** Read off
the published schema rather than assumed: there are **15 `IAction*` definitions** — `alert`,
`closeFlow`, `conditional`, `custom`, `hideElement`, `navigate`, `navigateBack`, `navigateNext`,
`nothing`, `openUrl`, `purchase`, `restorePurchases`, `selectProduct`, `setVariable`, `showElement`
— and none of them is a permission request. So the library's permission-timing pattern, which is a
CR +10–15% item, is **not buildable by the builder at all**: the flow can render the pre-permission
soft prompt and fire a `custom` action, and the app makes the system call. `SKILL.md`'s
`## What you cannot invent` states it as a hard `No` with the enumeration attached, so nobody
re-derives it from the pattern's presence in the library. This is finding 15's class read forward:
the recommended path led into a capability that does not exist.

**`flowkit` could not express a personalization payoff at all — finding 12, again, on the single
highest-value pattern in the library.** Conditional text is how an onboarding echoes the user's own
answer back, and there was no helper for it, so the only reachable "personalization" was a stack of
elements with `visibility` conditions. **`switch_rich()`** now emits it, with the shape taken from a
real builder export (`bf5d731e` in the sandbox app) rather than the schema: the `switch` nests
**inside** each locale, cases are `[condition, const]` pairs, and every locale carries its own full
copy of the expression — so **parity is per branch**, which is what `SKILL.md` already told users
and what nothing could produce.

**And the helper would have shipped with a hole, which a measurement caught.** `config()`'s
condition-variable resolution pass walked `props.visibility.condition` and `states[].condition` and
nothing else. Measured against the live service (2026-09-01, `adapty` 0.8.1, the sandbox app): a
conditional-text switch on a group that exists returns `valid: true, issues: []`; the identical
document with the variable renamed returns **`valid: false`, "Generated scripts failed validation",
with `code` and `path` both `null`.** So a conditional-text predicate is **compiled**, exactly like
a visibility condition, and is fatal — the **opposite severity** from a `variable` *span* in the
same `props.content`, which renders its literal token and publishes. Two shapes, one property, and
only one of them compiles. The pass now walks any localizable value whose per-locale content is a
`switch`; negative-tested by deleting the walk, which reddens exactly one case.

**`flow-audit` false-blockered on the shape, and it is the THIRD instance of one trap in one
function.** `_has_content` reads richtext-shaped nodes, so a per-locale value that is a `switch`
looked like no content at all: a real 6-screen onboarding came back **`NOT READY FOR PRODUCTION —
1 blocker: empty translation`**, naming the three fields that make up its payoff. Its own docstring
already recorded the two earlier instances — variable-only content (every price on every paywall)
and per-locale image objects (two real fixtures) — so the shape of the bug was documented and the
new value shape walked straight into it. Worth stating plainly: **the read-only auditor put a
blocker on the exact screen the sibling skill exists to produce.** Fixed by recursing the branches
rather than accepting the type, so an all-empty switch still counts as empty; both directions are
pinned in `tests/test-audit-flow.py` and the fix is negative-tested.

**One limitation was accepted rather than fixed, and it is labelled in the code.** `flat_text` still
returns `''` for a switch, so a conditional field stays invisible to the `same`-as-base parity count
and to every other check that reads visible text — the price-literal and store-review checks
included. Widening `flat_text` reaches checks calibrated against measured false positives, so it
needs its own calibration rather than a ride on this one.

**`flowkit.spinner()` was the third missing helper**, found the same way: `patterns.md` tells an
agent to build a loading screen from `loader-spinner-label` and *forbids* substituting a static
`icon` for the spinner, and there was no way to emit a `spinner` from the module. The helper fixes
`icon.type` to `custom` (a phosphor spinner is a 422) and its docstring carries the two facts the
field names contradict: `duration` is the **rotation period**, not a delay, and the element **draws
blank in `config preview`** — the timer beside it is what moves the flow on.

**What WAS tested: a live end-to-end build of three onboarding flows in the sandbox app, and what was
NOT: any GREEN round.** The three were built through `flow-generator`'s five phases with this skill
in the Design direction, deliberately in three categories that force three different skeletons —
Wellness (**personalization loop**, `524e9930`), Productivity (**value walkthrough**, `d11d4711`),
Education (**problem → method**, `30bd5a3c`). All three pass `verify-config.py` and
`flows config validate` (`valid: true`), render on every screen, round-trip byte-identical through
`config update` → `config get`, and audit to `READY, PENDING` with only the Android-binding question
outstanding. The conditional-text echo is **visible in the renders**, which is the end-to-end proof
that `switch_rich` works. Two defects were caught by the skill's own pass 3 over its own output —
an ask leaking into product copy as a benefit row, and a mixed step-marker style — which is the
pass doing the job it exists for. **But one author running the skill is not an arm comparison**, and
per the Iron Law and [`docs/green-round-gate.md`](docs/green-round-gate.md) every behavioural claim
here is open. **The scenarios to run**, and note the account now contains three reference
implementations, so gate row "a scenario must not be answerable from the account the agents can
read" applies and these must be run elsewhere or against a different vertical: (1) ask for an
onboarding for an app that **cannot** back a personalized promise, and score whether the loop is
ruled out on its prerequisite or built anyway; (2) ask for a permission-priming step and score
whether the agent reports the handoff or invents an action; (3) hand an agent a flow config and
score whether it interviews anyway.
