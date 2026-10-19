# Maintainer notes: the repo as a whole

Evidence and history behind the rules in `CLAUDE.md`: measurements, test rounds, dated findings. Not loaded into sessions. Read the part you need before changing a rule; add new findings here, never to `CLAUDE.md`.

## Background

**The link lint covers ALL of `skills/`; the symbol lint covers `adapty-integration` and guards the rest.** Widened 2026-08-28 — it previously hardcoded `plugin/skills/adapty-integration`, so a green run said nothing about four of the five skills that ship, while the runtime agent is told to fetch URLs from all of them. The widening cost 17 unique URLs and found no dead links; coverage is now printed per skill on every run (`adapty-integration 322, ads-manager 1, flow-audit 7, flow-generator 22, onboarding-teardown 1, paywall-teardown 1` — `flow-audit` had none when the lint was widened and has since gained 7). Two extraction rules were needed and both are load-bearing: a URL containing `…` **or** `...` is a documentation placeholder, not a link — the second came from a real 404 on a media URL inside pasted sample output with the hash cut out (`1e5bbbb4-.../hero-600x400.png`), which is elided-example noise rather than a finding.

**The symbol lint was deliberately NOT widened, and that is a measured decision rather than an omission.** It resolves a file's platform from its name (`references/<platform>.md`) and checks against that platform's docs aggregate; the other seven skills have no platform and name **zero** SDK symbols (measured across all their `.md`; re-measured when `migrate-placements` and then `adapty-docs` were added — still zero). But "they name none" is an assumption that rots the moment someone adds one, so it is now checked instead of believed: a **scope guard** scans those seven for `Adapty[A-Z]…` / `Adapty.<member>` and turns the lint **red** with a pointer to either drop the symbol or widen the lint. The capital `A` is what separates an SDK symbol from the domain (`adapty.io`) and the CLI (`adapty asa`). Negative-tested by injecting `Adapty.getPaywall()` into `flow-audit`.

**`OTHER_SKILLS` in `lint-symbols.mjs` is a hardcoded array, so a new skill gets NO symbol coverage in either direction until it is named there.** The lint stays green while saying nothing about it, which is the worst failure mode a guard can have. Add the skill to that array in the same change that creates it, then negative-test it by injecting a symbol and confirming the lint reddens — the injection is the only thing that proves the new entry is live rather than merely present. `lint-links.mjs` needs no edit: it already walks all of `skills/`.

- **Frontmatter lint** — every `plugin/skills/<name>/SKILL.md` frontmatter must parse as **strict** YAML and meet the Agent Skills spec: `name` present, matching its directory, lowercase letters/digits/hyphens, ≤ 64 chars; `description` present, non-empty, ≤ 1024 chars; no repeated or unknown key. It exists because an unquoted description containing `: ` (flow-audit's `Read-only: never writes…`) is invalid YAML that a lenient loader accepts and a strict one rejects — so a harness can drop the skill with no error — and neither other lint parses frontmatter; `skill-validator` found it, CI did not. Zero-dependency like the others, so it accepts a **deliberate subset** (top-level scalars: plain, single- or double-quoted, or a `>`/`|` block) and **refuses anything else by name** rather than passing a shape it cannot check. Calibrated against Ruby's YAML parser: the parsed value matches on all nine skills, and it flags every shape that parser rejects — plus an unquoted ` #`, which that parser *accepts* and silently truncates as a comment. If a skill ever needs `metadata` (a map), extend the script; do not loosen a check.

**Every skill but `adapty-docs` now carries the copy.** `adapty-docs` is an intermediary: it finds
a page for another skill and prints nothing of its own, so it has no voice to set. Measured per
skill against HEAD with two consecutive rounds (ledgers under `docs/superpowers/baselines/`,
2026-10-02 and 2026-10-05); `ads-manager` got the section with no round, because its baseline
already met every rule. Two findings recur across skills and are worth knowing before the next
edit: **the fixed blocks' own templates and examples are what leak** (element ids, file names,
backticked counts, bolded labels) — fix the template, not the rule — and **a condition the agent
cannot observe is not followed** ("if `flow-generator` is not installed" was ignored until it
became a check: a sibling directory and a shell).

**Measured on `flow-audit`, two consecutive rounds (Russian, then Spanish; two different
flows; 3 control + 3 treatment each; ledger `docs/superpowers/baselines/2026-09-25-flow-audit-voice-green.md`).**
Treatment was clean on every row both rounds. Control — the old skill — translated well and
kept every finding (the competence prior held), but leaked what the rules exist to stop:
element ids in 4 of 6 replies, `flow-generator` in 2 of 6, raw action names in 2 of 6, builder
labels translated away in 6 of 6, and **0 of 6 could say whether a placement shows the flow**,
because the old skill told it that was invisible. Two things the rules do NOT move, measured:
language and completeness are already right without them, and so is turning a gate failure into
a plain blocker (6 of 6 both arms). **Where the text comes from a script, fix the script's
wording first**: most of the separation came from what the agent was handed, not from the relay
rules alone, and an agent translating near-verbatim copies the script's words, good or bad.

