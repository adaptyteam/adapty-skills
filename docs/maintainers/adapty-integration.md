# Maintainer notes: `adapty-integration`

Evidence and history behind the rules in `CLAUDE.md`: measurements, test rounds, dated findings. Not loaded into sessions. Read the part you need before changing a rule; add new findings here, never to `CLAUDE.md`.

## Files

- `plugin/skills/adapty-integration/SKILL.md` — the skill entry point. Phase-by-phase flow: state tracking → setup (docs-fetching rules, session marker) → project analysis → three user questions → dashboard setup through the Adapty CLI → staged, per-platform implementation → closing review. Platform-agnostic on purpose; per-platform details belong in references.

- `plugin/skills/adapty-integration/references/<platform>.md` — one per platform (`ios`, `android`, `flutter`, `react-native`, `unity`, `kmp`, `capacitor`) plus `store-setup-{ios,android}.md (store products and the store↔Adapty connection only; the sandbox purchase itself moved to `purchase-testing`)`. Code snippets and the exact docs URLs the agent fetches before writing each piece of code.
- `plugin/skills/adapty-integration/references/migration.md` — the cross-platform migration spine: source detection, mapping rules from another purchase system's concepts to Adapty's, and the `ADAPTY_SETUP.md` handoff contract. Injected on every run where `migrationSource` is set, alongside the platform reference; kept lean on purpose, since a headless run can't skip past padding. `references/migration-<source>.md` (currently `migration-revenuecat.md`) adds source-specific mapping and is also cross-platform; its section 5 is a 33-row triage table of RC→Adapty behavioral divergences, each row keyed to a grep-able RC signal and ending in **restructure** or **drop**. The third verdict, **swap**, is deliberately kept out of the table — a divergence that resolves at the call site lives in the deep file only, so the always-injected half stays limited to work an agent cannot do without leaving it. Three rows are keyed to the **absence** of a call rather than its presence — no fallback file, no `AdaptyUI.activate`, no preload — because RC has no counterpart to grep for and a call-site-to-call-site mapping therefore skips them silently. Ten files are the odd ones out, loaded **on demand only** and never injected by default. Eight are the RC topic files — `references/migration-revenuecat-{activation,identity,placements,entitlements,purchases,observer,attribution,gaps}.md`, 60–110 lines each — reached from the triage table, whose verdict cell names one of them (`Restructure → placements`). They carry the reasoning, the architectural options, and the per-gap staleness checks that the always-injected table states in a single line, which is the whole point of the split. **They were one 658-line file until the load unit was fixed:** an agent reads files, not headings, so a `§N` pointer into one big file made every matched row cost all eight topics. One file per topic makes the load unit equal the decision unit — a typical run reads 250–350 lines instead of 658, and a run that touches all eight is no worse than before. Adding a topic means adding a file plus a legend row, never growing a shared file. The other two are `references/migration-architecture.md`, when a call site has no one-to-one Adapty equivalent; and `references/migration-flow-rebuild.md`, when `paywallApproach` is `flow_builder` — the user's own Phase 2 answer, never inferred from the source having a builder paywall — and the paywall being replaced is hand-built or came out of the source's visual builder (RevenueCat's Paywall Editor, presented through RevenueCatUI) — the one migration that retires the paywall instead of rewiring it. That file owns the two rules the spine can't state generally: no CLI-created placements on such a run (the flow needs those developer IDs), and the rebuild spec is in hand before any code changes — extracted from the code for a hand-built screen, asked for as screenshots (each plan state, other locales as text, original assets, the offering ID) for a source-builder paywall — because that spec is the brief `flow-generator` builds the flow from (and the user's rebuild brief when it cannot run). The file maps no builder elements itself — `flow-generator` owns that, and hands back what the format cannot reach for the user to decide on.

