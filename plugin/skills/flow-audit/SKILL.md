---
name: flow-audit
description: 'Use when a client asks whether a Flow Builder flow is ready for production, wants it audited or checked, or asks something like "did I forget anything — triggers, products, variables?", "is this ready to publish?", or "check my paywall/flow". Answers one question — is this flow safe to put in front of paying users — with a verdict and ranked findings. Read-only: never writes to a flow. Complements `flow-generator` (which owns writes) and `paywall-teardown` (which owns conversion advice).'
---

# flow-audit

## What this answers

**Is this flow ready for production?** Not "here is a list of things about your flow" —
a verdict: ready, or not ready and why, backed by ranked findings that each carry a
concrete fix. A **blocker** is precisely a reason to answer no.

This skill is **read-only**. It never calls `flows config update`, `products create`, or
`flows create`. It cross-references the flow's config against the live dashboard
(catalog, access levels) to catch what an offline checker structurally cannot — a bound
product that does not exist, one with no store binding, a card whose copy claims a
period the product does not have. When the user wants something fixed, hand it to
`flow-generator`, which owns the backup, the approval gate, and the write. This skill
does not implement transforms and does not touch the config on disk beyond the working
copy it fetches to check.

## How you sound

Every message, not only the report:

- **A patient colleague who knows in-app purchases.** The user may be new to them. When
  they ask, answer plainly and use their own flow as the example. Friendly through
  patience, never through filler.
- **"I" for what you do, "you" for what they do.** Lead with the answer; end on the one
  thing they need to do next. No opener, no recap, no "let me know if…".
- **Plain words over raw values.** Show a value only when the user will type it or see it
  elsewhere — a placement ID, a builder label, a URL. Element ids, status codes and tool
  names never.
- **Full, clickable links to the exact page.**
- **Could not check it? Say how they can.** Do not know something? Look it up before
  saying so — the CLI, the flow, the `adapty-docs` skill.
- **Offer the outcome ("I can fix these"), never the skill that will do it.**
- **Reply in the user's language.**

## CLI or MCP

This skill reaches Adapty through the Adapty CLI or the Adapty MCP server. Its commands are written
for the CLI, and over MCP each one is a tool call. Before the first call, check both, pick one way,
and keep it for the run:

- **The CLI is ready** when `adapty auth whoami` shows an account. Install nothing for this check.
- **MCP is ready** when you hold Adapty's tools (names ending in `apps_list` and `auth_whoami`,
  after any prefix your client adds) and `auth_whoami` shows an account.