**Before creating or editing a skill, invoke `superpowers:writing-skills`.** It owns the frontmatter and the `description`'s triggering rules, SKILL.md's structure, the token budgets and the Iron Law, and nothing here restates them. What this file carries is what this repo adds on top: the local bar of two consecutive clean rounds, the null contract that trims or reverts a change a round could not justify, and [`docs/green-round-gate.md`](docs/green-round-gate.md) as the pre-dispatch checklist. Where a rule appears in both, that skill owns the general form and this file owns the measurement behind it.

## Repo and distribution, full text

One repo, three distribution channels: a Claude Code plugin (the marketplace is `.claude-plugin/marketplace.json` at the repo root; the plugin itself is `plugin/`, with its own `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`), the skills.sh CLI, and plain directory copy of a `plugin/skills/<name>/` directory into a tool's skills folder. Keep every skill directory self-contained and format-portable — nothing in one may assume Claude Code specifically.

All eleven skills ship inside the single `adapty-skills` plugin, because a plugin exposes every skill under its `skills/` directory (`plugin/skills/`). No manifest edit is needed to add one. The plugin name is deliberately broader than any one skill — installing it gives you every skill in the repo, and that is the intended shape. Splitting the skills into separate marketplace entries was considered and rejected; do not reopen it without a reason the plugin name no longer covers.

`marketplace.json` also carries a **deprecated `adapty-sdk-integration` entry** pointing at the same `source: "./"`, so installs made under the old plugin name keep resolving and keep updating. Verified: `plugin details` through either handle reports the same plugin identity and the same skill inventory. Drop that entry only after the docs stop teaching the old handle — never before, or you break the installs it exists to protect.

**Three namespaces, renamed together:** the GitHub repo is `adapty-skills`, the plugin is `adapty-skills`, and the SDK skill is `adapty-integration` (the ads and flow skills keep their names). They are independent namespaces that happen to agree now — a future change to one does not imply the others. Note the repo rename has no alias mechanism the way the plugin does: GitHub redirects git and web traffic from the old name indefinitely, but **`raw.githubusercontent.com` does not follow renames**, so any consumer fetching raw file URLs breaks the moment the rename lands and must be updated in the same wave. The redirect also dies permanently if anything is ever created at `adaptyteam/adapty-sdk-integration-skill` again, so never reuse that name.

**Only `plugin/` ships.** It is the folder users install and the folder the Anthropic and OpenAI directories scan: the two manifests, `skills/`, `assets/`, `README.md` (the user-facing README, shown as the directory listing) and `LICENSE`. Everything a maintainer needs (`CLAUDE.md`, `scripts/`, `tests/`, `docs/`, `.github/`, the short root `README.md`, `SECURITY.md`) stays at the repo root, outside it, so it neither ships nor draws a directory review hold. A script a skill tells the agent to run must live under `plugin/skills/<name>/references/`, never at the repo root. The directory fixes a submission's folder at submit time, so `plugin/` cannot be renamed without a new submission.

- **The plugin sends no telemetry.** The end-of-integration feedback POST (and the `feedback-endpoint/` function that received it) was removed for the Anthropic and OpenAI directory submissions: its `sentiment` field was inferred from the conversation, which the Anthropic directory policy forbids extracting, and its personal Vercel host failed OpenAI's publisher-identity rule. The only outbound data beyond the Adapty CLI's own API calls is the `?ref=skill-<token>` docs marker, which carries a random token (prefixed `rc-` on a RevenueCat migration) and nothing else, and the README discloses the token. Do not reintroduce a call home without a privacy policy, an `adapty.io` host and a README disclosure in the same change.

## The lints, full text

