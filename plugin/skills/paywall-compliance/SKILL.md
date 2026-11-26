---
name: paywall-compliance
description: 'Use when someone wants to know whether a paywall, an onboarding or a purchase screen will pass App Store or Google Play review, whether it breaks subscription consumer law, or why it was rejected — "will Apple reject this paywall?", "is my paywall compliant?", "check store guidelines", "App Store rejected us under 3.1.2", "do I need a restore button?", "can I put a skip on the notifications screen?", "is a free-trial toggle allowed?", "is this a dark pattern?", "is my paywall FTC-compliant?", "can our AI companion app get banned?", "what is Apple rejecting lately?". Works on an Adapty Flow Builder flow, on screenshots or designs, and on a paywall built in the app''s own code (SwiftUI, UIKit, Jetpack Compose, Flutter, React Native). Read-only. `flow-audit` runs its store checker on every flow audit.'
---

# paywall-compliance

## What this answers

**Would the App Store or Google Play reject this screen, and what to change so they don't.**
Two kinds of finding, and the difference is the point:

- **Required mechanisms** — Restore, the Terms of Use and Privacy Policy links, a way out of a
  paywall. A screen that sells without them is rejected under App Store 3.1.1 and 3.1.2. These
  are facts about the screen, so they are **blockers**.
- **Shapes that have drawn rejections** — a free-trial toggle, a per-week price louder than the
  billed amount, a Skip beside a permission prompt, a sign-up wall, an exit offer on close. Store
  review is done by people and changes without notice, so these are **risks** or **questions**,
  never a verdict. Say "Apple has rejected", never "will reject".

Around them, three more layers, each its own section of the report and none ever a verdict:

- **Consumer law** — what US, UK and EU regulators act on when a subscription is sold: renewal
  terms as visible as the offer, a "free" that is free, a personal plan that is personal, no
  shamed decline. [`references/consumer-law.md`](references/consumer-law.md).
- **The app around the screens** — what the onboarding asks for, sign-in and account deletion,
  AI and chat apps, a crowded category. [`references/app-level.md`](references/app-level.md).
- **What developers report lately** — recent rejections developers write about, matched to these
  screens. [`references/developer-reports.md`](references/developer-reports.md).

**Never certify a pass.** A clean check is not an approval, and a finding is not a rejection;
every report says both, and that it is not legal advice.

This skill is **read-only**. It never changes a flow, a product or the app's code. When the user
wants a flow fixed, hand the finding numbers to `flow-generator`; for the app's own code, show
the change and make it only on the user's yes, like any code edit.

## How you sound

Every message, not only the report:

- **A patient colleague who knows store review.** The user may be new to it. When they ask,
  answer plainly and use their own screen as the example. Friendly through patience, never
  through filler.
- **"I" for what you do, "you" for what they do.** Lead with the answer; end on the one
  thing they need to do next. No opener, no recap, no "let me know if…".
- **Plain words over raw values.** Show a value only when the user will type it or see it
  elsewhere — a builder label, a guideline number, a URL. Element ids, check names, status codes
  and tool names never.
- **Full, clickable links to the exact page.** A docs page is read as its `.md` URL; the user gets the same URL without `.md`.
- **Could not check it? Say how they can.** Do not know something? Look it up before
  saying so — the CLI, the flow, the `adapty-docs` skill.
- **Offer the outcome ("I can fix these"), never the skill that will do it.**
- **Reply in the user's language.** Builder labels, App Store Connect and Play Console field
  names and guideline numbers stay as those tools show them.

## Pick the path by what the user gave you

