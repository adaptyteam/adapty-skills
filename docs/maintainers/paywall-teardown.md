# Maintainer notes: `paywall-teardown`

Evidence and history behind the rules in `CLAUDE.md`: measurements, test rounds, dated findings. Not loaded into sessions. Read the part you need before changing a rule; add new findings here, never to `CLAUDE.md`.

## Files

- `plugin/skills/paywall-teardown/SKILL.md` — the paywall skill's entry point. Owns the **two directions** — audit a paywall someone else will change, or *design*, which is entered on an observable predicate (**no design reference was given**: no reference image, no screen to copy, no layout spec) and runs two passes, the second of which grades and corrects the agent's own render — the three input forms (screenshot / `flows config preview` render / flow config), the internal four-step process, the two output formats, the fixed-meaning disclaimer, the next step chosen by input, and the framing rules that keep the numbers honest. Adapted from Adapty's growth-team `paywall-teardown` skill shipped on claude.ai; the additions here are the render/config inputs, the design-brief direction, the `## What you cannot invent` section, and the two-way link with `flow-generator`.
- `plugin/skills/paywall-teardown/references/patterns.md` — the pattern library: 15 patterns plus category playbooks, each with when it applies, its cross-check, its impact tier and its category-level grounding. **Kept at that filename deliberately**, matching the upstream skill so a growth-team update to the library copies in as a one-file diff — even though `plugin/skills/flow-generator/references/patterns.md` is a different file about layout composites. They never own the same fact: conversion patterns and impact numbers here, JSON skeletons there.
- `plugin/skills/paywall-teardown/references/look.md` — repo-owned: how a screen you design looks, and it covers the whole flow when an onboarding ends on the paywall. Owns three rules in order: **the app's design comes first** (code, flows, screenshots or a given brand set the style, and no look is invented — a neon-on-black app gets neon on black); **with a brand, invent only the layout** (question layout, paywall composition, signature element); **with no design, invent the whole look** — four concepts from the app's own world, drop the most obvious, roll among three with a `python3` command. It also owns the two looks nobody chose (white + one accent; near-black + one neon) and the design system every screen is built from (named colours, five type presets, exactly three radii, one spacing scale, one component per screen type, the paywall in the same system).

## Conventions and findings: `paywall-teardown`

- **This skill is vendored, not authored here.** It came from the growth team's claude.ai skill and the library is theirs. Keep repo-specific additions in `SKILL.md` and keep `references/patterns.md` as close to upstream as possible, so their next revision of the library lands as a clean copy rather than a merge. When a pattern's impact range or cross-check changes, it changes upstream first.
- **The impact numbers are priors, and inflating one is the failure mode.** Every range is expected effect calibrated from teardowns, never measured lift for the user's app — which is why the disclaimer is verbatim and non-optional. The single most common defect is assigning a redesign-sized number to a copy tweak; the tier table at the top of the library exists to stop exactly that. Never add a range that is not in the library.
- **Never name a company.** Grounding is category-level only ("near-universal", "common in top fitness apps"). Naming an app critiques a brand Adapty may be selling to.
- **The next step is chosen by an observable predicate, not on tone.** For something the user cannot yet edit (a screenshot, a competitor, a design) it is an offer to build the paywall now with `flow-generator`, then the builder pitch as one sentence — the pitch alone when no `flow-generator` sibling or shell exists; for a flow config or a `flows config preview` render it is the offer to make the rows, never the pitch, because that user is already inside the builder. The no-close-button row carries flow-audit's reason only: agents in both teardowns added an unverified "store review may reject it" until the rule forbade it. Written as a conditional rather than a preference on purpose — a preference gets negotiated away in both directions.
- **`## What you cannot invent` is the safety content, and it is repo-specific.** The upstream skill talks the user out of *reporting* invented stats; here the same skill can feed a generator that *ships* them into a live flow, which is a different blast radius. Its table maps each pattern to what the config can build versus what only the user can supply, and it delegates every mechanic (`old-price`, `_meta.icons`, empty asset maps, variable producers) to `flow-generator` by name rather than restating it. Keep it that way: this skill owns conversion claims, `flow-generator` owns the JSON.
- **The trigger is a predicate, not a vibe.** An earlier draft keyed both call sites on an "abstract brief", which is a judgement the agent makes about the user's tone; it is now keyed on *was a design reference given* — an image, a screen to copy, a spelled-out layout — because that is checkable and because it also catches the ordinary case the word "abstract" misses: a plain "add a paywall screen" where the agent silently picks the whole design. Corollary that must stay attached: **a reference that was given outranks the library**, or the skill starts overwriting the user's own design with its priors.
- **In Design the findings are corrections, not advice.** Pass 2 exists because a screen the agent designed and then merely *reported on* ships every defect it named. The wording — a finding on your own draft is a defect; never hand over a screen with a table of the patterns you skipped — is the whole point of wiring this skill into a generator rather than leaving it a standalone reviewer.
- **The library ranks elements, not compositions, and that produced one screen shape twice.** Read forward, `patterns.md`'s highest-impact entry — the free-vs-paid comparison table — has a `when` clause ("no comparison exists on screen") that is true **by construction** on anything you author, so it fires every time; the rest of the top of the list is plan-card machinery. Measured: two live builds in two unrelated verticals came out as the same comparison-table-over-plan-cards screen, and the proximate cause was a build script copied forward rather than a judgement. Hence `## Choose the archetype first`: seven named compositions, each gated on an **observable prerequisite** (an uploaded asset, a verified intro offer, plans differing only by period), chosen **by the skill and disclosed**, never put to the user as a question — the same reason every other decision in this repo is a named-and-disclosed choice rather than a prompt. Two clauses in it are load-bearing and were added from the same run: a missing prerequisite **rules an archetype out** rather than licensing a placeholder (an image you cannot upload is not an archetype; a trial timeline with no verified offer is a fabricated offer), and **the same archetype twice in a row is a smell** to check against inertia.
- **The two-way link is load-bearing in both directions.** `flow-generator` phase 2 asks who chose the design and invokes this skill when the answer is the agent, putting its asks to the user before any JSON is written; phase 4 runs it over the render and *applies* the Fix-first and High rows, while a correction still costs a screenshot instead of a `config update`. Delete either call site and the pair silently degrades to what it was: a generator with no taste, and a teardown with nothing to tear down.
- **Untested by subagent, and that is recorded rather than hidden.** The Iron Law in `superpowers:writing-skills` wants a baseline round before the content lands; this skill's repo-specific additions have not had one, because the session that added them was instructed not to dispatch agents. The upstream half arrived already in production use. Treat a GREEN round over the design-brief direction and the two `flow-generator` call sites as the open follow-up, and the highest-value scenario is the one this skill is armored for: "add a paywall screen" with no reference attached, where the agent has no real rating, no real outcome data and no hero asset — the round should score whether pass 2 changed the config or merely described it.