| CLI ready | MCP ready | Use |
|---|---|---|
| yes | no | the CLI |
| no | yes | MCP |
| yes | yes | the way this skill prefers (the line after this section's example) |
| no | no | ask which one to set up (below) |

**Over MCP, run each command as its tool.** `$ADAPTY <topic> <command>` is the tool whose name ends
in `<topic>_<command>`, dashes and spaces turned into underscores: `ab-tests list` is
`ab_tests_list`, `flows config get` is `flows_config_get`. The flags become the tool's parameters;
take their names and shapes from its schema (`--app` is `app_id`, a flag that may repeat is one
list). The tools return JSON, so drop `--json`. `--yes` has no parameter: the yes this skill asks the
user for still comes before the call. Skip the `$ADAPTY` resolution, `--help` probes, `auth login`
and `auth status`: a command exists when its tool is in your list, and the client signs in.

**A command with no tool, and a script that runs `$ADAPTY`, need the CLI** (`feedback` and
`segments create` have no tool). Run that step with the CLI when it is ready. Otherwise skip the
feedback note without a word, and for any other step say it needs the CLI and offer to set it up.

**When a call fails one way,** a read may run once the other way if that way is ready. After a
write fails or times out, read the state again the way that wrote; never repeat the write the
other way.

**Neither ready:** ask which one to set up, the one this skill prefers first, then give only that
one's steps. Use your question tool if you have one; otherwise ask in one message with numbered
options.

- **The CLI:** run this skill's CLI resolution, then `adapty auth login`, which opens the browser for
  the user's sign-in. The Claude app also needs Adapty's domains allowed first:
  https://adapty.io/docs/developer-cli-cowork.md
- **MCP:** the server is `https://mcp.adapty.io/mcp`, and the user signs in in the browser. The
  `adapty-skills` plugin adds it, so when your client says the server needs sign-in, only the
  sign-in is left.
  - Claude Code: `/mcp`, pick `plugin:adapty-skills:adapty`, **Authenticate**. Without the plugin,
    first `claude mcp add --transport http --scope user adapty https://mcp.adapty.io/mcp`.
  - Codex CLI: the plugin's connect prompt signs in. Without the plugin:
    `codex mcp add adapty --url https://mcp.adapty.io/mcp`, then `codex mcp login adapty`.
  - The Claude app: connect it on the plugin's **Connectors** tab. Without the plugin: Settings →
    Connectors → **Add custom connector**, with the URL above.
  - Any other client: its own way to add a remote MCP server that signs in with OAuth.

  If the tools do not appear in this session, the user starts a new one: say so and stop.

Example of the question's shape, not words to copy:

> I can reach your Adapty account in two ways. Which one should I set up?
> 1. The Adapty CLI (better for this): I install it, and you sign in once in the browser.
> 2. The Adapty MCP server: you add it to your AI tool and sign in; nothing to install.

**This skill prefers the CLI:** its checks read the flow's config from a file, and over MCP the
whole config passes through the conversation. With MCP only, offer the CLI in one line; on a
no, save the config `flows_config_get` returns to a file and audit that.

## Phase 1 — resolve and authenticate

Resolve `$ADAPTY` once:

```bash
ADAPTY="npx --yes adapty@latest"
$ADAPTY auth status
```

**This skill installs nothing, which is the one place it differs from every other skill
here.** An audit is read-only and makes a handful of calls, so the ~1 s the npx wrapper
costs per call is noise, while `npm i -g` would be the only thing an audit writes to the
machine. `@latest` on every call is what keeps the run off a stale global binary, which is
what the install buys elsewhere.

**Never gate this on a version number — a command is declared missing only after `--help`
says so.** If
`$ADAPTY <command> --help` does not describe one, try `npx --yes adapty@beta <command>
--help` once; only then is the route unreleased. `--yes` on the fallback is load-bearing:
without it npx asks permission to install an uncached package, and a headless run has
nobody to answer. In `zsh` a multi-word `$ADAPTY` is not word-split, so run
`setopt shwordsplit` once in the same shell; `command not found: npx --yes adapty@latest`
is that shell problem, never a missing CLI. If `auth status` shows no
session, stop and tell the user to run `adapty auth login` — this skill cannot
authenticate for them.

Resolve the app:

```bash
$ADAPTY apps list --json
```

If the user already named the app, match it by title and skip asking. Otherwise show
the list and ask which one.

## Phase 2 — select the flow

```bash
$ADAPTY flows list --app "$APP" --json --page-size 100 > flows.json
```

Returns `{id, name, status, updated_at}` per flow — `status` alone is a finding source
(a flow sitting in `publication_failed` is worth saying out loud even before any check
runs). If the user named a flow ("audit my onboarding flow"), match it by name and
skip the prompt. If they did not, show name + status for each and ask which one.

**Never audit a flow the user did not name or select.** A silent pick on the wrong flow
wastes the whole run and can mislead the user into thinking a different flow was
checked.

## Phase 3 — fetch

```bash
$ADAPTY flows config get "$FLOW" --app "$APP" --json > flow.envelope.json
python3 -c "import json; d = json.load(open('flow.envelope.json')); \
json.dump(d['config'], open('flow.config.json', 'w'))"
$ADAPTY products list --app "$APP" --json > catalog.json
```

`flows config get` returns an **envelope** — `{config, remote_configs, updated_at,
status}` — not a bare config. Every check in Phase 4 wants the bare config, so extract
`config` before running anything. **Keep the envelope**, and not only for `updated_at`:
when the last publish failed it also carries `publication_status`, `transform_error` and
`publication_error`, which is the only place in this audit the *reason* for a
`publication_failed` status appears. `products list --json` returns `{"data": [...]}`; the
audit script accepts either that wrapper or a bare array.

The catalog fetch happens **before** the checks run, in this same phase, because every
product finding in Phase 4 is a comparison against it — a bound product absent from the
catalog can't be detected without it.

Then fetch every placement, so the audit can say whether the app can reach this flow at
all. `placements list` carries no audiences, so each placement is read with `placements
get`; a flow audience is `{"content_type": "flow", "flow_id": …}`.

```bash
mkdir -p placements; page=1
while :; do
  $ADAPTY placements list --app "$APP" --json --page-size 100 --page $page > placements.page.json
  python3 -c "import json; d = json.load(open('placements.page.json')); \
print('\n'.join(p['id'] for p in d['data']))" >> placement-ids.txt
  pages=$(python3 -c "import json; \
print(json.load(open('placements.page.json'))['meta']['pagination']['pages'])")
  [ "$page" -ge "$pages" ] && break; page=$((page + 1))
done
xargs -P 8 -I{} sh -c "$ADAPTY placements get {} --app $APP --json > placements/{}.json" \
  < placement-ids.txt
python3 -c "import glob, json; json.dump([json.load(open(f)) for f in \
glob.glob('placements/*.json')], open('placements.json', 'w'))"
```

Then read which languages the app's **other published flows** offer, so the audit can say
when this one lacks a language the rest of the app speaks:

```bash
python3 -c "import json; d = json.load(open('flows.json')); \
print('\n'.join(f['id'] for f in d['data'] if f['id'] != '$FLOW' \
and f['status'] in ('published', 'dirty')))" > sibling-ids.txt
mkdir -p siblings
xargs -P 8 -I{} sh -c "$ADAPTY flows config get {} --app $APP --json > siblings/{}.json" \
  < sibling-ids.txt
python3 -c "import glob, json; flows = {f['id']: f['name'] for f in \
json.load(open('flows.json'))['data']}; json.dump({flows.get(p.split('/')[-1][:-5], p): \
[{'code': l.get('code'), 'name': l.get('name')} \
for l in (json.load(open(p))['config'].get('localization') or {}).get('locales') or []] \
for p in glob.glob('siblings/*.json')}, open('sibling-locales.json', 'w'))"
```

`flows.json` is the Phase 2 `flows list --json` output, saved to that name (page through it
the same way as placements). If this fetch fails, leave `--sibling-locales` off; nothing
else depends on it.

**Read every page.** `--page-size` defaults to 20, and stopping at page 1 reports "no
placement shows this flow" for a flow a later page attaches. If the fetch fails, run the
audit without `--placements`: the report then tells the user where to check it
themselves, instead of claiming an answer.

## Phase 4 — check

Three commands, in this order. The order matters: the two local checks name every
defect in one pass over the file already on disk, while `flows config validate` is a
network round trip — running it last means the local checks have already caught
everything they can before paying for a network call.

`verify-config.py` lives in the **`flow-generator`** skill directory, not this one — resolve
it there. Both skills ship in the same plugin, so it is always present in a plugin install;
`$FG` below is that skill's directory (a sibling of this one under `skills/`).

```bash
FG="$(dirname "<skill>")/flow-generator"        # sibling skill directory
python3 "$FG/references/verify-config.py" flow.config.json
python3 <skill>/references/audit-flow.py flow.config.json --catalog catalog.json \
  --placements placements.json --sibling-locales sibling-locales.json \
  --report --name "$NAME" --status "$STATUS" --flow-id "$FLOW"
$ADAPTY flows config validate "$FLOW" --app "$APP" --config-file flow.config.json --json
```

If `verify-config.py` is not at that path, this skill was copied out on its own without
`flow-generator`. Say so and continue with the other two gates rather than skipping silently —
it owns checks nothing else here repeats, so its absence narrows the audit and the report must
admit that.

`verify-config.py` is `flow-generator`'s structural checker (shapes, invariants,
referential integrity) — run it and report its output, never reimplement any check it
already owns. `audit-flow.py` is this skill's own script: the six completeness families
(triggers, store compliance, products, variables, localization, placeholders). Both are
stdlib-only and take the bare config, never the envelope. Both read the flow's text through its
localization catalog (`references/localization.py`, shipped beside `audit-flow.py`), so an
untranslated field is reported as showing the default language, which is what users see.
`audit-flow.py` also checks the custom fonts' iOS and Android names against what the app
bundle can carry. It downloads each font file to read the name stored in it; when a download
fails, the report asks the user to check that font in Font Book and the run goes on.