**Every CLI call in every skill goes through `$ADAPTY`, resolved once per run — never a bare `adapty` and never a bare `npx` at a call site.** The default resolution is `npm i -g adapty@latest`, with `npx --yes adapty@latest` as the fallback where the global prefix is not writable. **`flow-audit` is the one exception and resolves `$ADAPTY` straight to the npx form, installing nothing** — it is read-only and makes six calls, so the wrapper's cost is noise and `npm i -g` would be the only thing an audit writes to the user's machine; every other rule in this paragraph still applies to it. Elsewhere the skills release with the CLI, so the install is what keeps a run off a stale global binary: a GREEN round found a machine's `adapty/0.3.0` and 3/3 agents concluded two commands did not exist. **Do not wrap each call in `npx` instead** — measured, the wrapper costs 0.73-1.40 s per invocation against 0.07 s installed, and a run makes dozens. Two supports belong in the skill beside the block, because both read as a missing CLI: `--yes` is not optional on the fallback (npx otherwise stops to ask permission to install, and a headless run has nobody to answer), and `zsh` does not word-split a multi-word `$ADAPTY`, so `command not found: npx --yes adapty@latest` is a shell problem. **And `@latest` is not where an unreleased command lives**, which is the opposite of the intuition: `flows publish` and `flows update` shipped in `0.8.3-beta.0` and `beta.1`, were **absent from the `0.8.3` release**, and returned in `0.8.4-beta.1`. So a command is declared missing only after `--help` says so, plus one `npx --yes adapty@beta` attempt — never from a version number, and never behind a numeric floor.

The bullets below apply to `adapty-integration`; the `ads-manager` section further down adds its own.

