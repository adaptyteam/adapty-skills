---
name: retention-messaging
description: Use when a user wants to keep iOS subscribers on Apple's Cancel Subscription screen with Adapty Retention Messaging — check whether it is set up, give Apple Adapty's URL, run Apple's performance test, create or edit default and promo messages, activate or deactivate one, or read how each message performs. Triggers on "keep subscribers who cancel", "show a message on the cancel screen", "set up retention messaging", "is retention messaging on", "create a retention message", "add a German translation to my retention message", "deactivate this message", "how are my retention messages doing", "save rate", "saved revenue".
---

# Retention Messaging: Apple's cancel screen

Apple shows a subscriber a message on the iOS Cancel Subscription screen, right before they
confirm, and Adapty answers Apple with the message for that product and language. This skill
runs the feature through the CLI's `retention-messaging` topic or the Adapty MCP tools
`retention_messaging_*`: the setup status, Adapty's URL and Apple's performance test, then
messages (create, edit, activate, deactivate) and their numbers. **A message reaches real
subscribers once Apple approves it.** Every write runs only after the user's yes to its effect.

Sandbox and production are Apple's two environments: each has its own URL and its own messages,
and every write needs a yes in both. How each step works in the dashboard:
https://adapty.io/docs/retention-messaging

It does not own:

- **Apple's approval of the app** and the App Store keys: the user requests access from Apple
  and sets the keys in the dashboard (step 1 of the Workflow names the page).
- **A promotional offer or a plan** for a promo message: made in App Store Connect and added to
  Adapty first. Adding an existing store offer to a product → `growth-advisor`.
- **Whether to use it at all, and which products need it** → `growth-advisor`.
- **Deleting a message:** there is no delete. Deactivate it instead.

## How you sound

- **"I" for what you do, "you" for what they do.** Lead with the answer, end on one next step; no
  opener, no recap. Name a skill only when the user must act on it themselves.
- **Name messages and products, not ids:** "the Annual default message". Ids only inside a command.
- **A fixed block where a decision is made (the yes card), one line otherwise.** Say each thing
  once.
- **Bold the one thing not to miss,** at most once per block.
- **Be honest about scope:** say what you did not read (the other environment, a page of the
  list) and how the user can check.
- Full, clickable links. A docs page is read as its `.md` URL; the user gets the same URL without
  `.md`. Reply in the user's language; the dashboard's own words stay ("Sandbox mode").

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

**This skill prefers the CLI** when both are ready: only the CLI uploads a header image and
bullet icons. With MCP only, do everything else with the tools; an image or a new bullet point
needs the CLI (`adapty retention-messaging messages update <message_id> --app <app_id> --image
<file>`, or a change file with an icon): offer to set it up, or name the dashboard step.

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
`npx --yes adapty@latest` after the npx line, else to `adapty`. **Run it and the probe below also
when the user limits your reads or asks you to change nothing:** they read and update only the CLI
tool on this computer, never the user's Adapty data.

Then probe `$ADAPTY retention-messaging setup-status --help`. If it reports no such topic, try
`npx --yes adapty@beta retention-messaging setup-status --help` once (use that form if it works).
If that fails too, say the CLI does not support Retention Messaging yet and offer MCP when it is
ready, else the dashboard. Do not compare version numbers. `--yes` on `npx` is required: without
it `npx` waits for a confirmation nobody gives. In `zsh`, run `setopt shwordsplit` before using a
multi-word `$ADAPTY`. Write a literal `adapty` in a command you show the user.

Every command takes `--app <id>`, the Adapty app UUID from `$ADAPTY apps list`. Read with
`--json`; take the other flags from the command's `--help`. Over MCP, `--type` is `message_type`.

| CLI `retention-messaging …` | MCP tool `retention_messaging_…` | Does | Yes |
|---|---|---|---|
| `setup-status` | `setup_status` | keys, Apple access, each environment's URL, the test | no |
| `realtime-url get` | `realtime_url_get` | Adapty's URL for Apple, one for both environments | no |
| `realtime-url configure --mode <m>` | `realtime_url_configure` | gives Apple Adapty's URL for that environment | yes card |
| `performance-test start` | `performance_test_start` | Apple's test, sandbox only | no |
| `messages list --mode <m>` | `messages_list` | the messages of one environment with their numbers | no |
| `messages get <id>` | `messages_get` | one message whole | no |
| `messages create --mode <m> --file <json> [--image <png>]` | `messages_create` | a new message, sent to Apple's review | yes card, both environments |
| `messages update <id> [--file <json>] [flags]` | `messages_update` | changes only what is named | yes card |
| `messages set-status <id> --action activate\|deactivate` | `messages_set_status` | starts or stops a message | yes card, both environments |
| `products suggest --mode <m> --type <t>` | `products_suggest` | products a message can take | no |
| `promo-offers suggest <product_id>` | `promo_offers_suggest` | a product's promotional offers | no |
| `plan-switches suggest <product_id>` | `plan_switches_suggest` | plans a product can switch to | no |

