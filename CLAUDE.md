# CLAUDE.md

Guidance for working in this repository. Keep it short: it loads into every session.

**This file holds standing rules only.** Evidence, test rounds, measurements and dated findings
go in `docs/maintainers/<skill>.md` (or `docs/maintainers/repo.md` for the repo as a whole),
never here. When a finding changes a rule, update that rule's one line here and put the evidence
in the maintainer notes. Read a skill's notes before changing one of its rules.

## What this repo is

Portable, Claude-style skills for agentic CLIs (Claude Code, GitHub Copilot CLI, OpenAI Codex,
Gemini CLI), all shipped in one plugin, `adapty-skills`:

| Skill | Does |
|---|---|
| `ab-tests` | Runs the life of a regular paywall or flow A/B test through the CLI's `ab-tests` topic: plan, create, update, start, stop, replace, archive |
| `adapty-attribution` | Answers campaign-performance questions from Adapty Attribution through the CLI's read-only `attribution` topic |
| `adapty-docs` | Routes any Adapty question to the right docs index and page; the fallback every other skill uses for a URL |
| `adapty-integration` | Integrates the Adapty SDK into a mobile app end to end, including migrations from other purchase systems |
| `ads-manager` | Operates Apple Search Ads through `adapty asa` |
| `audiences` | Creates or reuses segments and adds them as placement audiences |
| `flow-audit` | Read-only: is this Flow Builder flow ready for production |
| `flow-generator` | Reads, transforms, builds and writes Flow Builder configs; attaches a published flow to a placement |
| `growth-advisor` | Reads the app's subscription numbers through the read-only `analytics` topic and returns hypotheses to A/B test; no pricing |
| `migrate-placements` | Moves an app from paywall placements to flow placements, by creating new ones |
| `onboarding-teardown` | Growth hypotheses for an onboarding sequence; touches nothing |
| `paywall-teardown` | Conversion hypotheses for a paywall screen; touches nothing |
| `purchase-testing` | The first sandbox purchase and every failed one |

Three distribution channels: the Claude Code plugin (marketplace `.claude-plugin/marketplace.json`,
plugin in `plugin/` with `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`), the
skills.sh CLI, and a plain copy of one `plugin/skills/<name>/` directory. So **every skill
directory is self-contained and assumes no particular CLI**: never link a sibling skill by
relative path (name it in backticks), and never reach into another skill's files at runtime.

- **One plugin for all skills.** A new skill needs no manifest edit. Splitting into separate
  marketplace entries was rejected; don't reopen it without a new reason.
- **Keep the deprecated `adapty-sdk-integration` marketplace entry** until the docs stop teaching
  that handle; it keeps old installs updating.
- **Never create anything at `adaptyteam/adapty-sdk-integration-skill`**: it kills GitHub's
  redirect from the old repo name. `raw.githubusercontent.com` does not follow renames.
- **No telemetry.** The only outbound data besides the CLI's own calls is the docs
  `?ref=skill-<token>` marker and the `adapty feedback` note. Don't add a call home without a
  privacy policy, an `adapty.io` host and a README disclosure in the same change.

## Layout

- **Only `plugin/` ships** (manifests, `skills/`, `assets/`, the user-facing `README.md`,
  `LICENSE`). It cannot be renamed without a new directory submission.
- Everything else is maintainer-only: `CLAUDE.md`, `scripts/` (lints and allowlists), `tests/`
  (the `flow-generator` fixture corpus and repo-only test scripts), `docs/` (maintainer notes,
  `green-round-gate.md`), `.github/`.
- **A script a skill tells the agent to run lives under `plugin/skills/<name>/references/`**,
  never under `tests/` or the repo root. A shipped file may not instruct running anything in
  `tests/`.
- Per-skill file maps are in each skill's maintainer notes, under "Files".

## Lints

The lints are the verification gate; there is no test suite for the skills. Run all four after
any edit to a SKILL.md or a reference:

```bash
node scripts/lint-frontmatter.mjs              # strict YAML, Agent Skills spec
node scripts/lint-symbols.mjs [platform ...]   # SDK symbols exist in the docs
node scripts/lint-links.mjs                    # every https URL works as an agent fetches it
node scripts/lint-anonymity.mjs                # nothing points into Adapty's internal systems
```

Exit `0` clean, `1` findings, `2` environment problem (fix the environment, not the skill). CI runs
all four on PRs, on pushes to `main` and daily; a scheduled failure files one `skill-drift` issue.