- **Frontmatter lint** — every `plugin/skills/<name>/SKILL.md` frontmatter must parse as **strict** YAML and meet the Agent Skills spec: `name` present, matching its directory, lowercase letters/digits/hyphens, ≤ 64 chars; `description` present, non-empty, ≤ 1024 chars; no repeated or unknown key. It exists because an unquoted description containing `: ` (flow-audit's `Read-only: never writes…`) is invalid YAML that a lenient loader accepts and a strict one rejects — so a harness can drop the skill with no error — and neither other lint parses frontmatter; `skill-validator` found it, CI did not. Zero-dependency like the others, so it accepts a **deliberate subset** (top-level scalars: plain, single- or double-quoted, or a `>`/`|` block) and **refuses anything else by name** rather than passing a shape it cannot check. Calibrated against Ruby's YAML parser: the parsed value matches on all nine skills, and it flags every shape that parser rejects — plus an unquoted ` #`, which that parser *accepts* and silently truncates as a comment. If a skill ever needs `metadata` (a map), extend the script; do not loosen a check.

- **Symbol lint** — every Adapty-branded symbol used in a reference's code contexts (`Adapty.x` / `adapty.x` / `AdaptyUI().x` member calls, `Adapty*` type names, in fenced blocks and inline backticks) must exist in that platform's official docs. Ground truth is the `<platform>-llms-full.txt` docs aggregate plus pages the reference links; the docs are verified against SDK sources by the docs team's release process, so docs presence transitively means the symbol exists in the SDK. A reference's platform comes from its filename (`store-setup-*` files are pinned to their platform in the script). Two plain-text escape hatches, editable without touching code:
  - `scripts/app-side-allowlist.txt` — wrapper names the references deliberately tell the *user* to create. They look Adapty-branded but are not SDK symbols; add the name here when a reference introduces a new suggested wrapper.
  - `scripts/undocumented-sdk-symbols.txt` — real SDK symbols deliberately absent from the docs. Each entry pins a source-of-truth code URL and is verified against the SDK source instead, so a rename still turns the lint red. Format: `<reference>: <symbol> <source-url>`.
- **Link lint** — every https URL in the skill must work the way an agent fetches it: `adapty.io/docs` pages are checked via their `.md` variant with query/hash stripped, `*-llms*.txt` aggregates as-is. A docs 404/410 is a hard failure (the skill literally instructs fetching that URL); external links (stores, consoles, GitHub) failing are warnings only, as are docs pages missing from `llms.txt` (they work but agents can't discover them).
- **Anonymity lint** — no tracked file may point into Adapty's internal systems; see the rule below. Scans every tracked text file, not just `plugin/`, because the whole repo is public. Runs its own self-test first, so a broken pattern turns it red instead of silently passing.

Public repos may be cited freely: the SDKs (`adaptyteam/AdaptySDK-*`), `adapty-cli`, this repo, `apple-ads-cli`, and the docs. `scripts/lint-anonymity.mjs` enforces the mechanical half. It cannot catch people's names, customer names or a retold customer case, so check those yourself before committing. **Fixtures need the same care:** `tests/fixtures/` holds sanitized exports of real flows, and sanitizing remaps ids but not visible copy, so replace any product or brand name in a new fixture's text before committing it.

Git history is not rewritten: commits before this rule keep the old text. Only a leaked credential would justify a history rewrite.

CI (`.github/workflows/skill-lints.yml`) runs all four lints on PRs and pushes to `main` (red blocks merge) and on a daily cron that catches drift with no skill commit involved — docs renames, SDK releases. A scheduled failure files one deduped `skill-drift` GitHub issue; repeats become comments on it.

## Output voice, full text

What a user reads is written to one voice across all ten skills. This list is the
canonical version; **each skill carries its own compact copy** (a `## How you sound`
section), because a directory-copy install ships one skill alone and cannot read this
file. Change a rule here first, then in every copy.

1. **Offer the outcome, invoke the skill on a yes.** "I can fix these for you. Want me
   to?" — then call `flow-generator`. Name a skill only when the user must act on it
   themselves, for instance because it is not installed.
2. **"I" for what the agent does, "you" for what the user does.** No passive voice where
   the user has a step to take.
3. **A patient, friendly, realistic colleague.** Assume the user may be new to in-app
   purchases. When they ask, answer clearly and use their own app as the example.
   Friendly through patience, never through filler; realistic about what is slow or
   hard. Not wordy: lead with the answer, number steps, end on one next step, no opener,
   recap or "hope this helps". Full explanations only when asked.
4. **Bold marks the one thing not to miss**, at most once per block (a heading or a
   verdict line is that one thing).
5. **Raw values only when the user will type them or see them elsewhere** — a developer
   ID, a builder label, a command they run. Element ids, internal status codes, tool and
   variable names never; statuses read the way the dashboard shows them.
6. **Links are full, clickable, and point at the exact page.**
7. **Honest about scope, then close the gap.** Say what was checked and what was not;
   for what was not, say how the user can check it (where, what they should see). Before
   saying "I don't know", try to find out.
8. **Fixed blocks where a decision is made, one line otherwise, each thing said once** —
   and each fixed block carries a short example **of its shape**, marked as not words
   to copy, since agents copy examples verbatim.
9. **Reply in the user's language.** UI labels from another tool stay exactly as that
   tool shows them.

Where a script prints the user-facing text (`flow-audit`'s report), the script's
English is written to these rules and the agent relays it translated, keeping every
numbered item. Applied so far: `flow-audit`.