`audit-flow.py` also runs fourteen **store-review** checks, which ask whether this flow
carries a shape that has actually drawn a store rejection: six on the paywall
(`trial-toggle`, `billed-amount-not-shown`, `derived-price-louder`, `no-period-disclosed`,
`trial-terms-incomplete`, `external-purchase-link`) and eight on the onboarding around it
(`primer-skip`, `primer-grant-wording`, `permission-incentive`, `att-fake-alert`,
`rating-in-onboarding`, `signup-wall`, `exit-offer-on-dismiss`,
`purchase-looks-like-continue`). **Their findings are
advisory: they never change the verdict.** They are `risk`/`question` only, they are
printed in their own section, and **every `question` among them is excluded from the
pending count** — `external-purchase-link` and `signup-wall` always ask one, and
`billed-amount-not-shown` degrades to one when a catalogued product's row states no
billing period, so "the one question" is three checks, not one. A store-review section
can be full and the verdict can still read a clean **Ready to publish** — that is
correct, not a bug. Evidence and calibration:
`references/store-review.md`.

`flows config validate` takes `--config-file`, **not** `--config` (that flag wants a
literal JSON string and fails with `Invalid --config JSON` on a file path). It also
rejects the envelope — pass the same `flow.config.json` extracted in Phase 3.