- **A new skill goes into `OTHER_SKILLS` in `scripts/lint-symbols.mjs`** in the same change, then
  inject an `Adapty.getPaywall()` to confirm the lint turns red. Until then it has no symbol
  coverage and the lint stays green.
- **Skills other than `adapty-integration` name no SDK symbols**; the scope guard turns the lint
  red if one does.
- **New app-side wrapper names** a reference tells the user to create go in
  `scripts/app-side-allowlist.txt`; real SDK symbols missing from the docs go in
  `scripts/undocumented-sdk-symbols.txt` with a source URL.
- **If a description ever needs a YAML map,** extend the frontmatter lint; never loosen it.

### This repo is public: keep it anonymous

Everything is public on GitHub and `plugin/` ships to every user. Never write:

- task-tracker keys or links (Jira keys, Atlassian URLs, also in branch names);
- support tickets, chat links or internal channel names;
- merge-request numbers from internal repos;
- customer cases: a customer's or app's name, an ID from a customer's account, one customer's story
  (aggregates are fine);
- people's names or personal accounts (write the role);
- closed-source code from Adapty's private repos: repo names, paths, function names, excerpts (say
  "read from the transformer's source");
- internal hosts, log index names, the internal sandbox app's name or ID ("the sandbox app").

Public repos (`adaptyteam/AdaptySDK-*`, `adapty-cli`, this repo, `apple-ads-cli`, the docs) may be
cited. The anonymity lint cannot catch names or a retold customer case: check those yourself. A
new fixture keeps real visible copy, so replace product and brand names in it.

## Output voice

Every user-facing skill carries its own compact copy of these rules as `## How you sound`, because
a single copied skill cannot read this file. Change a rule here first, then in every copy.
`adapty-docs` prints nothing of its own and has no copy.

1. **Offer the outcome, invoke the skill on a yes.** Name a skill only when the user must act on
   it themselves.
2. **"I" for what the agent does, "you" for what the user does.**
3. **A patient, friendly, realistic colleague.** Lead with the answer, number steps, end on one
   next step; no opener, recap or "hope this helps".
4. **Bold marks the one thing not to miss,** at most once per block.
5. **Raw values only when the user will type or see them elsewhere.** No element ids, internal
   status codes, tool or variable names.
6. **Links are full, clickable, and point at the exact page.**
7. **Honest about scope, then close the gap:** say what was not checked and how the user can check it.
8. **Fixed blocks where a decision is made, one line otherwise, each thing said once.** Each fixed
   block carries a short example of its shape, marked as not words to copy.
9. **Reply in the user's language.** UI labels stay as the other tool shows them.

Where a script prints the user-facing text, fix the script's wording first: agents relay it
nearly verbatim. A skill's own templates and examples are what leak into replies, so fix the
template, not the rule. A condition the agent cannot observe is not followed; make it a check.

## Editing skills

- **Invoke `superpowers:writing-skills` first.** It owns frontmatter, structure and the Iron Law.
- **Behaviour changes need test rounds.** The local bar is two consecutive clean rounds. A change
  a round could not justify is trimmed or reverted. Design a round against
  [`docs/green-round-gate.md`](docs/green-round-gate.md) before dispatching agents. Arms overlay
  only what ships: never put `CLAUDE.md` or `tests/` in one arm only.
- **Every CLI call goes through `$ADAPTY`, resolved once per run:** `npm i -g adapty@latest`, with
  `npx --yes adapty@latest` as the fallback. Never a bare `adapty` or a per-call `npx` at a call
  site. `flow-audit` alone resolves straight to the npx form. Keep `--yes` and the `zsh`
  word-splitting note beside the block. A command is missing only after `--help` says so and one
  `npx --yes adapty@beta` attempt; never gate on a version number.
- **Verify CLI facts against each command's own source** (`static flags`, description) in
  `adaptyteam/adapty-cli`, not prose, `--help` or flag-set composition; enumerate `dist/commands/`.
  Print `--version` with anything you test.
- **Docs URLs must literally exist.** Never assemble a slug; take URLs from the skill or a fetched
  `llms.txt` index.
- **When a fact is superseded, grep every reference and `component-catalog.json` for the old rule
  in the same change.**
- **Commit with explicit paths during test rounds,** never `git add -A`.
- **An agent's report is not an artifact:** score the files it wrote.

## Per-skill rules

Standing rules only. The evidence for each is in `docs/maintainers/<skill>.md`.