### Finding 55 (2026-10-12): taste in Design mode — category length, invented looks, one design system

A team thread said builds with no reference looked typical and alike. Six RED builds on `main`
(fitness ×3, document scanner ×3, local only, rubric pre-registered) confirmed it: fitness flows
were **6 screens 3/3** (category runs 20–50) of single-choice cards, and **6/6 shared one layout**
— eyebrow, bold heading, icon-in-tinted-square rows, full-width button, empty image box — with
only the accent swapped; **6/6 paywalls were two plan cards**, 5/6 with a trial timeline. The
fitness runs went short because each ruled out a computed plan and then had nothing honest to fill
a long flow with. Fixed with `onboarding-teardown/references/categories.md` (length by category,
14 honest screen types, the rhythm) and `paywall-teardown/references/look.md`, over five GREEN
rounds (ledger `docs/superpowers/baselines/2026-10-09-teardown-taste-red.md`, untracked):

- **Length and mix:** fitness 20–21 screens with 9+ screen types in every round after the change;
  sleep 20; utilities stayed 4. Education has no sourced length, and one language run stopped at
  11 against an unsourced floor of 12.
- **Look, and the lesson worth keeping: each fix created the next default.** "Not the white
  template" became **near-black + one neon accent 6/6** across fitness and scanner alike; a menu
  of seven directions picked by "best fit" converged **within every prompt 4/4**; a rolled menu
  varied fitness but a "night-time use" override sent every sleep roll to Night. What finally
  varied the same prompt was **inventing four concepts from the app's world, dropping the most
  obvious, and rolling among three with a shell command** — a model asked to pick at random picks
  its favourite. Round 5: three sleep builds, three different invented looks (linen/lavender,
  sea-teal/sand, plum/honey), two paywall compositions. Concept pools overlap across runs; the
  roll is what spreads the picks.