The body and change files, the limits, the image rules, the numbers and the server's refusals:
[references/messages.md](references/messages.md). Without `--yes`, a write asks at a terminal and,
in a pipe or with `--json`, exits 6 and sends nothing; a "no" at the terminal is exit 1. Exit 2 is
a refusal before anything was sent, 3 a missing or refused sign-in or right, 4 the server's
refusal with its own text, 5 no answer from the server.

## The yes rules

Over the CLI and over MCP alike. Only an answer to the card counts, not an earlier "go ahead"
about the plan. "No", silence or a change of plan: send nothing.

- **Reads need no yes,** over the CLI and over MCP. A status read saves the result of Apple's
  test, and a list or message read saves Apple's review results, as the dashboard does when it
  opens the page; that can start showing a message the user and Apple already approved.
- **A read limit the user sets wins.** When the user names what you may read, read only that; any
  other read is a Next step that waits for their yes.
- **Give Apple the URL.** Card: Apple sends this environment's cancel-screen requests to Adapty;
  in sandbox Adapty also adds a hidden test message.
  When the status shows `configured_to_other_url` for that environment, a second card: **the URL
  now set in Apple is replaced**, and that server stops getting Apple's requests. Only after a yes
  to it pass `--replace-other-url` (MCP `replace_other_url: true`); `--yes` alone does not
  replace it, and the CLI exits 6 or the tool refuses with the same warning.
- **Create.** Card: the message goes to Apple's review now; once approved, subscribers who cancel
  the named products see it (in sandbox, sandbox testers). In both environments.
- **Edit.** Card: **every edit, a name alone too, sends the message to Apple's review again**; an
  inactive message starts showing again once Apple approves it; a change made in the dashboard
  between my read and my write can be lost.
- **Activate or deactivate.** Card: activation shows the message to subscribers after Apple's
  approval (approved languages do not wait again); deactivation stops future shows and does not
  undo past ones. In both environments.

Example of a card's shape, not words to copy:

> Create "Annual: stay" as a default message in production.
> - Products: Annual, Monthly. Languages: English, German. No image.
> - Apple reviews it now. **Once approved, subscribers who cancel these plans see it.**
>
> Create it?

Then run the command, with `--yes` on a command that takes it (`performance-test start` takes
none and asks nothing), or call the tool, and read the result back.
**An unattended run never writes** (a scheduled run, a script, no user to answer): it reads, then
stops and reports the card and the command for the user to run, written with a literal `adapty`
and **without** `--yes`.

## Workflow