### `ab-tests`

- **Every command, flag and output field comes from `src/cli/commands/ab-tests/*` in `adapty-cli`,** not from help text. CLI 0.13.0 is the first release with the `ab-tests` commands.
- **Start, stop, replace and archive run only after the user's yes to the exact effect:** who sees what from when, what stops, what cannot be undone; then `--yes`. The CLI asks only at a terminal and refuses with exit 6 elsewhere, so the skill's card is the confirmation. An unattended run never does these four.
- **Read the test and the placement before each of the four; read the placement again just before a start, stop or replace.** Changed since the user saw it: a new card, a new question.
- **Never start a test that is not a draft** (it would start again with old users on their old arms); offer a new test, or `replace` for a live one.
- **Never write a placement.** Only `ab-tests` commands start, stop and replace tests; a placement write that carries a test entry belongs to `audiences`, which keeps entries as read.
- **`update` sends the whole test again:** a flag left out is cleared. On a started test it changes only title and goal, with the arms and placement as read.
- **`list` shows flow tests unless `--type paywall` is given;** look at both types.

### `adapty-attribution`

- **Apple Search Ads spend is not in Attribution.** Keep the sentence the reply says; read spend through `asa`; a spend the user states becomes a threshold, never a ROAS.
- **Run every playbook command** against the real CLI's local validation after an edit (catalog metrics, `--granularity` needs `--group-by date`, window caps).
- **Route setup to `adapty-docs`;** don't teach it in the skill.

### `adapty-docs`

- **The routing table is the skill:** the root `llms.txt` never names the sub-indexes. Re-check that before calling the table redundant.
- **Full-text aggregates are grep targets, never fetched.** Keep the `# File:` recipe free of bare URL literals inside shell quoting (the link lint scrapes them).
- **Use `<platform>` in templated URLs** so the link lint skips them; route endpoint questions to `api-llms.txt`, not the spec-header pages.

### `adapty-integration`

- **Keep the session marker format** `?ref=skill-<sessionToken>`: never a literal example token; a migration source's prefix goes inside the token; runs from this repo use `skill-dev-`.
- **A new platform** needs `references/<platform>.md` and a published `<platform>-llms-full.txt`; **a new migration source** needs `references/migration-<source>.md` and a spine detection row.
- **Every "no Adapty equivalent" claim carries its own `llms.txt` grep** (or a page re-read for model limits) and says a hit means report the equivalent.
- **SDK timings and failure modes come from SDK source at a pinned release tag;** re-read it when touching them. Take RevenueCat URLs from its `llms.txt`.
- **The store product ID is a slot in the `products create` template:** a store-less product succeeds and cannot be repaired from the CLI.

### `ads-manager`

- **Verify against `src/commands/asa/<topic>/<command>.ts`,** pin the commit, and detect drift by diffing flag sets and descriptions per command, not the file list.
- **A rationalization-table row needs a byte-exact quote from a real run.**
- **Keep the slots unguessable:** `--idempotency-key <key>` and `--<filter-from-that-list-s-matrix-row>` stay as they are.
- **`SKILL.md` links into `asa-management.md` and `asa-metrics.md` by exact heading;** don't rename those headings.

### `audiences`