- **App design first** (owner's call): neon on black is right for an app that looks like that.
  Round 5's three builds with a stated black/volt/square brand all followed it with no roll. **Not
  run:** the layout-invention step for brand-given builds, added after round 5 because those three
  builds shared one paywall and one layout.
- **Consistency:** flows in rounds 3–4 used 6–13 corner radii; with the design system 5/6 stay
  within three. A radius-count checker was **ruled out on calibration** — real builder exports
  already use 3–6 values. Same-type option identity is a prose rule plus a side-by-side back-pass
  check, not mechanical.

**Bycatch, each its own fix:** the timeline rail hidden behind a filled card (PR #126); input text
unreadable on dark screens (no input text colour); typed prices from the request (2 runs); the
render page's maintenance banner over every render, which `shoot.sh`'s guard does not catch.

### Finding 56 (2026-10-16): variety without a reference — each fix moved the sameness one level up

Paywalls with no reference, built unattended through `flow-generator`, local only plus image
uploads to a test app. 27 builds for an invented pony-themed to-do app (with a code theme, and
README-only) and 6 for an invented small-business AI advisor (README-only). One build per
independent agent, judged by eye from the renders; no arm comparison, so this is a run log, not a
measured treatment effect. What each round showed, and what it moved:

- **Layout ideas redrew only the benefit block.** Six builds before the change rolled six
  different concept names and shipped one screen: header, value block, plan cards, button, fine
  print. Now each concept is four answers (what the screen is, top half, where the plans live,
  where the value lives) and two concepts must differ in both the top half and the plans.
- **A rule checked on the written concept is passed by rewording it** ("the table *is* the top
  half"). The back pass now asks the four questions of the screenshot, and the obvious structure
  on the render is *Fix first*, rebuilt and never redescribed.
- **Different made it worse-looking:** the easiest way off the obvious structure was more boxes.
  Added the quality rules in `look.md` (one focal element, card treatment only on what is tapped,
  each thing said once, every part of the screen designed — filled or framed on purpose; the owner
  rejected "leave space empty" as a rule). Character concepts draw the character as one uploaded
  illustration, never an icon on a coloured circle; before that rule 0 of 19 builds drew
  anything, after it every scene did.
- **A concrete scene recipe became the new template** (sky, subject bottom-left, floating chips,
  plans on a ground band: 6 of 7 scenes). Replaced by principles plus a viewpoint choice.
- **The concept list itself converges per app, so the roll does not spread.** All three advisor
  builds rolled "ledger page", because it was in every list. Each concept now starts from a
  random starting point drawn by a command before any concept is written; the rerun gave a
  certificate, a till receipt and a Monday-morning brief.
- **Content sliced by the pinned bar** persisted at High (3 of 6 in one round); now *Fix first*.
- **Trial wording from a README** appeared once (1 of 9) after plan cards gained a slot; a row in
  both teardowns' "cannot invent" tables now says a planned trial is not an offer: when the
  catalog shows none, ask whether it exists and suggest one, and only an unanswerable run leaves it
  out with the question in the reply.

**Contamination of mine, worth the warning:** from round 5 the scene recipe's example objects
were the test app's own content (a dye pot, a saddle, a second pony), and every scene then drew
exactly those. Examples in shipped guidance are now from a different app (plant care). **Never
write a test fixture's own nouns into the guidance under test.**

**Added after these rounds, untested:** the obvious structure now also names the market's default
parts (short headline, checklist, two plan cards with annual pre-selected, a trial-naming button,
a cancel line, no image), taken from a survey of 100 top iOS paywalls that describes what is
common, not what converts; a six-word headline limit in the quality rules; and a trial-or-product
decision before the archetype. Two rounds (ledger `docs/superpowers/baselines/2026-10-16-default-anatomy-green/`, untracked; three apps, README only, 7 builds per arm): the market default came out in 4/7 control and 2/7 treatment builds, headlines of six words or fewer in 5/7 and 7/7, and with a confirmed trial (or a confirmed none) the screen sold the right thing in 3.5/4 and 4/4. Every row leans treatment and none separates, so the wording stays and no behavioural claim is made for it. Control led with value on the no-trial app unaided, 2/2. Treatment replies stated the trial-or-product choice 4/4 in round 2 (0/3 in round 1, where no trial could be confirmed).

**Calm looks (2026-10-19), untested beyond one run per app.** An old-versus-new comparison on three
fresh README-only apps (a travel phrasebook, dog training, a shared budget) showed the new skill
varied every screen but made two of three loud: a fridge door of notes in five colours at uneven
heights, a drawn dog plus a six-stop trail plus a third accent. The one that worked carried its
idea in one element (a split-flap headline) and kept the rest ordered. `look.md` now adds four
rules: one idea in one place, few colours, everything on one grid, and content before decoration
on a screen with a pinned bar (value pushed below the fold by an empty decorative shape is cut
first). Re-runs came out as one illustration over plain rows and an enrolment form; the second is
close to the comparison-table default, which is the trade-off to watch.

**The standard layout is offered, not banned (owner's call, 2026-10-19).** The 100-paywall survey
shows what is common, not what converts, and an invented look has no conversion data either. So
the obvious concept stays out of the build but the reply offers it as the version to A/B test
against. Untested.

Bycatch fixed: `crop.py` wrote every crop fully opaque, so trimming a transparent drawing gave a
black box (test added, red against the old code); the missing-assets block listed a drawing the
agent had already uploaded as missing (held in 4 of 5 replies afterwards). **Not tested:** any of
this on an onboarding — `onboarding-teardown` gained the back-pass and trial rows by pointer only;
the advisor variety is one round of three; and uploads in these runs left unused images in the
test app's media library, which the CLI cannot delete.