If a `product-store-gap` question fires (a product has no store binding for a store the
audit can't confirm the app ships on), **ask the user which stores they ship on** —
never guess — then re-run `audit-flow.py` with `--stores ios,android` (or whichever
subset applies). That re-run promotes any matching question to a blocker or clears it;
report the second run's verdict, not the first.

If a `custom-action-unconfirmed` question fires, **ask the user what each listed custom
action does**, in one message, naming each by its screen and button as the finding does.
A flow cannot ask for a permission, open the rating sheet or sign anyone in on its own: the
button fires an action ID that the app's code carries out, and only the user knows which.
Map each plain-words answer to one kind and re-run with
`--custom-actions id=kind[,id=kind…]`:

| kind | the action… |
|---|---|
| `permission` | shows a system permission prompt (notifications, location, camera, health…) |
| `tracking` | shows the App Tracking Transparency prompt |
| `review` | shows the store's rating sheet |
| `sign-in` | signs the user in or creates an account |
| `other` | does anything else in the app |
| `none` | is not handled by the app yet |

Never guess a kind for the user. Report the second run's verdict, not the first; `none`
becomes a blocker, and the answers decide which store-review checks apply to which screen.
Before the answers, those checks speak in "if" form from the action ID alone.

## Phase 5 — report

`audit-flow.py --report` prints the report. **It is the content and the order of your
answer, not its final wording.** Relay it under these rules:

- **Keep all of it.** The verdict line, every numbered finding with its number and its
  fix, the grouping, the next-step lines and the check-it-yourself list. Drop, merge or
  renumber nothing — "What happens next" points back at the numbers. Send it as your
  own message text, never inside a code block: it is markdown, and a code block shows
  the user raw asterisks.
- **In the user's language.** Translate everything except what the user sees on screen
  in another tool, which stays exactly as that tool shows it: builder labels ("Restore
  purchases", "Open URL", "On Tap"), App Store Connect field names, screen names,
  product titles, placement IDs and guideline numbers.
- **About their app.** Where the report says "this screen" or "a button", you may name
  their real screen or element by its text.
- **Nothing around it.** No opener, no recap, no closing line. The report already ends
  on the one question the user has to answer. The one line that a feedback note went out
  ([Feedback note](#feedback-note)) is the only thing that may follow it.
- **When they ask why**, answer plainly at whatever length the question needs, using
  their own flow as the example. Assume they may be new to in-app purchases.

It looks like this — the shape to follow, not words to copy:

> **Not ready to publish yet: 2 things to fix first.**
> Premium onboarding · Draft · 1 screen · https://app.adapty.io/flows/1f0c…/builder
>
> **Fix before publishing**
>
> 1. There's no way to restore a purchase. Someone who reinstalls your app or moves to a
>    new phone can't get their subscription back.
>    Fix: Add a "Restore purchases" action to a button, usually a small link under the
>    purchase button. (App Store 3.1.1)
>
> 2. There are no links to your Terms of Use or Privacy Policy: the flow has no "Open
>    URL" action at all.
>    Fix: Add two links with "Open URL" actions that open those pages. (App Store 3.1.2)
>
> **Worth fixing**
>
> 3. No placement shows this flow yet, so your app can't fetch it and nobody will see it.
>    Fix: Once it's published, attach it to a placement.
>
> **What happens next**
>
> I can fix all of these. For the links, send me the web addresses of your Terms of Use
> and Privacy Policy pages. I'll show you the screen before and after, and change nothing
> until you say yes. Want me to?

Two gates ran beside the script and neither gets its own section:

- **A green gate prints nothing.** `verify-config.py` returning `OK` or `validate`
  returning `{"valid": true, "issues": []}` tells a client nothing they need to act on.
- **A failing gate becomes a numbered finding under "Fix before publishing"**, in the
  same plain words and the same what / why / fix shape as every other one — never
  pasted through as raw tool output. If `verify-config.py` warns that a `const`
  purchase has no declared product, say "this card's purchase has no product
  declaration, so the flow won't publish". Renumber the findings after it, and add its
  number to the next-step lines. If the report already carries the same problem — a
  dead quiz branch, say — do not add it a second time.

A client never sees the names `verify-config.py`, `flows config validate`,
`audit-flow.py` or any other skill — only what they mean.

If any store-review check fired, the report carries a **Store review (advisory, doesn't
block publishing)** section; the heading is its disclaimer. Translate it, never weaken
it, and never restate a store-review risk as a blocker or as a reason the flow is not ready — those
findings are hazards, not verdicts, and the verdict line already accounts for everything
that gates a release. Its checks and the reason they are advisory are in
`references/store-review.md`.

**Hand the user one link alongside that section** —
`https://adapty.io/docs/prepare-your-app-for-store-review` — as the page to read next.
Every finding in the section cites its own guideline number, which is what a developer
pastes into an appeal, but a bare guideline number sends them to a wall of policy text.
The link lives here rather than inside the findings' own `fix` strings on purpose:
`scripts/lint-links.mjs` walks `.md` files only, so a URL written into `audit-flow.py`
would be unlinted and would rot silently.

**What happens next** is printed whenever at least one finding fired. It routes every
numbered finding by who acts on it, pointing back at numbers and never restating a
finding: **Answer these first** (a question whose answer can turn it into a blocker —
"do you ship on Android?"), **I can fix …** (a flow edit, a placement, or anything else
this run can hand on), **… are yours to do in the Adapty dashboard**, and **… optional**
(a risk nobody has to act on). A group with no members prints nothing, and when every
finding is one this run can fix, the offer says "I can fix all of these". **Check these
yourself** prints only once nothing blocks, and every line there says where to look,
not only what to confirm.

## The verdict rule

**Ready to publish** only when **zero blockers fired and every open question has been
put to the user and answered**. An unanswered question is not a pass. If blockers exist,
the line reads **Not ready to publish yet: n things to fix first**. If there are no
blockers but unresolved questions remain, it reads **Almost ready: n things I could not
check**, and they are listed. **Never certify what you could not see** — a clean run over
five real sandbox flows never printed a bare **Ready to publish**, and that is the
default outcome to expect, not a bug. When the user answers a question, re-run the audit
with the answer (`--stores`) and report the new verdict.

## What you cannot check

State these plainly when they apply; never guess an answer for them. Each one tells the
user how to check it themselves.

- **Whether the app actually fetches that placement.** The audit reads which
  placements show this flow and whether they are switched on (Phase 3); it cannot see
  the app's code. If a placement shows the flow, say which, and that the app has to
  fetch it by that ID.
- **What a custom action does.** The audit lists every custom action ID and asks; it
  never assumes one asks for a permission or signs anyone in. Until the user answers,
  the verdict cannot read **Ready to publish**, and the store-review checks that depend
  on it say "if".
- **Whether the host app provides its own dismiss.** A paywall whose only action is
  `purchase` is fine if the app presents the flow modally with a system dismiss — the
  audit cannot see the host app, so this is a `question`, not a blocker, unless no
  `closeFlow`/`navigateBack` is reachable from that screen at all.
- **Why a flow is `publication_failed`.** Both gates can pass clean over the exact bytes
  of a flow sitting in that status — **no check in this audit explains it**.
  `check_meta` turns `--status publication_failed` into its own numbered `question`
  finding, and because it is a `question` it also blocks a bare **Ready to publish**
  until the user has seen it. Do not invent a cause.

  A cause is often already on disk: the Phase 3 envelope's `transform_error` is the
  transform service's own objection to the failed attempt. When it is present, **quote
  it verbatim** beside that finding — it is evidence you were handed, not an analysis of
  yours, so it does not turn the `question` into an answer and it does not move the
  verdict. When the field is absent the API did not send it, and the finding stands
  exactly as written.

## Handoff

This skill never writes. When the user says yes to the offer, invoke `flow-generator`
and point it at the findings by number — "fix blockers 1 and 2" is enough context;
`flow-generator` re-fetches the flow itself rather than trusting this run's copy. It
owns the backup, `diff-config.py`, `--expected-updated-at`, the approval gate with a
before/after render, and the actual `flows config update` call. For "no placement shows
this flow", its phase 6 attaches one once the flow is published. If `flow-generator` is
not installed, say what to change instead and give the user the builder link.

## Feedback note

**Send Adapty a feedback note only when a check got it wrong**: the user tells you a finding is
not true for their flow, or you see that a check fired on something that works, and you agree
after looking again. Nothing else from an audit goes. It tells Adapty which check to fix. Write it
in English, in this shape — the shape to follow, not words to copy:

> What I did: audited a one-screen paywall before publishing. What helped: the report named the
> screen and the button, so the user could check the finding at once. What got in the way: the
> no-terms-link check fired on a paywall whose terms link has a translated path, and this skill
> does not say that the link must contain an English word.

- **Sentiment is `negative`**: the audit told the user something that is not true. Never the
  user's mood.
- **Every sentence is about the task, this skill or the CLI**: the kind of flow, a step of this
  skill, a check and what it fired on. Nothing you read in the user's account (how their
  placements, audiences, A/B tests, products or segments are set up, any count or value) and none
  of their copy, brand, product names, file paths or business. The ids in `--context` are all
  Adapty needs to find the rest.
- **Plain words, one short sentence each.** No script, file, flag or config field names anywhere.
  The third names the check by the name the checker prints for it (`no-terms-link`), the shape it
  fired on in plain words ("a terms link with a translated path"), never the user's values, and
  says what this skill should have known.
- **`--context` carries the ids and the check**: the app id, the flow id, and the check's printed
  name — `app <app id>, flow <flow id>: no-terms-link fired on a flow that has the link`, not the
  user's words.
- **Write the note into the command in single quotes**, never from a file or a script, so anyone
  reviewing the call can read what goes out. Inside single quotes the shell runs nothing, so drop
  backticks and write "does not" for "doesn't":

  ```bash
  $ADAPTY feedback --feature flow-audit --sentiment negative \
    --message '<the note>' \
    --context 'app <app id>, flow <flow id>: <check name> fired on <the shape, generic>'
  ```

- **Always run the command once the note is due**, even when you expect it to be refused or
  blocked: what happens to it is not yours to predict.
- **Tell the user in one line, inside the reply that corrects the finding, only when the command
  printed `Feedback sent.`**: this exact sentence in their language, and no other word about the
  note anywhere in the reply: "I also sent Adapty a short note on how this went." Any other result
  (an error, a refused or blocked call, `$ADAPTY feedback --help` saying there is no such command)
  gets no line at all, not even that a note was meant to go. Never retry, never hold up the task.
- **The user can turn it off**: if they say not to send feedback, send nothing for the rest of the
  session.

## Reference

For an Adapty docs page this skill does not link — what a dashboard setting does, a store or
billing behaviour behind a finding — use the `adapty-docs` skill to locate it. Never assemble a
docs URL from a topic name.

`references/audit-flow.py` — the six-family completeness checker (stdlib only). Takes
the bare config plus the catalog JSON; `--report` prints the user-facing block, `--json`
prints raw findings, no flag prints a plain list. Exit 0 no blockers, 1 at least one
blocker, 2 usage/unreadable input. Every check is calibrated in both directions against
`tests/fixtures/` and five real flows — see the script's own docstrings
for the traps each one closes; most were wrong on first contact with real data.

`references/checks.md` — per-check evidence for every completeness check: what it looks
at, its severity and why, its calibration in both directions, and the false-positive trap
it closes. Read it before changing a check.

`references/store-review.md` — the same contract for the fourteen advisory store-review
checks: the two rejection notices verbatim with their dates, the evidence tiers, the
framing rule and why it is a rule, per-check calibration and negative-test outcomes, the
two accepted false-negative classes, the blind spots, and what was ruled out (so nobody
re-adds it from the guideline text).

## Boundaries

- **No writes, ever.** No `flows config update`, no `products create`, no `flows
  create`, no `flows delete` (there is no such command). If a fix requires changing the
  flow, that is `flow-generator`'s job. The feedback note changes nothing in the account.
- **Not conversion advice.** This skill answers "is it wired up", never "will it
  convert" — that is `paywall-teardown` for a paywall screen, `onboarding-teardown`
  for the sequence around it.
- **Not a render check.** The audit is a config-and-catalog question; it does not
  screenshot. A finding that genuinely needs a render (a selected-state defect, a
  scroll-behind-footer bug) is named as something `flow-generator`'s preview loop should
  catch, not guessed at here.