1. **Read the setup status** first (`setup-status`) and lead with what it means:
   - `credentials` `missing`: the App Store setup is done in the dashboard first, in App settings
     → iOS SDK, and nothing in the CLI or MCP sets it. Name every field the feature uses, since
     the status shows only the first: the Bundle ID and the In-App Purchase key (connection and
     upload), the Apple App ID (Adapty's answer to Apple), the key under App Store promotional
     offers (signs a promo message's offer) and the App Store Connect API key (lists the plans for
     a plan switch): https://adapty.io/docs/retention-messaging-setup#before-you-begin
   - `registration_status` `not_registered`: Apple has not approved the app. Give the user
     Adapty's URL (`realtime-url get`) for Apple's request form, same page; Apple takes up to a
     month.
   - Sandbox URL `not_configured` or `configured_to_other_url`: offer to give Apple the sandbox
     URL, with its card.
   - Sandbox URL `configured_to_adapty`, test `not_started` or `failed`: offer to start Apple's
     test. The user first buys their longest plan with a sandbox account or TestFlight and keeps it
     active; the test takes up to an hour.
   - Test `running`: wait, then read the status again.
   - Test `passed`: offer to create the default message, also under a read limit or a no to
     writes; a read it needs first (`products suggest`, the list) is part of that offer, not a
     next step of its own. Production needs its own URL first
     (`configure --mode production`, with its card) when production does not show
     `configured_to_adapty`.
2. **Pick products:** `products suggest` for the environment and type (with the message id when
   editing). A product with `disabled_reason` cannot be taken: `used` (another message of this type
   has it), `no_default_message` (a promo needs a default message on that product first). No
   product at all: the app's products come first (`adapty-integration` creates them).
3. **Create the default message first, then promo ones.** A promo message links a promotional
   offer or a plan switch to each product (`promo-offers suggest`, `plan-switches suggest`); it has
   no image and no bullet points. An empty offer list: the promotional offer is made in App Store
   Connect and added to the product in Adapty
   (https://adapty.io/docs/app-store-offers#promotional-offers). An empty plan list: the other
   products of the subscription group are added to Adapty, each with an App Store status, and the
   App Store Connect API key is set
   (https://adapty.io/docs/troubleshoot-app-store-integration#products-dont-appear-or-show-no-app-store-status). Write the English texts and each language yourself, within the
   limits. Choose the title position now: it cannot change later.
4. **Read the numbers:** `messages list --mode production` (the dashboard's table: every number
   covers the message's whole life). Say what each number means once, from `references/messages.md`,
   "The numbers".
5. **Edit:** name only what changes; everything else stays. Deleting a language, a bullet point,
   a product or the image is only an explicit remove field. A new bullet point needs its text in
   every language of the message.
6. **Activate or deactivate** with its card. A product holds one default and one promo message;
   activation fails when another message took the product meanwhile.

## A lost answer

The CLI and the tools never repeat a create or an edit. **After a create whose answer was lost
(no answer, or a 5xx), never create again:** the result is unknown. Search the environment's list
by the name (`messages list --mode <m> --search <name>`, MCP `search`; the CLI error gives the
exact name as `Message name:`, `message_name` in `--json`; every page up to
`meta.pagination.pages`; say so when you read fewer), and read each candidate whole by id.
**Show each candidate (name, state, texts, products) and ask which one, if any, is the user's;
never pick one yourself.** A name match, no match and a `retention_product_claimed` refusal prove
nothing. A new create is the user's new decision with its own card. After a lost edit, read the
message by id and check it.

## Never

- **Never pass `--yes` on a command the user will run themselves.**
- **Never start Apple's test while one runs,** and never retry a refused write with changed values
  to get it through: say the server's reason in plain words (`references/messages.md`, "Refusals
  the server sends") and ask.
- **Never guess an id or a field:** take each from a read, a suggest command or `--help`.

## Feedback note

**Send Adapty one feedback note per message, right after its first `create` or `set-status` in
this session,** and one when the user asked for a message and the run stops before its create. A
run that only reads, edits or gives Apple the URL, with no message asked for, sends none. Write it in English, in this shape: the
shape to follow, not words to copy:

> Message: a default message with three bullet points, two languages. Source: growth-advisor. Did:
> created it in sandbox.

> Message: a promo message with a plan switch. Source: not given. Did: activated it in
> production. Got in the way: retention-messaging messages set-status failed with http_500
> (request id req_7f3a9c), and this skill does not say whether a retry is safe.

- **Message is its kind in a few generic words:** default or promo, offer or plan switch, how many
  bullet points and languages. **Source** is `growth-advisor`, `own data`, `other` with a few
  generic words, or `not given`; never ask for it. **Did** names the write and the environment.
- **No value and no name from the account or the user's business:** no message text, product,
  price, rate or revenue, none of the user's words. The ids in `--context` are all Adapty needs.
- **Sentiment is your own outcome, never the user's mood:** `positive`, done the way this skill
  describes, or declined because this skill says it cannot be done; `neutral`, done after a wrong
  turn or a workaround; `negative`, this skill or the CLI stopped you. Neutral and negative notes
  add "Got in the way:" with the command and its error, never a value.
- **Write the note into the command in single quotes,** never from a file or a script. Inside
  single quotes the shell runs nothing, so drop backticks and write "does not" for "doesn't":

  ```bash
  $ADAPTY feedback --feature retention-messaging --sentiment <positive|neutral|negative> \
    --message '<the note>' \
    --context 'app <app id>, message <message id>: <create|activate|deactivate> in <sandbox|production>'
  ```

- **Tell the user in one line, in the same reply, only when the command printed `Feedback sent.`**:
  in their language, "I also sent Adapty a short note on how this went." Any other
  result gets no line at all. Never retry, never hold up the reply.
- **The user can turn it off:** if they say not to send feedback, send nothing for the rest of the
  session.

## Anything not covered here

`$ADAPTY retention-messaging <command> --help` for the flags on the installed version; the
`adapty-docs` skill for any dashboard behaviour. Do not guess a flag, a field name or a URL.
