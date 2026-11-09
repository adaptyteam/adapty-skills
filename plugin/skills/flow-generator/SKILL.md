---
name: flow-generator
description: Use when a user wants to change an Adapty flow by editing its builder config JSON — add a locale, translate a paywall or onboarding, rewrite copy, add/remove/reorder screens, add tabs or plan pickers, wire quiz branching, or build an onboarding sequence — and also once a flow is published, to point a placement at it so an app can fetch it. Triggers on "edit my flow config", "add a language to my paywall", "translate my onboarding", "remove a screen from the flow", "add tabs to my paywall", "show the user's name or coin balance on my paywall", "build me a paywall like this", "build me an onboarding", a supplied Adapty flow config, and on "publish my flow", "I published my flow", "attach my flow to a placement", "create a placement for this flow", "my flow does not show up in the app", and on "how are my screens connected", "show me the flow map", "where does this button lead".
---

# Flow generator

Read an Adapty flow's builder config, transform it, check the result, and write it back.
Transforming a config that exists is the default, and the safer path: everything you emit is then
grounded in a document that already works.

**Authoring a new flow is also in scope**, and two things — and only these two — genuinely
cannot be synthesized:

- **An image you have no readable FILE for.** Given a path you can now upload it —
  `flows media upload` ([media.md](references/media.md)). An image you can only *see* — pasted or
  attached into the conversation — is not one you have: ask for a path. With no file there is
  nothing to upload, so its catalog entry stays empty, never a made-up URL (trap 5). **SVG uploads
  fail**, so a monochrome glyph is authored inline in `_meta.icons`; a graphic no element can
  express, you draw and rasterize ([media.md](references/media.md)). An icon is **not** in this
  list: `python3 references/icons.py --search <word>` resolves any phosphor glyph, and an
  invented name draws blank however good your markup is (trap 23).
- **Real store prices.** They come from the store, not from Adapty; `products create --price-usd`
  is only the USD base a store push starts from.

Everything else is reachable: product UUIDs from `adapty products list` (or `products create`),
offer ids from `adapty product-offers list`, `theme` colours sampled off a reference screenshot,
and icon markup resolved from the bundle `references/icons.py` ships.