| The user gave | Path |
|---|---|
| an Adapty flow, by name or link, or asks about a paywall in Adapty | [Flow path](#flow-path) — the checker runs |
| screenshots, a design, a screen recording, a store-review rejection with screenshots | [Screens and code path](#screens-and-code-path) |
| the app's own paywall or onboarding code | [Screens and code path](#screens-and-code-path) |
| a rejection message and nothing else | read it, match it to a row of [`references/screens-and-code.md`](references/screens-and-code.md), then ask for the screen it names |

A flow and a screenshot of the same paywall: run the flow path; the screenshot only adds what a
render shows (a close button drawn too faint, a price cut off).

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

**`feedback` is the tool `feedback_send`,** with the same fields; its `{"status": "sent"}` answer
counts as `Feedback sent.`

**A command with no tool, and a script that runs `$ADAPTY`, need the CLI** (`segments create` has
no tool). Run that step with the CLI when it is ready. Otherwise say it needs the CLI and offer to
set it up.

**When a call fails one way,** a read may run once the other way if that way is ready. After a
write fails or times out, read the state again the way that wrote; never repeat the write the
other way.

**Neither ready:** ask which one to set up, the one this skill prefers first, then give only that
one's steps. Use your question tool if you have one; otherwise ask in one message with numbered
options.

- **The CLI:** run this skill's CLI resolution, then `adapty auth login`, which opens the browser for
  the user's sign-in. The Claude app also needs Adapty's domains allowed first:
  https://adapty.io/docs/developer-cli-cowork

  **EU account:** first check that the CLI knows the region: `ADAPTY_REGION=xx $ADAPTY auth status`
  exits 2. On any other exit, set `ADAPTY="npx --yes adapty@latest"` and keep it for the login and
  every next call, also in a new shell, whatever the version block printed. Then log in with
  `$ADAPTY auth login --region eu` (or `ADAPTY_REGION=eu`); where this skill has the user log in,
  run no login yourself and tell them to run `adapty auth login --region eu`. The user opens the
  link in a browser signed in through https://app.adapty.io/eu-login. After a damaged login file,
  log in again with the same region; if you do not know it, ask the user.
- **MCP:** the server is `https://mcp.adapty.io/mcp`, and the user signs in in the browser. The
  `adapty-skills` plugin adds it, so when your client says the server needs sign-in, only the
  sign-in is left.
  An account on Adapty's EU servers uses the EU instance, `https://mcp-eu.adapty.io/mcp`, instead.
  The plugin adds only the default server, so add the EU one in your agent by hand:
  [Adapty on EU servers](https://adapty.io/docs/eu-cluster).
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

**This skill prefers the CLI:** its checker reads the flow's config from a file, and over MCP the
whole config passes through the conversation. With MCP only, offer the CLI in one line; on a
no, save the config `flows_config_get` returns to a file and check that. The screens and code
path needs neither.

## The CLI

Resolve `$ADAPTY` once and use it for every call:

```bash
if [ "${ADAPTY-}" != "npx --yes adapty@latest" ]; then ADAPTY="adapty"; VMSG=$(
  _a() { if [ -n "${HTTPS_PROXY-}${https_proxy-}" ]; then NODE_USE_ENV_PROXY=1 $ADAPTY "$@"; else $ADAPTY "$@"; fi; }
  _v() { _a --version 2>/dev/null | sed -n 's|^adapty/\([^ ]*\).*|\1|p'; }
  command -v adapty >/dev/null 2>&1 || { npm i -g adapty@latest >/dev/null 2>&1 \
    && command -v adapty >/dev/null 2>&1; } || { echo npx; exit; }
  J=$(_a version --json 2>/dev/null) && printf '%s' "$J" | node -e 'let s = "";
    process.stdin.on("data", d => s += d).on("end", () => { try { const j = JSON.parse(s);
      if (j && typeof j.installed == "string" && (j.latest === null || typeof j.latest == "string")
        && typeof j.update_available == "boolean") process.exit(j.update_available ? 1 : 0);
    } catch (e) {} process.exit(1); });' && exit
  old=$(_v); npm i -g adapty@latest >/dev/null 2>&1 || { echo npx; exit; }
  new=$(_v); [ -n "$new" ] || { echo npx; exit; }
  [ "$new" != "$old" ] && echo "CLI updated from $old to $new." || echo "Could not update the CLI: still $new."
); [ "$VMSG" = npx ] && ADAPTY="npx --yes adapty@latest" \
  && VMSG="Could not install or update the CLI globally, so I run it through npx."
if [ -n "$VMSG" ]; then echo "$VMSG"; fi; fi
```

**Run this block as its own command, right after the readiness check `adapty auth whoami` and
before any other CLI command.** Copy it as it is: it runs `$ADAPTY version --json` and updates a
CLI that is behind or too old to have that command. If it prints a line, your reply to the user
starts with that line, in their language, with nothing added. Say nothing else about the CLI
version: no "up to date", no version number. A new shell does not keep `$ADAPTY`: set it again, to
`npx --yes adapty@latest` after the npx line, else to `adapty`.

In `zsh` a multi-word `$ADAPTY` needs `setopt shwordsplit`. Write commands out for the user with a
literal `adapty`.

## Flow path

1. **Resolve the app and the flow.** `$ADAPTY apps list --json`; if the user named the app,
   match it by title, else ask. Then every page of `$ADAPTY flows list --app "$APP" --json
   --page-size 100 --page <n>`; match the flow the user named, else show name and status and ask.
   **Never check a flow the user did not name or pick.**
2. **Fetch the config and the catalog.** The catalog lets the price checks know each product's
   billing period; read every page, since a product on a later page reads as unknown.

   ```bash
   $ADAPTY flows config get "$FLOW" --app "$APP" --json > flow.envelope.json
   python3 -c "import json; d = json.load(open('flow.envelope.json')); \
   json.dump(d['config'], open('flow.config.json', 'w'))"
   mkdir -p catalog; page=1
   while :; do
     $ADAPTY products list --app "$APP" --json --page-size 100 --page $page > catalog/$page.json
     pages=$(python3 -c "import json; m = json.load(open('catalog/$page.json')).get('meta') or {}; \
   print((m.get('pagination') or {}).get('pages') or 1)")
     [ "$page" -ge "$pages" ] && break; page=$((page + 1))
   done
   python3 -c "import glob, json; json.dump({'data': [p for f in glob.glob('catalog/*.json') \
   for p in json.load(open(f))['data']]}, open('catalog.json', 'w'))"
   ```

3. **Check.**

   ```bash
   python3 <skill>/references/store-check.py flow.config.json --catalog catalog.json \
     --report --name "$NAME"
   python3 <skill>/references/store-check.py flow.config.json --screens
   ```

   `--screens` prints each screen's text and what each button does, in the order people reach
   them. Go through [`references/consumer-law.md`](references/consumer-law.md) and
   [`references/app-level.md`](references/app-level.md) against it.

4. **Ask what the checker cannot know, then run it again with the answers.** Ask everything in
   one message, and report the second run, not the first:
   - **Where the app sells** (the US, the UK, the EU, elsewhere) and **who bills** (the stores,
     or the app on the web), for the consumer-law rows. Never infer either from the currency.
     When a screen says "free" about more than a trial, also ask whether the app has a free tier.
   - **Each app-level row the screens make relevant** (an account, an AI provider, user content),
     as one short question each.
   - **Which stores the app ships on**, unless the user said. Several rules are iOS-only (the
     trial toggle, permission screens, a sign-up wall, an exit offer) and one is Google Play's
     (a purchase button worded like the buttons before it). Re-run with `--stores ios`,
     `--stores android` or `--stores ios,android`.
   - **What each custom action does**, when the flow has one. A flow cannot ask for a permission
     (other than push notifications), open the rating sheet or sign anyone in on its own: a button
     fires an action ID that the app's code carries out. Name each by its screen and button, map
     each answer to one kind, and re-run with `--custom-actions id=kind[,id=kind…]`:

     | kind | the action… |
     |---|---|
     | `permission` | shows a system permission prompt (notifications, location, camera, health…) |
     | `tracking` | shows the App Tracking Transparency prompt |
     | `review` | shows the store's rating sheet |
     | `sign-in` | signs the user in or creates an account |
     | `other` | does anything else in the app |
     | `none` | is not handled by the app yet |

     Never guess a kind for the user. Until they answer, the onboarding findings speak in "if"
     form from the action ID alone.

5. **Read what developers report lately**: [`references/developer-reports.md`](references/developer-reports.md).
6. **Report** (below): the checker's findings, then the consumer-law and app-level findings with
   the user's answers, then the developer reports, each in its section.

`flow-audit` runs the same store checker on every audit and merges its findings into its own
report. After a flow audit, skip the `--report` run and use that report's store findings; the
other layers still run from `--screens` on.

## Screens and code path

Open [`references/screens-and-code.md`](references/screens-and-code.md) and go through **every
row** against what you were given. It is the same rule set the checker runs on a flow, written
for a picture and for code: each row says what to look for in a screenshot, what to look for in
the code, and the fix.

- **Screenshots.** Read every screen in the order the user would see them. A rule about the
  screens before the paywall (a purchase button worded like the ones before it, a sign-up wall)
  needs those screens: ask for them, or say the rule was not checked.
- **Code.** Find the paywall and onboarding views, then follow each button to what it calls. A
  label says what a button claims; only the handler says what it does. Read the restore call, the
  legal links, the close path and every system prompt the screens trigger.
- **Then the other layers:** [`references/consumer-law.md`](references/consumer-law.md),
  [`references/app-level.md`](references/app-level.md) and
  [`references/developer-reports.md`](references/developer-reports.md), with the same questions
  as the flow path's step 4 (where the app sells, who bills, the app-level rows) in one message.
- **Never report a row you could not see.** A screenshot cannot show what a button does, and code
  cannot show how loud a price looks once rendered. Put each such row under "Tell me, and I can
  check" with the one thing you need.

Report in the shape below, the same as the checker's.

## Report

The flow path's `--report` prints the report; for screens and code, write it in the same shape.
**It is the content and the order of your answer, not its final wording.** Keep every numbered
finding with its fix and drop nothing; number the findings in the order the report shows them,
and send it as your own message text, never inside
a code block. Translate everything except builder labels, store field names and guideline
numbers. No opener, no recap.

It looks like this — the shape to follow, not words to copy:

> **The stores will reject this as it is: 1 thing to fix first.**
>
> **Fix before you submit**
>
> 1. There is no way to restore a purchase. Someone who reinstalls your app or moves to a new
>    phone cannot get their subscription back.
>    Fix: Add a "Restore purchases" button, usually a small link under the purchase button.
>    (App Store 3.1.1)
>
> **Has drawn rejections**
>
> 2. The per-week price is bigger than the price people are billed.
>    Fix: Make the yearly price the largest price on the card. (App Store 3.1.2(c))
>
> **Consumer law**
>
> 3. "Renews automatically" is only in the grey footnote, while the free week is the largest
>    text on the screen. Regulators have acted on renewal terms hidden like this.
>    Fix: Put "Free for 7 days, then $59.99/year, renews until you cancel" under the button.
>    (US: ROSCA; EU: Consumer Rights Directive Art. 6)
>
> **Tell me, and I can check**
>
> 4. Does the plan on "Your plan is ready" change with the quiz answers? If it is the same for
>    everyone, the "Analyzing your answers" screen claims a personal result that is not.
>
> **What developers report lately**
>
> - One developer reports a rejection under 5.1.1(v) for a required date of birth in an
>   onboarding quiz (Apple Developer Forums, October 2026: <link>).
>
> Store review is done by people and changes without notice: a clean check is not an approval,
> and a finding is not a rejection. This is not legal advice.
> What the stores look at: https://adapty.io/docs/prepare-your-app-for-store-review

The sections, in this order, each only when it has something: "Fix before you submit", "Has drawn
rejections", "Consumer law", "Tell me, and I can check" (the questions of every layer), "What
developers report lately", then what you could not check (below), the disclaimer and the link.
The verdict line counts what is under "Fix before you submit". With at least one blocker it reads
"**The stores will reject this as it is: n things to fix first.**", whatever the checker printed.

- **An answer settles a question.** When the user's answer confirms what a checker question asked
  about (the app adds no close button, the link is a payment page, the core needs no account), the
  finding moves to the section its rule puts it in: a missing mechanism under "Fix before you
  submit", a shape under "Has drawn rejections". An answer that clears it drops it.
- **One thing, one finding.** When a consumer-law row repeats a store finding (the same button, the
  same price), add one unnumbered line that points to that finding and cites the law; never a
  second fix.
- **Nothing found in a layer:** say in one line that the consumer-law and app-level rows found
  nothing, so a clean store verdict is not read as the whole check.

Then **one next step**: for a clean flow, offer a full flow audit (products, prices, the placement)
before it is published; for a flow with findings, "I can fix these" (on a yes, invoke `flow-generator` with
the finding numbers). For a paywall or onboarding in the app's code or in screenshots, offer to
rebuild it as an Adapty flow with the fixes in (on a yes, invoke `flow-generator` with the screens
and the finding numbers): a flow can be changed later without a new app release. Say in the same
breath that each change is still held to the guidelines ([`references/app-level.md`](references/app-level.md#changing-screens-after-review)).
When the user wants to stay in code, offer the code change instead.

**A flow finding that holds in some of the countries the app sells in and not in others** (a
rule of one storefront, like a link to pay on the web): offer, beside the fix, to keep the allowed version where it
is allowed, with a copy of the flow shown to those countries only. The shape, the country
attribute and the steps are in [`references/country-versions.md`](references/country-versions.md);
`flow-generator` and `audiences` do the writes on the user's yes.

## What you cannot check

Say these when they apply, each with where the user checks it:

- **Products approved in App Store Connect** before review sees the paywall, or the reviewer gets
  empty prices — App Store Connect, the subscription's status.
- **Terms and Privacy linked in the store listing too**, not only in the app — App Store Connect,
  the app's information page and the subscription group's metadata.
- **Prices matching** the store listing and any marketing.
- **Whether the reviewer reaches the paywall at all** — a placement the app never fetches shows
  nothing; that is `flow-audit`'s question.

## Feedback note

**Send Adapty one feedback note per run, with its first verdict**, on every path, good runs
included (a re-check later in the run sends none): it tells
Adapty how the job went for **you** with this skill and the CLI. Send it with the CLI or MCP when
one is ready; never set one up only for the note. Write it in English, in one of these shapes — the
shape to follow, not words to copy:

> Checked a two-screen paywall flow and found two missing legal links before submission.

> What I did: checked an onboarding from screenshots. What helped: the rule table named what a
> picture cannot show. What got in the way: the developer forum refused every thread page, and
> this skill does not say where else to read recent rejections.

- **Sentiment is your own outcome, never the user's mood, nor how many findings there were**:
  - `positive` — the check ran the way this skill describes, whatever it found. One sentence on
    what you checked and the kind of thing it found.
  - `neutral` — done, after a wrong turn, a workaround, or a source that would not load.
  - `negative` — this skill, its checker or the CLI stopped you, or a check told the user
    something that is not true and you agree after looking again.

  Neutral and negative notes carry all three parts. Name a check by the name the checker prints
  for it, or the row's heading on the screens and code path.
- **Every sentence is about the task, this skill or the CLI**, in plain words, one short sentence
  each: none of the user's copy, brand, product names, code, file paths or account values.
- **`--context` carries the ids and the path**: `app <app id>, flow <flow id>: flow path`; for
  screenshots or code, `screens` or `code`.
- **Write the note into the command in single quotes**, never from a file or a script. Inside
  single quotes the shell runs nothing, so drop backticks and write "does not" for "doesn't":

  ```bash
  $ADAPTY feedback --feature paywall-compliance --sentiment <positive|neutral|negative> \
    --message '<the note>' \
    --context '<ids>: <path>'
  ```

- **Always run the command once the note is due**, and tell the user in one line, inside the
  message with the verdict, only when it printed `Feedback sent.`: "I also sent Adapty a short
  note on how this went." Any other result gets no line. Never retry, never hold up the task.
- **A finding the user disputes later** gets its own note then, `negative` when you agree the
  check was wrong.
- **The user can turn it off**: if they say not to send feedback, send nothing for the rest of the
  session.

## Reference

- `references/store-check.py` — the flow checker (stdlib only). `--report` prints the report,
  `--json` the findings `flow-audit` merges. Exit 0 no blockers, 1 at least one, 2 usage or
  unreadable input.
- [`references/screens-and-code.md`](references/screens-and-code.md) — every rule, for a picture
  and for code.
- [`references/consumer-law.md`](references/consumer-law.md) — what regulators act on, for
  every path.
- [`references/app-level.md`](references/app-level.md) — the app around the screens.
- [`references/developer-reports.md`](references/developer-reports.md) — where developers write
  about rejections and how to read them.
- [`references/country-versions.md`](references/country-versions.md) — a flow shown in one version
  where a rule allows more and another everywhere else.
- `store-check.py --screens` — each flow screen's text and buttons, for the three above.
- [`references/mechanisms.md`](references/mechanisms.md) — evidence and calibration of the four
  required mechanisms. Read it before changing one.
- [`references/store-review.md`](references/store-review.md) — the rejection notices, evidence
  tiers and calibration of every advisory check, and what was ruled out. Read it before changing
  one.

For an Adapty docs page this skill does not link, use the `adapty-docs` skill. Never assemble a
docs URL from a topic name.

## Boundaries

- **No writes.** A flow change is `flow-generator`'s, a segment or a placement audience is
  `audiences`'s; a code change is the user's yes away.
- **Not conversion advice.** What a store will accept, never what will convert — that is
  `paywall-teardown` for a paywall screen, `onboarding-teardown` for the sequence around it.
- **Not legal advice.** Consumer-law findings name what regulators act on; whether a law applies
  is a lawyer's call, and the report says so.
- **Not a flow audit.** Products, prices, variables, languages and placements are `flow-audit`'s,
  which runs this skill's checker inside its own report.