- **Docs URLs are load-bearing.** SKILL.md forbids the runtime agent from guessing slugs — it may only open URLs written in the skill or found in a fetched `llms.txt` index. So every docs URL you add must literally exist (the link lint enforces this); never assemble one from a topic and platform name.
- **The session marker matters.** SKILL.md tells the runtime agent to mint a random `sessionToken` and tag every docs fetch with `?ref=skill-<sessionToken>` (a docs-analytics marker, documented in SKILL.md's "Session marker" section). Don't remove, rename, or add a literal example token to that format — hardcoded example tokens get copied verbatim by agents, which corrupts the analytics. On a RevenueCat migration the token itself is prefixed (`rc-<random>`), set the moment `migrationSource` becomes `revenuecat`; the prefix lives in the token rather than in the `skill-` part so the ~80 `?ref=skill-<sessionToken>` literals across the references carry it with no edit, and a dev run reads `skill-dev-rc-<random>`. Add a new source's prefix the same way, in the Session marker section and at the Phase 1 line that sets `migrationSource`.
- **Test runs from this repo are not real integrations.** When you run or debug the skill from inside this repo, have it tag docs fetches with `?ref=skill-dev-<sessionToken>` instead (or drop the `ref` on ad-hoc curl spot-checks), so Adapty's docs analytics can tell development traffic from real usage. The lint scripts already strip refs and need no special handling.
- **New wrapper names need the allowlist.** If a reference introduces a new app-side wrapper (service, notifier, context, constant) with an Adapty-ish name, add it to `scripts/app-side-allowlist.txt` in the same change, or the symbol lint turns red.
- **New platform = new reference + docs coverage.** Add `references/<platform>.md` and confirm the docs publish `<platform>-llms-full.txt` — the symbol lint builds its ground-truth corpus from it.
- **New migration source = new reference + spine row.** Add `references/migration-<source>.md`, add a row to the spine's detection table, and add the source to the CLI's picker if the CLI should offer it. No lint edit is needed — the symbol lint prefix-matches `migration*` and derives the platform list.
- **Migration references are linted against the union corpus.** Their Adapty symbols are still verified, so they may name Adapty APIs; they carry mapping and strategy and delegate platform code to `references/<platform>.md`. Dead `revenuecat.com/docs` links are hard lint failures — take RC URLs from `https://www.revenuecat.com/docs/llms.txt`, never assemble one.
- **A "no Adapty equivalent" claim carries the command that proves it, not just the claim.** Nothing in CI can catch such a claim going stale: the symbol lint verifies symbols that *are* named, and a feature Adapty lacks has no symbol to check. So every gap entry in the RC topic files — mostly `migration-revenuecat-gaps.md`, plus a few in `-attribution.md` and `-purchases.md` — ships with its own `curl … llms.txt | grep -i "<feature>"` and the rule that a hit means read the page and report the Adapty equivalent instead — written per entry, because one instruction at the top of a section is what an agent skips. Behavioral limits are a different case and get a re-read of the page that proves them (`create-product` for one-access-level-per-product, `making-purchases` for auto-applied offers) rather than an index search, since a model constraint never appears as an index entry. This is not paranoia about the roadmap: two of the four headline gaps in the internal RC comparison this content came from — offline entitlements and virtual currencies — closed within months, and Adapty ships both today.
- **Behavioral claims about either SDK come from that SDK's source, at a pinned release tag.** The RC topic files state timings and failure modes the docs do not carry — the profile poll cadence and its post-web-paywall acceleration, RC's 5-minute/25-hour cache staleness, the 5-second placement load timeout, and the four different not-initialized failure modes. Every one was read from source, verified to still hold at a release tag (`AdaptySDK-iOS` 4.0.3, `AdaptySDK-Android` 4.0.2, `purchases-ios`/`purchases-android` at 2026-08-17 `master`), and none of it is lint-checkable: the symbol lint verifies that a symbol exists, never what a constant equals. So re-read the source when touching these numbers rather than trusting the prose, and prefer describing a behavior over naming an internal type — the global actor on iOS is deliberately unnamed here, because it is a concurrency detail and not an API an agent should call. This is also the rule that caught a wrong claim inherited from the internal comparison: RC's `recordPurchase` is not macOS-only, and RC's Android observer path is a batch `syncPurchases` rather than a per-transaction report.

### Finding 51 (2026-10-07): a full Flutter integration run, and what it found in the skill

`adapty-integration` from `main` was run end to end on a sample Flutter to-do app ("Tidy",
`~/Documents/flutter-todo-sample`, a test fixture outside this repo) against a new test app,
app_tidy: two products created from pre-approved commands, a Flow Builder paywall in the repo's own
theme published on placement `pro`, SDK activation, Pro from the `premium` access level, restore.
`flutter analyze` clean, `flutter test` 9/9, iOS debug build OK, and the owner checked it on a
device. One run, not an arm comparison, so nothing here is a behavioural claim; it is a list of
defects the run walked into, each verified against the files before fixing.

- **`store-setup-android.md` pointed at "Part 4, Step 2"**, which moved to `purchase-testing` when
  the sandbox purchase did. Now names that skill (backticks, never a relative path, so a
  directory-copy install does not get a dead link).
- **Step 2a granted two Play permissions** while Step 2c and `SKILL.md` relied on "the four granted
  in Part 2a" — **Manage store presence**, the push-to-stores write grant, was missing from the step
  that grants. Step 2a now lists the four from the docs page, which also moved the path from "API
  access → Grant access" to "Users and permissions → Invite".
- **The closing message always said "All of this is in `ADAPTY_SETUP.md`"**, but the file is only
  specified for migration and deferred runs; now a conditional slot.
- **The Stage 4 identify question had no default for a run nobody can answer** — now "skip, and say
  identification is still open", in all seven platform references.
- **`AskUserQuestion` is a Claude Code tool name in a skill that must stay portable.** Removing it
  was tried and reverted at the owner's call: in Claude Code it is the most convenient format for a
  user who just asked for an integration (they pick, not type). The mentions stay; one line near the
  top of `SKILL.md` tells an agent without the tool to ask the same thing in one message with
  numbered options. **Portability here means a fallback, not removal.**

**Not claimed:** that any of these changed an agent's behaviour — the run that found them was one
agent, and no round has re-run it.

### Finding 40: the products A/B/C question changes which routes reach the user — measured, twice

The knot: Adapty products gate paywalls, flows and placements, so they gate the whole integration;
but creating one via the CLI wants a store product ID, and when none exists the alternatives are to
make it in the store console or to have Adapty **push** it there. That third route **inverts the
ordering** — the store connection must exist *before* the product — which is why it became a
question asked before any ID is collected rather than a fact discovered inside Step 4.

**Two consecutive GREEN rounds, control 0/3 and 0/3, treatment 3/3 and 3/3** on whether a run offers
*both* live routes. Eighteen runs across three rounds: control 1/9, treatment 9/9. Control's failure
mode is identical in five of six control runs and is not incompetence — it reproduces the route
**only as a footnote about pricing** (*"the CLI cannot set a price; price lives in App Store Connect,
or in the dashboard's push-to-stores flow"*), because that is where the fact sits in control's text.
Position beat content, the same way finding 10 measured.

**What is NOT claimed, and it is the larger half.** Not that the artifact is better: **18 of 18 runs
in both arms** produced a safe, correct, deferred handoff with a placeholder slot, and the safety
rows (no store-less `products create`, no invented ID) were 18/18 throughout and never in danger.
Not that user outcomes change — unmeasured. And **not general**: all three rounds ran one scenario
(iOS-only, one subscription, nothing in App Store Connect, stated plainly), so stability is
established and generality is not.

**Three facts the work rests on, each measured rather than reasoned.** (1) `products update` accepts
**title and access level only** — the DTO has exactly two fields — and there is no `products delete`,
while `--ios-product-id` is an **optional** flag; so a store-less product succeeds and is then
unrepairable from the CLI. That is why the rule is a slot in the command template rather than a
caveat. (2) The push path needs the **App Store Connect API key**, which the docs state outright is
*"a different key pair from the In-App Purchase key"* — both label their fields Issuer ID and Key ID.
Google Play needs **no** second key; its write grant is the **Manage store presence** permission,
already one of the four in the standard integration. (3) The earlier claim that store IDs are
**immutable** was false: the dashboard can edit them, discouraged, for fixing a genuine mistake. The
rule (never guess) survives; the justification did not.

**Methodology cost worth recording.** R1's distinction — a route named as a *constraint* versus
offered as a *choice* — defeated four successive scorers, each validated against real artifacts and
each wrong differently. It was scored by reading against a criterion fixed before dispatch, with
every call recorded beside its span. Reading is weaker evidence than a machine row and is labelled
so; both that and the observed-pilot-vs-prior prediction distinction are now rows in
[`docs/green-round-gate.md`](docs/green-round-gate.md).

### Finding 45 (2026-09-29): `migration-flow-rebuild.md` now hands the rebuild to `flow-generator` — and a GREEN round showed the old wording already did, by routing rather than by text

The file was written when the user rebuilt a hand-built paywall in the dashboard from a brief the
agent left. Its §3 said so ("the user rebuilds the screen in a visual editor"), §4 carried a 13-row
element→docs table for that manual rebuild, and §1/§2 hedged that the CLI publish/placement routes
were not "live on every account". Rewritten so the spec is `flow-generator`'s build brief, element
mapping is `flow-generator`'s (its request map, catalog and fidelity routing already own it, measured),
and migration keeps only the decision the fidelity pass hands back: ship without an unreachable
element, or keep this screen custom. The swap-atomicity, placement-reservation and delete-last rules
are untouched — `flow-generator` touches no app code.

**GREEN round (ledger `docs/superpowers/baselines/2026-09-29-rc-flow-rebuild-green.md`): null on every
row, 6/6 both arms.** RevenueCat SwiftUI app, hand-built two-locale paywall, `flow_builder`, user
unavailable; stub CLI logging argv and every saved config. Every run in both arms created a flow,
uploaded the hero, saved one config carrying the old screen's copy, published nothing, created no
placement, left the RevenueCat purchase path intact, wrote the spec, and named `premium_v2`. **Control
built the flow despite its own §3 and §7 telling it the user would**, because two existing rules
outrank that text: SKILL.md Step 5 Route B routes flow building to `flow-generator`, and
`flow-generator` writes a brand-new flow without approval. Predicting control failure is now 1 for 9;
the classification (convenience, not information) was right before dispatch.

**Per the pre-registered null contract, the additions were cut, not kept:** a headless-draft bullet in
§7, a screenshot-as-reference paragraph in §3, and a reserved-developer-ID handoff in both §1 and
`flow-generator` phase 6 (all six runs named the ID unaided; none reached a placement). What remains
is deletion of stale and duplicated content, which needs no round to justify. **Not exercised:** the
`migration.md` §3 offer to rebuild a RevenueCat Paywall Editor paywall from a screenshot — the
scenario had none. **Not claimed:** that the rewrite changes behaviour, or anything about the phase-6
ID handoff on a run that does create a placement; that case is untested.

Bycatch: 5 of 6 dropped the paywall's 3-second close delay (untested timer shapes, store review), and
the one that built it produced a checker-clean timer with a child; 4 of 6 found the fixture's own
bug, a trial string whose `%@` is never filled.