- **Field names come from a real `segments get`,** never from memory.
- **Pass A/B test entries back as read** (CLI 0.11.0 is the first release that returns them). Shared-test (`cross_*`) entries stay unchanged, and a test id goes only on the audience that already carries it. Starting, stopping or replacing a test is `ab-tests`, never a placement write here.
- **A placement write never stops, starts or moves a test:** every test entry goes back as read, and a request that would stop one (a write that replaces or moves a test's audience) is routed to `ab-tests stop`, and one that would start one to `ab-tests start`; then the write follows. Read the placement again before the write (changed: ask again; unattended: stop and report). The CLI has no such check. An unattended run may write when every test entry is unchanged.
- **Never delete an entry the CLI refuses** (`content_type` on 0.10.0 and older, "this CLI does not know this audience kind" later); tell the user to update the CLI, re-resolve `$ADAPTY`, then the dashboard.
- **OR is two segments** (filters inside one are ANDed); equality is `IN` with one value; new audiences go before the default.

### `flow-audit`

- **Read-only; installs nothing.**
- **"Ready to publish" only with zero blockers and every open question put to the user.**
- **The store-review checks stay advisory** (`risk`/`question`, own section, fixed disclaimer) and never move the verdict; missing-mechanism checks stay blockers. Never re-add `subscription-under-7-days`.
- **Nothing parses finding message text;** tests key on check names. Read `checks.md` or `store-review.md` before changing a check.

### `flow-generator`

- **Never renumber a trap** in `flow-schema.md`; a new one takes the next number after the router's last row, with its router row in the same change.
- **`SKILL.md` links into its references by exact heading;** grep the links before renaming one.
- **One owner per fact; link, never restate.** Don't split `flow-schema.md` or `patterns.md` (tried and reverted). Keep `patterns.md`'s skeleton order, `footer` first.
- **When guidance prescribes a shape, make `flowkit.py` emit and guard it;** agents build what the helper exposes. Keep design opinions out of `flowkit.py`.
- **`component-catalog.json` templates carry no sample prices, trials, bound ids or baked selected looks;** keep `tests/test-catalog-premades.py` green.
- **Calibrate every checker change:** silent on every real export in `tests/fixtures*`, firing on injected defects, each mechanism negative-tested. Never edit a fixture to quiet a check.
- **Trust order: `flows config validate`, then a real export, then the schema.** A shape no export shows needs a device check.
- **A preview never retires a device report;** a claim about tapping, scrolling or navigation needs the driven page or a device. A shape verified with diagnostics in it is the instrumented shape.
- **The fetched config is the only write base,** never a build script or leftover file; `diff-config.py` removals go in the approval ask.
- **Don't rebuild what was ruled out:** the fake-video detector, a draft-validate copy tool, the Google Fonts catalog, a `CircleNotch` loader guard, an `x-supported` element ban beyond `old-price`. The reasons are in the notes.

### `growth-advisor`

- **`references/evidence.md` is vendored byte-for-byte from the growth team.** Repo-specific facts go elsewhere; never quote the raw test library, which names customers.
- **One owner per number:** uplift ranges from `evidence.md`, market medians and win rates from `market.md`. No Autopilot impact numbers.
- **Pricing is out of scope:** no price is read, compared or proposed, and price is mentioned only in the skill's fixed sentence. Don't restore the deleted competitor-price reads.
- **Two words for users: a hypothesis, and once picked, an A/B test.** Ask which one to start with, never for a verdict on each.
- **A live placement changes only through the confirmation block:** `update` replaces every audience, so a running A/B test entry not passed back as read stops that test.
- **Filter values come from `analytics values`, never from a group's `key`;** read funnel and retention groups from the grouped answer. New segments go through `audiences`.

### `migrate-placements`

- **Create, never convert:** only `placements create`; the old placements stay as the rollback.
- **The user approves every developer ID** before anything is created; IDs are permanent.
- **Build, publish, then place.** Route on `Cannot attach a draft flow` (the backend sentence is the legacy form).
- **An A/B test entry is skipped and named, never migrated:** a test on the default audience skips the whole placement; `to_flow_audience` and `build_create_command` raise on a test entry; the source placement never changes.
- **Keep the guards in `migrate.py`:** paginate through `fetch_list`, `content_type` on every audience, no mixed audiences, phase-7 argv only from `plan --flows`.
- **Look for converted flows first** (Reuse → Convert → Build → Stub); those reads degrade, never fail the run. Ledgers are `flows.json` and successes-only `placements.json`; the stub ships locally, never `flowkit`.

### `onboarding-teardown` and `paywall-teardown`

- **Their `references/patterns.md` files are vendored from the growth team** (onboarding byte-for-byte). Repo-specific facts go in `SKILL.md`, `categories.md` or `look.md`; impact ranges change upstream first. Never name a company.
- **Onboarding owns the sequence and the seam; paywall owns the screen.** Don't duplicate rows.
- **No interview inside a build:** called from `flow-generator`, answer from the brief, config and catalog, and batch the rest.
- **Choose skeletons and archetypes by observable prerequisites,** disclose the choice, and never fake a missing prerequisite (an offer, an asset, a personalized result). A flow cannot request a permission.
- **Design mode is entered only when no design reference was given;** a given reference outranks the library; findings on your own draft are fixed, not reported.
- **Looks follow `look.md`:** the app's design first; with a brand invent only the layout; with none, invent from a random starting point and roll by command. Never put a test fixture's own nouns in shipped examples.

### `purchase-testing`

- **Route, don't restate:** store-console procedures belong to the doc that maintains them. Preflight checks come from the CLI's typings, not prose.