**`flowProductId`** — the per-screen declaration in `_meta.screens[].products[]` — is derived, not
waited for: `flowkit.predeclare(screen_id, products)` writes it, and **`verify-config.py` warns on a
binding it does not declare** (it says the fix). When *rewriting* a flow, carry the live
`_meta.screens` forward instead of regenerating it — **and `screens[].products` with it**, the
screen-owned registry that `_meta` is derived from. Never write `"products": []`: absent and empty
mean opposite things to the builder. When *authoring*, `flowkit.screen()` writes the registry and
the structured product refs for you, from the screen's own bindings — bind an offer with
`product(..., offer_id=...)` and a dotted price variable picks it up
([products.md](references/products.md)). A yearly product sold in monthly payments is
`product(..., billing_plan='monthly')`, with its own `<uuid>@monthly.<field>` variables
([products.md → A yearly product can be sold under its monthly plan](references/products.md#a-yearly-product-can-be-sold-under-its-monthly-plan)).
When you do author, [`references/flowkit.py`](references/flowkit.py) owns the mechanical parts —
the `hierarchy`/`map` split above all — and [patterns.md](references/patterns.md) owns the shapes.

It also covers conditions (`when`/`ref`/`all_`/`not_empty`), all fourteen action types, the
eight inputs and the tabs composite — each raising on the shape the transform service refuses,
`interactions=` included (the error says what to pass).

## How you sound

Every line the user reads, the fixed blocks included:

- **"I" for what you do, "you" for what they do.** Lead with what changed; end on one next step.
  No opener, no recap of their request, no narration of phases.
- **A patient colleague, not a log.** Assume they may be new to flows; say what a step is for in
  their terms, once.
- **Bold at most one thing per block.** A fixed block's heading is that one thing; step labels,
  list lead-ins and the things to check stay plain.
- **Raw values only when the user will type them or see them elsewhere** — a flow name, a screen
  name or button label as the builder shows it, a price, a link. Never element or screen ids,
  internal action names (`closeFlow`, `navigate`), config keys (`_meta.screens`), language codes,
  file names, element counts, checker output (`valid: true`) or tool names. Say what it means:
  "the Continue button now opens the paywall", "Spanish", "the publish check passed".
- **Full, clickable links**, bare on their own line, never in backticks.
- **Reply in the user's language**, the fixed blocks too. Builder labels stay exactly as the
  builder shows them.

## What you print

The user reads your messages, not this file. Keep them short.

**Four fixed blocks, and nothing else is fixed:** the approval ask before a write and the closing
callout after one, both in phase 5; the **missing-assets block**, printed in phase 2 whenever a
build has assets nobody has a file for; and the **placement ask** in phase 6, before an
irreversible developer ID is spent. Fill their slots and do not pad them.

The missing-assets block, when it goes out and its slots: [build.md → The missing-assets block](references/build.md#the-missing-assets-block).

**Name what the builder cannot do yet, beside it**: for each behaviour or effect in the design the
flow does not perform (creating an account, a permission prompt, a blur), say what the screen really
does ("sends `create_account` to your app; the flow creates no account") and the routes that fit — a
custom action your app answers with its own screen, a second flow on its own placement if the
onboarding continues after it, or an image or a video (uploaded in the builder) of an effect — and
call it "not in the builder yet", never impossible.
When any route is a custom action, list the action IDs and offer to write their handlers in the
app: "I can add the code that answers these in your app. Want me to?" — on a yes, hand the IDs to
the `adapty-integration` skill, which owns app code; without it, find the platform's "Respond to
actions" page through the `adapty-docs` skill and link it.

Images up to ~2.5 MB you can upload; **SVG, fonts, video and anything larger are builder-only**
([fidelity.md](references/fidelity.md)). Phase 5's callout carries the outstanding count as one
line, not a repeat of the table.

**Send Adapty one feedback note at the end of every run that called the CLI** — whether it wrote,
handed over a file, or stopped on something you could not get past. It tells Adapty how the job
went for **you** with this skill and the CLI, good runs included. Write it in English, in one of
these shapes — the shape to follow, not words to copy:

> Added German to a six-screen onboarding.

> Declined to <what was asked, in generic words>, because <the limit this skill states>.

> What I did: tried to save a button label change on a one-screen paywall. What helped: this skill
> said where button labels live, so the edit was one step. What got in the way: flows config update
> failed twice with http_500 (request id req_7f3a9c), and this skill does not say whether a retry
> is safe.

- **Sentiment is your own outcome, never the user's mood**:
  - `positive` — done the way this skill describes, **or declined because this skill says it
    cannot be done**. One sentence on what you did or declined and why, and nothing about checks,
    saving or how it went: the grade already says that.
  - `neutral` — done, after a wrong turn or a workaround, **or around a problem you found in the
    flow and left alone**. The third part names that problem by its shape ("a button opens a screen
    the flow no longer has"), never by the user's values.
  - `negative` — this skill or the CLI is what stopped you, or you delivered something you know is
    wrong.

  Neutral and negative notes carry all three parts.
- **Every sentence is about the task, this skill or the CLI**: the kind of change, a step of this
  skill, a command and its error. Nothing you read in the user's account (how their placements,
  audiences, A/B tests, products or segments are set up, any count or value) and none of their
  copy, brand, product names, file paths or business. The ids in `--context` are all Adapty needs
  to find the rest.
- **Plain words, one short sentence each.** No script, file or flag names in the first two parts.
  The third names the command and its error, and says what this skill or the CLI should have told
  you.
- **`--context` carries the ids and the request**: the app id, the flow id, and what was asked in a
  generic form — `app <app id>, flow <flow id>: rename a button and save the flow`, not the user's
  words.
- **Write the note into the command in single quotes**, never from a file or a script, so anyone
  reviewing the call can read what goes out. Inside single quotes the shell runs nothing, so drop
  backticks and write "does not" for "doesn't":

  ```bash
  $ADAPTY feedback --feature flow-generator --sentiment <positive|neutral|negative> \
    --message '<the note>' \
    --context 'app <app id>, flow <flow id>: <what was asked, generic>'
  ```

- **Tell the user in one line, inside your closing message, only when the command printed
  `Feedback sent.`**: in their language and with nothing about what the note said, "I also sent
  Adapty a short note on how this went." Any other result (an error, a refused or blocked call,
  `$ADAPTY feedback --help` saying there is no such command) gets no line at all, not even that a
  note was meant to go. Never retry, never hold up the task.
- **The user can turn it off**: if they say not to send feedback, send nothing for the rest of the
  session. If they tell you mid-run that this skill or the CLI got something wrong, send a note
  about it then, in their words where they gave them.

**Everything else is one line or omitted** — what changed, what still needs them (products to
attach, assets to upload), any decision where two answers were defensible, and what your checks
did and did not cover. **Say each thing once**: if the approval ask already named it, the closing
note does not repeat it.

Do not narrate phases, restate the config back, list warnings you did not act on, or explain the
CLI to someone who asked for a flow.

## References

Each file **owns** its facts; link rather than restate, or the copies drift.

| File | Read it when |
| :--- | :--- |
| [flow-schema.md](references/flow-schema.md) | **Before any edit.** The envelope, `## Invariants`, `## Shape traps`, and `## Vocabulary` — the map from what a user asks for to what the JSON calls it |
| [validate.md](references/validate.md) | `validate` says no, or you want to know what a green run does *not* prove |
| the `adapty-docs` skill | You need an Adapty docs page nothing here links — a dashboard behaviour, a CLI or API detail. It routes to the right docs index instead of guessing a URL |
| [preview.md](references/preview.md) | A render surprises you: what it cannot show, what it costs, the four disagreeing surfaces, and what to do when it fails. Also the fidelity and teardown passes, the flow map and the device-preview QR |
| [build.md](references/build.md) | **Phase 2** for a new flow or a screen you design: creating it, the design modes, the teardown, products, custom tags, assets, the missing-assets block |
| [publish.md](references/publish.md) | Before a publish, and before the callout of a flow a placement shows: reach, Terms and Privacy, the weigh, `flows publish` itself |
| [custom-tags-code.md](references/custom-tags-code.md) | The user said yes to passing the flow's custom tags from their app's code |
| [fidelity.md](references/fidelity.md) | A reference image was given — the per-element inventory, the gap-closing ladder, and what becomes a user ask |
| [media.md](references/media.md) | The screen has an image: the upload's limits, element-versus-`fill` shapes, geometry, and when to rasterize |
| [products.md](references/products.md) | Before touching a `product` element — `products create` writes to a live dashboard |
| [merge.md](references/merge.md) | The flow has been edited by a human since it was generated, or you are tempted to re-run a build script over an existing flow |
| [transforms.md](references/transforms.md) | You hit a point where two answers are defensible and silence is the only wrong one |
| [patterns.md](references/patterns.md) | You need a composite you cannot guess: tabs, progress bars, toggles, countdowns, screen transitions, an element that appears after a delay, plan cards |
| [placements.md](references/placements.md) | **Phase 6** — the procedure and the placement ask, every `placements` refusal and who owns it, the `update` variant, the dashboard URLs and their params, and why the developer ID is irreversible |
| the **`paywall-teardown`** skill | **Phase 2** when *you* choose the design of a **screen that sells**, **phase 4** to grade what you built. It owns whether the screen sells; this skill owns the JSON |
| the **`onboarding-teardown`** skill | The same two phases when what you are choosing is a **sequence** — onboarding, welcome, quiz, activation. It owns the shape of the flow and the onboarding→paywall seam. A flow that is both runs both |
| the **`ab-tests`** skill | **Phase 6**, when the user wants this flow tested against another flow. It owns the test from the draft to the stop; this skill hands it the published flow ids |
| the **`adapty-integration`** skill | **Phase 6**, once a placement points at the flow. It owns the app side — the fetch, the render and the call sites — and this skill hands it one thing: the placement developer ID |

Executable, all under `references/`: `flowkit.py` (authoring), `icons.py` (glyph lookup,
any phase), `localization.py` (phase 2, the catalog), `verify-config.py` (phase 3),
`validate-with-schema.mjs` (phase 3), `diff-config.py` (phase 2 and phase 5), `montage.py`,
`render-measure.py` and `canvas.py` (phase 4, and whenever someone asks how screens connect), `preview-with-playwright.mjs` (phase 4, through `shoot.sh`),
`mobile-preview.mjs` (phase 5, the device-preview QR), `weigh-config.py` (phase 2 before an
upload, phase 5 before a write or a publish).

## CLI or MCP

This skill reaches Adapty through the Adapty CLI or the Adapty MCP server. Its commands are written
for the CLI, and over MCP each one is a tool call. Before the first call, check both, pick one way,
and keep it for the run:

- **The CLI is ready** when `adapty auth whoami` shows an account. Install nothing for this check.
- **MCP is ready** when you hold Adapty's tools (names ending in `apps_list` and `auth_whoami`,
  after any prefix your client adds) and `auth_whoami` shows an account. A `Not Found` or any other
  error from `auth_whoami` means MCP is not ready: switch to the CLI via `$ADAPTY`, setting it up if it is not ready either.

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

**This skill prefers the CLI:** `gates.sh`, `shoot.sh` and the preview script run it, and over
MCP a whole config or image passes through the conversation as a tool argument. With MCP only,
offer the CLI in one line; on a no, go on over MCP, run the local checks yourself, and name each
check that did not run.

**A 5xx (a `520` too) on `flows config update` may or may not have landed:** `config get` and
diff before any retry.

**Over MCP, check a whole config's size before you send it.** Configs above roughly 30 KB have
failed to reach the tool. Above that, offer the CLI once; never seed a stub and push the rest
through the edit tool in compressed pieces.

## The CLI surface

```
$ADAPTY auth login                                             # code + link, waits; run it as phase 1 says
$ADAPTY auth whoami                                            # verifies the token server-side
$ADAPTY apps list --json                                       # to get <APP_UUID>

$ADAPTY flows list   --app <APP_UUID> [--page N] [--page-size N]    # page-size max 100
$ADAPTY flows create --app <APP_UUID> --name <name>            # row only; always `draft`
$ADAPTY flows get    <FLOW_ID> --app <APP_UUID>
$ADAPTY flows config get      <FLOW_ID> --app <APP_UUID> --json     # errors until first write
$ADAPTY flows config validate <FLOW_ID> --app <APP_UUID> (--config-file <f|-> | --config <json>) --json
$ADAPTY flows config preview  <CONFIG_FILE> [--screen <id>] [--device <id>] [--orientation …]
$ADAPTY flows config update   <FLOW_ID> --app <APP_UUID> \
    (--config-file <file|-> | --config <json-string>) \
    [--expected-updated-at <int>] [--remote-configs <json>]   # left out, the stored ones are cleared
$ADAPTY flows media upload    <IMAGE_FILE> --app <APP_UUID> --json  # PNG/JPEG/WEBP, < ~2.5 MB; no SVG, no GIF
$ADAPTY flows update  --app <APP_UUID> <FLOW_ID> --name <name>      # --name required; 405 in prod, rename in the builder
$ADAPTY flows publish --app <APP_UUID> <FLOW_ID> [--yes]            # async; 404 in prod, see below
```

**Resolve `$ADAPTY` once, here, and use it for every command.** A global `adapty` is frequently old
— measured at `0.3.0` on a real machine, which has no `flows` topic — and three agents read that as
"validate and preview do not exist" and skipped phases 3 and 4:

```bash
adapty --version                                   # >= 0.8.0 ?  ADAPTY="adapty", done
npm i -g adapty@latest >/dev/null 2>&1 \
  && ADAPTY="adapty" \
  || ADAPTY="npx --yes adapty@latest"              # fallback: prefix not writable
```

**In `zsh` — the macOS default — a multi-word `$ADAPTY` is not split into words**, so every command
below fails with `command not found: npx --yes adapty@latest`. Run `setopt shwordsplit` once in the
same shell (verified), or call `npx --yes adapty@latest` in full. That error is a shell problem,
never evidence the command or the CLI is missing. A letter after `$VAR:` is a zsh modifier too
(`$FLOW:l` lowercases the value), so a colon that follows a variable gets braces: `${FLOW}:`.
`gates.sh` and `shoot.sh` run in `bash` and split it themselves, so hand them the command as a
prefix: `ADAPTY='npx --yes adapty@latest' references/gates.sh …`.

**Install once; do not wrap every call in `npx`.** The wrapper costs ~1 s *per call* against
0.07 s installed, and a run makes dozens. Where the global prefix is not writable the `npx` form
still works, and there `--yes` is not optional: without it npx stops to ask permission to install.

Declare a command unavailable only after `npx --yes adapty@latest` *and* `npx --yes adapty@beta`
both lack it — never from a version number you read somewhere.

**On Windows, run the `.sh` scripts from Git Bash, and where this skill writes `python3`, call
`python -X utf8` (or `py -3 -X utf8`).** `python3` there is usually the Microsoft Store stub, and
"Python was not found" means the wrong interpreter, never a broken script; `-X utf8` keeps non-Latin
copy from passing through the console code page. `gates.sh` and `shoot.sh` find a working Python,
and Chrome or Edge, themselves; set `PYTHON=` or `CHROME=` only when they say they cannot.

**`flows media upload` works in production.** It takes a local image file and prints a live CDN URL
to bind into the config, so an image the user *handed you a file for* is yours to place, not a user
ask. Two limits shape when you reach for it: **SVG
returns `http_500`**, and the ceiling is **~2.5 MB of file bytes** (a bare `http_400` means too
large). **Run it with `--json` redirected to a file, and keep the file**: the human output omits
`preview_base64`, the config binds it as `previewValue`, and nothing else returns it — so that
file is the asset's record, and a second upload is a second asset rather than a way back to the
value. Call shape, the three values to capture, the two config shapes they bind into, how to get
a preview back when you no longer have one, and the geometry: [media.md](references/media.md).

**`flows publish`:** whether this build has it, its asynchronous status and the poll, which failure is real, and the deployment gate: [publish.md → Running `flows publish`](references/publish.md#running-flows-publish).

**There is still no `flows delete`.** Deleting is a dashboard action, so never claim to have
deleted a flow. Never write a command name the CLI does not have, and never invent a flag —
`config validate` takes only `--app`, `--config`/`--config-file` and `--json`.

Four facts about the config commands that are not guessable:

- **`config get` returns an envelope, not the config**: `{config, remote_configs, status,
  updated_at}`, plus `publication_status`, `transform_error` and `publication_error` when the last
  publish failed; `status` can be missing, so read it with a default. The document you transform is the `config` field, and both `update` and
  `validate` take that field alone. Handing `validate` the envelope returns
  `Invalid flow input` — which reads exactly like a broken config and is not one. (`preview`
  is the odd one out: it accepts either.)
- **`status` is not yours to write.** It belongs to the envelope and is **discarded** if you put
  it inside `config`. Do not emit it in a config you send to `update`, and do not treat its
  absence as a defect. (A *browser export* does carry `status` and `id` at the top level — that
  is a different document shape, and phase 5 covers what to do when the user wants a file.)
- **The lock token comes from `flows config get` and from nothing else.** Two fields share the
  name `updated_at` and mean different things. The `config get` envelope carries it as epoch
  milliseconds (`1787210847609`), and it marks the last change to the **content**. That value
  is the optimistic lock. `flows get`, `flows list` and `flows create` carry an **ISO string**
  (`2026-09-24T12:14:40Z`), and it marks the last change to the flow **row** (name, status). You
  already hold that one after a publish poll, and it is the wrong one.
- **The token is the one your draft is based on, so it lives in `flow.working.json`.** Phase 2's
  `config get` writes it there, and every successful `config update --json` you move into that file replaces it
  with the new one (the echoed value equals the next `get`'s). Read it from that file, never from a
  fresh `config get` just before the write: a fresh read is whoever saved last, which makes the
  lock pass over the very edit it exists to catch.

  ```bash
  UA="$(jq -r .updated_at flow.working.json)"   # right: the version your draft was patched from
  $ADAPTY flows config update <FLOW_ID> --app <APP_UUID> --config-file draft.json \
    --expected-updated-at "$UA" \
    --remote-configs "$(jq -c '.remote_configs // []' flow.working.json)" \
    --json > write.json && mv write.json flow.working.json
  ```

  The `mv` is only on success: a failed write prints its error JSON to stdout, and redirecting
  straight into `flow.working.json` would replace your token with it.

  A raw ISO string fails before anything is sent (`Expected an integer`, exit 2). Never convert it
  to milliseconds to make it fit: the write comes back `409` with *"This flow configuration was
  already updated by <name>"*, naming a person who did not touch it. A `409` on a token from
  `flow.working.json` is a real edit: phase 5 says what to do. Never drop the flag, and never
  re-fetch only the token, to get past it.
- **`config update` has no dry run.** `validate` and `preview` are the pre-flight checks, and
  both run *before* a write — see phase 5 on why that ordering matters.
## The six phases

### 1. Resolve the invocation, then authenticate

**First** set `$ADAPTY` as [the CLI surface](#the-cli-surface) describes — probe
`adapty --version`, and if it is old **install once globally** rather than paying the npx wrapper's
~1 s on every later call (`npx` only as the fallback). Do it before the first command, not after one fails,
and print the version you resolved in the same command you run next so the two cannot disagree.

Then `$ADAPTY auth whoami`. It hits the server and prints the name and companies, so it proves the
token works. Prefer it to `auth status`, which only reports what is stored locally and does not
verify it — it prints the stored name and token prefix even when the token no longer works.

If it fails with `Could not reach …` (`network_error`), the network is the problem, not the token,
so do not log in. With `HTTPS_PROXY` or `https_proxy` set, Node is ignoring the proxy:
`ADAPTY="env NODE_USE_ENV_PROXY=1 $ADAPTY"` carries the fix into every call, the scripts' included
(Node 22.21 or later, or 24; `adapty --version` names the Node it runs on).

Any other failure: log in. **`auth login` opens a browser only at a terminal: from your shell it
prints a code and a link, then waits in the foreground** for the user to approve, holding your
shell, and some agents kill it at their command timeout. Run it detached and read the link off its
log:

```bash
L="${TMPDIR:-/tmp}/adapty-login.log"
$(command -v setsid) nohup $ADAPTY auth login > "$L" 2>&1 < /dev/null &   # setsid only where it exists
for i in $(seq 20); do grep -q 'visit:' "$L" && break; sleep 1; done; cat "$L"
```

Send the code and the link as your next message, on their own: the code expires within minutes.
With a display, also `open` the link for them (`xdg-open` on Linux). Then run
`$ADAPTY auth whoami` every few seconds until it succeeds; the login is saved to disk, so later
shells have it. Never start a second login while the first waits: its code voids the link the
user is opening. When the log says `The code expired before authorization`, start one more and
say why there is a new link.

Then `$ADAPTY apps list --json` for the `<APP_UUID>` every later command needs.

**Then check where the request actually starts, because not every run is an edit.** *"I published
my flow"*, *"how do I get this into my app"*, *"nothing shows up in the app"* is a **phase 6**
request: the flow exists and is published, and what is missing is the placement pointing at it,
the app's own call site, or users reaching it. Go straight to phase 6 — phases 2-5 have no work to do — and say that is
what you are doing, so a user who did want an edit can redirect you.

*"How are my screens connected"*, *"where does this button lead"* is a **read**: `flows config get`
the flow into `flow.backup.json`, render its screens if they want thumbnails, and open the map
([phase 4](#4-preview-and-iterate-until-it-looks-right)). Nothing is written, so no approval.

### 2. New flow, or existing flow

Decide this explicitly and say which you chose, because the two paths differ in what they can
destroy.

**Existing flow** — the user names it, or `flows list` and confirm the match back to them
before touching it. Read its `status` with `flows get`: `archived` is a flow deleted in the
dashboard, and every write to it is refused with `Flow is deleted`, so say so and offer a new flow
on a yes (`flows create`, seeded from this config if `config get` still returns it). Then
`flows config get`, and **keep its `updated_at`** for the write, not the one `flows get` or
`flows list` printed.

**Take a backup before the first edit.** `config update` replaces the whole config and there is no
undo, so the copy you fetched is the only way back. Keep it in the project or another folder that
survives a reboot, never `/tmp` or `$TMPDIR`: there is no version history to fetch it from again.

```bash
$ADAPTY flows config get --app $APP $FLOW --json > flow.working.json
cp flow.working.json flow.backup.json
jq .config flow.working.json > draft.json
```

**If `config get` dies with `Maximum call stack size exceeded`, the flow is too large for Node's
default stack, not broken.** Run the installed CLI under a bigger stack:
`node --stack-size=4000 "$(npm root -g)/adapty/bin/run.js" flows config get …`. It must be that
flag on `node` itself: `NODE_OPTIONS` refuses `--stack-size`.

**Two files, two shapes.** `flow.working.json` and `flow.backup.json` are the **envelope**
`config get` and `config update` return; `draft.json` is the **bare config** you edit, check,
preview and send. A new flow has no envelope until its first write: author straight into
`draft.json`.

**The text is in the catalog.** Every localizable field holds a `{_lid}` ref, and its per-locale
values live in `localization.content` — so a copy edit or a translation changes
`content[id].values[<localeId>]` and keeps every id, and an entry several fields share changes all
of them ([transforms.md](references/transforms.md) decision 1). Anything you write inline — a
`flowkit` fragment, a catalog template, a hand-written value — gets catalogued before phase 3:

```bash
python3 references/localization.py catalog draft.json
```

When `verify-config.py` reports a string as wrong in the source rather than missing, it names it
once per locale: fix that string in each locale it names, and when more than one variant could be
right, ask the user which.

A fetched config below `schemaVersion` 13 is converted first, the same way; below 12 the user opens
it in the Flow Builder, makes one real edit (an unchanged flow is not saved), saves, and you fetch
again. The rules:
[flow-schema.md → Localization: the catalog](references/flow-schema.md#localization-the-catalog).

**Patch what you just fetched.** A build script or a `draft.json` from an earlier run predates
whatever was done in the builder since, and `config update` replaces everything
([merge.md](references/merge.md)). If such a copy is lying around, diff it against live, report
the `ADDS`/`CHANGES` as the human's edits, and move it out of the way:

```bash
python3 references/diff-config.py <the-old-local-copy>.json flow.working.json
```

**New flow** — `flows create` once, seeded from a config the user already has; the steps and the id every retry writes to: [build.md → Creating the flow](references/build.md#creating-the-flow).

Then, before editing: **report what the source config contains** — screens and captions,
locales, products, the navigation graph. Before proposing anything; it grounds the user and
catches a wrong flow immediately.

**Confirm the transform.** In scope: add a locale, rewrite copy, add/remove/reorder screens,
branching and conditions, renaming screen ids, and reusing a piece of another flow — its
dependency resolution has a measured hard-422 class (`flow-schema.md` invariant 8), so it runs
through `references/snippet.py`, never by hand ([snippets.md](references/snippets.md)). A request
outside those is named as out of scope, not improvised.

If the request is *"save this for reuse"* or *"add the thing I saved"*, run
`references/snippet.py plan` before any `graft` — read [snippets.md](references/snippets.md) first.

If it is *"give the screens readable ids"* — usually so a customer's own analytics stops reading
`scr_oAPBHPa7` — run `references/rename-screens.py`, never a hand edit (`verify-config.py` refuses
a `_meta.screens` key left behind). Renaming breaks analytics continuity, so it goes in the phase-5
ask ([transforms.md](references/transforms.md) decision 9). **Element `el_XXXX` ids are not part of
this and must not be renamed to match:** it buys nothing, because the id a customer's analytics
sees is `props.customId`
([flow-schema.md trap 7b](references/flow-schema.md#7b-the-id-analytics-sees-is-customid-and-leaving-it-blank-is-silent)).

**Were you given a design, or are you choosing it?** Decide the mode, and the teardown that is the reference when you choose: [build.md → Were you given a design](references/build.md#were-you-given-a-design-and-whose-is-it).

**A screen that sells resolves its products before the design; a value only the app knows is a custom tag; every image or clip is resolved before you write its element.** Read [build.md → Products](references/build.md#products-catalog-first-store-ids-second-create-last), [Custom tags](references/build.md#something-only-the-app-knows-a-custom-tag) and [Assets](references/build.md#assets-upload-the-file-then-build-with-its-url) at that moment.

**Before you author a construct you have not seen in a real document, count it.** The schema says
what is *permitted*; a real export says what is *produced*; only the second predicts the device. One
`jq` over the config you fetched and over `references/component-catalog.json` settles it in seconds,
and a count of **zero** is a finding to say out loud
([flow-schema.md](references/flow-schema.md#before-authoring-a-shape-you-have-not-seen-produced-grep-for-it)
— why, and the defects that shipped from skipping it).

**Resolve the request into schema terms.** The user's noun is rarely the element `type` — there
is no `button` and no `toggle` element, and tabs are a five-element composite. Use the request
map in [flow-schema.md → Vocabulary](references/flow-schema.md), and source any shape the config
does not already contain via
[patterns.md → Where to source a pattern, in order](references/patterns.md).

**Editing one screen of many? Patch in place with a script — never slice the screen out.** An
isolated mid-flow screen **fails the publish gate** the moment it navigates to a screen that is no
longer there, and isolation buys no speed on either gate — measured, with nothing to stitch back
([transforms.md](references/transforms.md)). Reach the screen with `jq` or a short Python patch
instead of reading the whole file into context.

**Apply**, preserving every key you did not deliberately change — including unrecognized ones.
**Nested** unknown keys survive a round trip; unknown keys at the **top level of `config`** are
discarded, so never park anything there.

Write the result to a local file. Phases 3 and 4 both work on that file, with nothing saved yet —
**and they apply whether the deliverable is a flow write or the file itself.** "No CLI write
happened" exempts you from the approval gate, never from the phases.

**If the file IS the deliverable, `verify-config.py` warns on a top-level `status` or `id`** and
says what to do: act on it, never paste it through.

### 3. Check the shape, then clear the publish gate

Walk [Verify](#verify) first — it is local and free and it finds every defect at once, which the
commands below do not. Then **all four gates in one call**:

```bash
BASELINE=flow.backup.json references/gates.sh draft.json <APP_UUID> <FLOW_ID>
```

It runs the structural walk, the schema shape check, a read of every bound product and offer
against the app (`validate` passes ids the app does not have) and the publish gate over the *same
bytes*, prints one verdict, and exits non-zero only when something blocking was found. **One call,
not four** — the gates cost well under a second each while an extra round trip costs tens of
seconds, so the turns were the expensive part. The three underlying commands, if you need to run one
alone, are in [validate.md](references/validate.md).

**Pass `BASELINE=` whenever you fetched a config** — the pristine copy from step 2. A brand-new
flow has no config to fetch (`config get` answers with an error), so it runs without one and has nothing older to
report. The schema describes the newest
`schemaVersion` while most live flows are older, so an unbaselined run on a v9 or v10 flow reports
pre-existing mismatches, none of them yours. Details in
[flow-schema.md → the two different validators](references/flow-schema.md).

`validate` runs the **same transform service that gates publishing**, so it is the only pre-write
check here that speaks for the publish gate. It saves nothing, needs no confirmation and needs no
baseline — a v9 config validates clean. The flow must already exist, so on new work it runs after
`flows create`.

**`gates.sh` unwraps an envelope and prints a failed call as `API ERROR`, apart from the verdict**
(it says what to do); run alone, `validate` is read as [validate.md](references/validate.md) says.

> **Done here is a run that printed `valid: true` over the exact bytes you are about to write.**
> It reports one fatal per run, so fix, re-run, repeat — a shorter list is not progress.

**When `gates.sh` prints `ALREADY IN` under the verdict, the fatal was in the live flow before your
edit.** Make your edit anyway:

1. Copy the draft to a scratch file, fix the blocker there, and run `gates.sh` over that copy.
   That is the only way to see whether your own edit is clean, because the old fatal hides
   anything of yours behind it.
2. Once the copy prints `valid: true`, save your edit as the user asked, without the fix, and ask
   with the fix named:

   > Your headline change is ready. The flow already had a problem before I touched it: one text
   > uses a type style the theme does not define, so it cannot be published as it is. Should I
   > point it at the theme's body style in the same save?

   *(The shape, not the words: what is ready, what was already broken, why it blocks publishing,
   the one fix.)*
3. On a yes, save the fixed copy.

**And while the products are unsettled it reports nothing but the products** — binding is an
early stage, so an unbound card or an undeclared product hides every later defect behind it.
That is what makes the local walk above the fast path rather than the thorough one: it names
those defects anyway, at no round trip.
[validate.md](references/validate.md#unsettled-products-hide-everything-else).

**Neither check is a proof, and they do not overlap.** `validate` catches the stranded references
the schema cannot see — an undeclared product, a `groupId` or a `navigate` pointing at something
that is gone. It also passes `fill: "banana"`, `schemaVersion: 999`, an element with no `states`,
and every property the service will silently drop on the device. The schema check answers the
opposite question and knows nothing about publishability. Coverage both ways, and how to read each
message family: [validate.md](references/validate.md).

### 4. Preview, and iterate until it looks right

**Render the screens you changed, in ONE call, and get back one strip to look at:**

```bash
references/shoot.sh draft.json scr_a scr_b scr_c     # preview + screenshot + montage
```

It previews locally (no `--app`, no auth, no save — file-only tasks included), screenshots each
screen with a watchdog, joins them left-to-right and prints the one path to open. **Open that
image and look at it**, against what the user asked for and — if they gave one — against the
reference image file, re-opened, not remembered.

**Run a batch of three or more screens in the background and wait for it.** A screen takes a few
seconds and can take minutes on a slow host. Each prints a line when it lands, and at
`TIME_LIMIT` seconds (default 300) the run stops and says what to re-run. A screen that scrolls comes back as every scroll position,
left to right, and `LOCALE=<code>` renders another language
([preview.md](references/preview.md#what-a-render-costs-and-which-knobs-do-nothing)).

**A screen that ends in a button bar is rendered twice more, on a short and a tall phone:**

```bash
DEVICE=iphone-se-3 references/shoot.sh draft.json scr_paywall      # 375x667
DEVICE=google-pixel-9 references/shoot.sh draft.json scr_paywall   # 412x924
```

On the tall one, look for an empty band: under the bar, above it, or between rows of a list
(`render-measure.py --column <x>` reports it as a gap). A band means nothing on the screen takes
a tall phone's extra height; on a screen with a hero it goes to the hero
([patterns.md](references/patterns.md#a-tall-phones-extra-height-goes-to-the-hero)). On the short
one, a photo hero should keep about 160pt; if it draws smaller, give it a fixed height and put
the bar in a [`footer`](references/patterns.md#a-bar-that-stays-at-the-bottom-use-footer), so the
small phone scrolls.

**Render only what you changed.** Each screenshot costs seconds, and minutes on a slow host, so the number of
renders *is* the cost of this phase, and re-shooting seven screens to check an edit to one is six
wasted launches. One strip is also one *look* instead of N, and a before/after or
default-vs-selected pair only reads as a *difference* when the halves are adjacent.

**Do not try to speed the screenshot itself up** — shrinking `--virtual-time-budget` does nothing
on a fast host, and parallel Chrome is slower than serial. **`shoot.sh` retries an empty or flat
shot itself and says what to do next**
([preview.md](references/preview.md#what-a-render-costs-and-which-knobs-do-nothing)). A dead render
is never a reason to report the work finished.
Measure rather than eyeball with `references/render-measure.py`. Always try the preview: never decide
from the config's size.

**Every image gets its properties checked here — reference build or not — because no other gate
looks at an image at all.** Read the drawn box off the screenshot and choose: `height: hug` takes
its height from the **asset's** aspect, so the layout moves if the file changes and any `value` on
the size is dead; `height: fixed` holds the box and the asset absorbs the mismatch — `cover` crops,
`fit` letterboxes and leaves a dead band. `objectFit` is `fit` or `cover`, no CSS set. Re-render
after each change ([media.md → Geometry](references/media.md#geometry-what-changes-when-the-asset-lands)).

**A screen with price variables is judged and handed over at real price length.** Each unbound
price renders as its full `{{…prod_price}}` token, which wraps and pushes text under a pinned
button. Render a throwaway copy with a plausible price in place of each token, fix the layout
against that, and hand that render over, saying the prices in it are samples; the config keeps
the variables ([preview.md](references/preview.md#what-a-render-cannot-show-you)).

**A reference image was given?** Run the fidelity pass before anything is written: [preview.md → The fidelity pass](references/preview.md#the-fidelity-pass-when-a-reference-image-was-given).

**Read [preview.md → What a render cannot show you](references/preview.md#what-a-render-cannot-show-you)
before you report what a screenshot proves** — every blindness on it measured, and two of them run
the *wrong* way: the render draws things a device will not. Two you act on here: it draws no notch
and no home indicator, so author `safeArea: true` and hand short-device clipping over as a device
check; and even then it measures an `absolute` element's `top` from the screen's top edge, not
from below the status bar ([patterns.md](references/patterns.md#under-safearea-true-check-where-an-absolute-element-lands)).

**Never stand a lookalike in for a real element** — not for one the preview cannot draw, not for one that looks hard to build: [preview.md → Never fake an element](references/preview.md#never-fake-an-element-to-make-the-screenshot-look-complete).

**Built a screen that advances itself?** Ship the timer-digits diagnostic with the first ask: [preview.md → A screen that advances itself](references/preview.md#a-screen-that-advances-itself-ship-the-diagnostic).

**Confirm you screenshotted the flow at all.** A bad `--device`, a broken fragment and a wrong host
all render as *pages* that pass a "did anything draw" check. `shoot.sh` uses the page's file
input ([`preview-with-playwright.mjs`](references/preview-with-playwright.mjs)) whenever it can; if
it fell back to the URL route and the render is blank, slow or wrong, run the install command it
prints — do not shrink the config. If you cannot render at all, say
so and ask the user to look; never report the work finished on a clean validate.

**Asked for an App Store review screenshot of a flow screen:** [preview.md → When to take an App Store review screenshot](references/preview.md#when-to-take-an-app-store-review-screenshot).

**A missing element may not be your bug, and a clean preview is not the builder opening the flow.**
Both, with the four surfaces and what each one proves:
[preview.md](references/preview.md).

**If you chose the design, grade what you built with the teardown before you hand it over**, every screen of a sequence at once: [preview.md → Grading what you designed](references/preview.md#grading-what-you-designed-the-teardown-pass).

**Show how the screens connect when the strip cannot.** A strip is in `screens[]` order, so it
hides every branch, skip and loop. Draw the map and open it in the user's browser:

```bash
python3 references/canvas.py draft.json --open     # canvas.html beside the config, renders as thumbnails
```

When to open it and what to check on it: [preview.md → The flow map](references/preview.md#the-flow-map-when-to-open-it).

**Iterate here.** Anything off, go back and fix it, then re-run phases 3 and 4. Nothing has
been saved yet, so an iteration costs a screenshot rather than a write.

### 5. Get approval, then deliver — a write or a file

**Whether you need a yes before writing is decided by one observable fact: does the target flow
already have a config?**

**It does not** — a flow you just created with `flows create`, whose `config get` 404s. Write it.
There is nothing to lose and nothing to overwrite, and stopping to ask would be friction over an
empty document. Report what you wrote afterwards.

**It does** — anything you fetched in phase 2. **Stop and get an explicit yes before the write.**
`config update` replaces the entire config: no partial write, no undo, no version history here, so
the document you are replacing exists in exactly one other place — the phase-2 backup. Put all of
this in front of the user in one message and wait:

**First, compute what the write destroys — never describe it from memory.** Run this on the bytes
you are about to write, after the last edit:

```bash
python3 references/diff-config.py flow.backup.json draft.json      # REMOVES = what you destroy
```

The **backup** is the baseline, not your working file: it is the one copy nothing in the run has
touched, so it is the only honest answer to "what was there before me". (An edit that landed after
you fetched is the lock's job, not this one's.)

**Every `REMOVES` line goes in the ask below**; `diff-config.py` says what to do with one you cannot
trace ([merge.md](references/merge.md)).

**Then weigh it: the user's phones download every byte of it.** On the same bytes:

```bash
python3 references/weigh-config.py draft.json      # exit 1 = something heavy to tell them
```

Exit 1 fills the weight slot of the ask below; exit 0 drops it. What it weighs, what the slot says and each fix on their yes: [media.md → Weighing a config](references/media.md#weighing-a-config-before-a-write-or-a-publish).

**Then show them the change — an approval on a description is not an approval on the screen.**
Split it in two, because the two halves need different things from the reader.

**Screens that changed — one row each, so "there are four of these" is visible at a glance.**
Render every touched screen from the draft, and its `before` from the backup (`preview` takes the
backup envelope as-is, no `jq`). A new screen has no before; say so rather than dropping the row.

> | Screen | What changed | Look at |
> | :-- | :-- | :-- |
> | Paywall *(new)* | outcome rows, two plans, trial badge | [Paywall, after](<path to the render>) — open in your browser |
> | Daily goal | nothing visual | [Daily goal, after](<path to the render>) |

Name screens as the builder shows them and link each render with the screen name as its text — the
file name is yours, not theirs.

**Changes with nothing to see — list them separately and say why.** A reader who has just looked at
four screenshots will otherwise assume the pictures were the whole change:

> - Daily goal: the Continue button now opens the paywall instead of closing the flow.
> - The two new plan cards are registered with their products, so the flow can publish.
> - 38 texts translated into German, checked for overflow in a German render. The 4 images stay the same in every language.

**Open exactly one of them live, and mark which row it is.** You are on their machine, so open it
rather than handing over a command to paste:

```bash
URL="$($ADAPTY flows config preview draft.json --screen <id>)"
open "$URL"          # macOS; xdg-open on Linux, start on Windows
```

The explicit opener is needed because your shell captures stdout, so the CLI prints the URL instead
of launching a browser as it would on a terminal. `preview` is fully local — no auth, no app id, no
write. **Print the command instead only when there is no display** (remote or headless) and say
that is why.

One tab, whatever the size of the change: the page renders a single screen and **does not walk the
flow**, so N tabs is N times the noise and still not the flow. Open the screen whose *state* matters
most — a picker, a toggle, a selected plan — because state is the one thing a static PNG cannot
show. **Identical screenshots do not mean an identical config**
([preview.md](references/preview.md)); that is what the second list is for.

> About to save over **<flow name>**, currently <status, as the dashboard shows it: draft, published, has unpublished changes>.
>
> <the two lists above>
>
> Removes: <each `REMOVES` line in plain words, traced to the request that asked for it — or "nothing">.
> I kept a copy of the current version, so I can put it back if you need it.
>
> `<only if the weigh exited 1:>` Load time: <the three sentences the weigh printed under "Say
> this", as they are: what is heavy, what it does to the person opening the flow, what I can do>.
>
> `<the last line, one question:>` Save it? `<or, with the weight slot, in its place:>` Fix
> the weight first, or save as is?

An example of the weight slot's shape, not words to copy:

> Load time: the image on Welcome is a 2.3 MB JPEG, 4× wider than any phone screen shows, and it
> also has a separate file in 4 languages. On a slow mobile connection people see a blurred
> placeholder there for about 13 s, while they decide whether to go on. I can convert it to WebP
> (usually 70-90% smaller, it looks the same), or use one image for every language or split the
> flow by language: tell me which, or keep it as it is.
>
> Fix the weight first, or save as is?

Do not paraphrase this into "shall I save?" — the flow name, the status, what it removes and the
way back are the content, and an approval given without them is not informed. Wait for a yes; a
screenshot the user liked is not one.

**If the flow is `published`, disclose what the save changes — then edit in place on their yes.**
A `published` flow you save becomes `dirty`: the status is visible to their whole team and cannot
be reverted from the CLI, while end users keep seeing the published version until the next
publish. Put that sentence in the approval ask and proceed — editing a live flow is the normal
case, and the preview pair, the backup and the lock exist precisely so it is safe. Suggest a
fresh `flows create` only when the work is exploratory — a redesign the user wants next to the
original — never as the default answer to an edit.

**Restoring from the backup — verified end to end.** Lock it on the version your last write left
in `flow.working.json`, so a restore cannot erase an edit someone made after yours:

```bash
jq '.config' flow.backup.json > restore.json
$ADAPTY flows config update $FLOW --app $APP --config-file restore.json \
  --expected-updated-at "$(jq -r .updated_at flow.working.json)" \
  --remote-configs "$(jq -c '.remote_configs // []' flow.backup.json)" --json > write.json \
  && mv write.json flow.working.json
```

Verified byte-identical on a real flow — so the recovery is real, but only if phase 2 actually
took the backup, which is why that step is not optional.

Only then:

```bash
# the lock is the version draft.json was patched from; the mv stores the next one on success
$ADAPTY flows config update $FLOW --app $APP --config-file draft.json \
  --expected-updated-at "$(jq -r .updated_at flow.working.json)" \
  --remote-configs "$(jq -c '.remote_configs // []' flow.working.json)" --json > write.json \
  && mv write.json flow.working.json
```

**Send the remote configs back on every write, restore included:** a write without
`--remote-configs` clears the stored ones. Each entry is `{locale, data}`, and `data` is a JSON
**string**, not an object; an object is refused with `400 Input should be a valid
string`, so encode a new one with jq's `tojson`.

Validate and preview both run on a local file, which is why the write comes last: one write when
the thing is right, instead of one per iteration. If you have already written and then found a
problem, that is fine: the `mv` already put your write's `updated_at` in `flow.working.json`,
so the next write locks on it with no extra read.

**That `--json` redirect *is* the read-back — no extra call.** The write returns the **same
envelope as `get`**, so your working file is already in sync for the next round, and you can diff
it against what you sent. A faithful round trip is the norm, so any difference is a real finding —
a top-level key that vanished, a `status` you should not have emitted. The one expected
difference: the server echoes the legacy top-level `locales` and `defaultLocale` back, which
`localization.py catalog` drops from what you send. Those two keys alone are not a finding.

A write that changes nothing does not bump `updated_at` (measured once), so re-running the same
content is not a fresh lock token. **On a 409** (*"already updated by <name>. Reload before
saving…"*, exit 1) someone edited the flow since you fetched it and nothing was written: re-`get`
into `flow.working.json`, re-apply your change **to their config**, tell the user someone else
saved in between, and write again. The builder can auto-save a cleanup of `states` that bumps
the version and that `diff-config.py` does not show: diff the raw JSON when the summary is empty.
Never force
past it and never re-send your local copy — that is the content that would erase their work. If
their version differs in ways you did not author, ask rather than restore.

**On `Flow is deleted`** someone deleted the flow in the dashboard after you read it: nothing was
written, and no write to that id can succeed. Say so; your draft is intact, so on a yes
`flows create` a new flow and write the draft there, with no `--expected-updated-at`.

**If you rebuilt the config from a script rather than patching the fetched one, you have the wrong
document** — a rebuild replaces the live flow, taking `_meta.screens` and the `screens[].products`
registry it derives from ([products.md](references/products.md)) and every manual edit with it. Patch the fetched config;
[merge.md](references/merge.md) names the only two cases where a rebuild is right. `verify-config.py`
refuses a patched-in screen whose ids repeat the live ones (it names the fix).

#### The file deliverable

When the user asked for a file rather than a write: no approval gate, and what the closing report and the import must carry: [transforms.md → The file deliverable](references/transforms.md#the-file-deliverable).

**Never end with the work in a local file.** `config update` is the only save this surface has, and
saving is where you stop by default. Publishing is a separate, explicitly confirmed step the user
asks for — never something you fold into a write.

**When your host's permission layer blocks the write** (a refusal from your tool runner, not an
answer from the CLI), keep the validated `draft.json` and `flow.working.json` where the user can
see them, give the exact `config update` command above with absolute paths for them to run, and
stop. Do not retry the write another way.

**When a placement shows this flow, read who it reaches before the callout:** [publish.md → Before a publish](references/publish.md#before-a-publish-read-who-the-flow-reaches).

**Then end with this callout, every time.** A save is not a release, and it takes their word to
finish it. Fill the slots and keep all three steps plus the closing line — that line is the
point. **If the user asked you to publish and you did,** the heading becomes "Published — live
on `<placement>`" (or "Published — not on a placement yet"), step 3 and the closing line go, and
the rest stays.

**Asked to publish?** Read [publish.md](references/publish.md) first: the Terms and Privacy URLs, the weigh, the call and its poll.

> **Saved as a draft — your users can't see this yet.**
>
> 1. Review it in the builder — refresh the page if it is already open:
>
>    https://app.adapty.io/flows/<FLOW_ID>/builder
> 2. Preview it on a real device and check <the specific things this build could not verify>.
>    <the QR image line if they asked for one; otherwise this line:>
>    Want a QR code to scan with the Adapty mobile app? Just say so and I'll make one.
> 3. Publish: say the word and I'll do it, or use Publish at the top right of the editor. After
>    that I can attach it to a placement, which is what makes your app show it.
>    `<only if a placement shows this flow:>` About `<n>` people a week start it on
>    `<placement>`, and a publish changes it for all of them. `<only for a change buyers see:>`
>    To measure the change first, I can set up an A/B test of a copy against the live version.
>    `<only if a product card has no product chosen:>` Publishing is blocked until you choose
>    the products for `<the cards, by label>` — tell me which, or pick them in the builder.
>
> `<one line, only if the phase-2 missing-assets list still has open items:>`
> `<n>` assets are still placeholders — see the list above.
>
> `<only if the flow has custom tags:>`
> It shows `<n>` values only your app knows — `<name>`, `<name>` — and everyone sees the fallback
> text until your app passes them. Want me to update your app code to pass them now?
>
> `<the closing line, by the flow's status:>`
> `dirty` — Until you publish, everyone continues to see the previous version.
> `draft` — Nothing is live yet: nobody sees this flow until it is published and attached to a
> placement.

**Offer the QR in slot 2, never the preview link, and make it only on a yes, after the write:** [preview.md → Offering the device-preview QR](references/preview.md#offering-the-device-preview-qr).

**Fill that slot with the actual list, never with "check it works".** You know which of your
choices the render could not reach — a branch that fires on tap, a toggle, a locale you did not render, a
progress bar that advances, a screen that advances itself, glyph metrics that differ on iOS. A
generic instruction gets skipped; three named things get tapped, and every defect this skill has
shipped to a user came through a gap this slot exists to hand over
([preview.md](references/preview.md)).

**A custom tag is not done until the app passes it:** on a yes to the callout's offer, write that code as [custom-tags-code.md](references/custom-tags-code.md#writing-the-code-that-passes-a-custom-tag) says.

### 6. Attach it to a placement, then hand the ID over

**When a flow reaches `published`, the user says it has, or the request starts here (phase 1):** offer to point a placement at it, never unasked. The steps, the placement ask (the fourth fixed block) and the handoff: [placements.md → Attaching a flow](references/placements.md#attaching-a-flow-to-a-placement-the-procedure).

## Safety

**Pass `--expected-updated-at` on every write except the first.** A stale value fails instead of
clobbering, so this is a real guarantee rather than a warning. Take it from `flow.working.json`,
the version your draft was patched from — never from a `config get` run just before the write,
which hands you the other person's token, and never from `flows get`, whose `updated_at` is a
different field. Omitting it is last-write-wins and will silently overwrite an edit someone else
made in between.

**The lock is not a merge.** It guards the *timing* of a write and says nothing about its
*content*: a document that was never based on the live config — regenerated, or patched from a
stale local file — passes the lock and overwrites the flow anyway. So patch what you fetched, and
diff before you write ([merge.md](references/merge.md)).

**Never write to a flow the user did not name.** `flows list` is for finding the right one and
confirming it back to them, not for picking one yourself.

**`config update` replaces the whole config.** There is no partial write, no undo and no version
history. Prefer a fresh `flows create` for new work, and create it once: a retry writes to the
flow you already created.

**Overwriting an existing config needs an explicit yes.** Phase 5 owns the form. The gate is keyed
to whether the flow already has a config, not to how confident you feel about the edit — a clean
validate, a good screenshot and a user who liked the design are all upstream of the question and
none of them is an approval.

**Deleting a flow is a dashboard action.** There is no `flows delete`, so never claim to have
removed one — including a throwaway you created yourself. Name the flow and tell the user where
to delete it.

`validate` and `preview` change nothing and cost nothing. Use them freely.

## Verify

Walked in phase 3 **before** the two commands, because this finds every row at once locally where
`validate` reports one per round trip.

**`references/verify-config.py` ships and phase 3 runs it, and it mechanises all but two of the
referential rows.** So do not re-derive them by eye: run it, and read its output as the checklist.
The full statements — what each invariant is, what breaks it, what a violation does — are
[flow-schema.md → Invariants](references/flow-schema.md#invariants), which owns them.

**What the tool cannot answer, and you must:**

| Check | Why no tool catches it |
| :--- | :--- |
| `fill` keeps the form the input used — object or array, **never converted**, and **one layer** | the form is only wrong relative to the input you fetched |
| an image URL is one **`flows media upload` printed in this session** | a plausible `public-media.adapty.io` path is indistinguishable from a real one |
| `_meta.icons[].raw` is **real** SVG — resolved through `icons.py`, not written by you | presence is checkable, authenticity is not |
| **every price variable's field agrees with its product's period** | needs the catalog, not the config |

That last one is a **hard stop, not a disclosure**: if the catalog has no product with the period
the design needs, stop before the write.

**Publish blockers** ([Common issues](https://adapty.io/docs/flow-common-issues.md)): a screen with
zero elements, a product element with no product, an incomplete interaction. `validate` reports one
per run. **Never treat a publish blocker as protection for a defect you left in** — the user clears
blockers, and clearing one often activates whatever it was masking
([products.md](references/products.md)).

**Warnings — report, never "fix":** an unreferenced component; a declared but unreferenced entry in
`variables[]` or `theme`; an inert `conditional` whose branches all resolve to `nothing`. Real
configs contain all of these.

**One warning splits by authorship: a catalog value under an undeclared locale id.**
`verify-config.py` says which way each goes.
