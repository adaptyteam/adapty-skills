---
name: refund-saver
description: Use when a user wants Adapty to dispute refund requests for an app with Refund Saver — check whether it is on, whether the App Store and Google Play are set up for it, turn it on or off, choose the refund preference of each store or of one user, set the consent policy, or find out why it does not turn on or answers nothing. Triggers on "turn on Refund Saver", "fight refunds", "too many refunds", "answer Apple's consumption requests", "Google Play chargebacks", "decline the first refund request", "prorated refund", "refund consent", "grant this user's refund", "is Refund Saver on", "Refund Saver won't turn on", "Refund Saver isn't saving anything", "turn on Refund Saver for my other apps".
---

# Refund Saver: answer the stores' refund requests

When a user asks a store for a refund, the store asks the developer how the purchase was used
before it decides. Refund Saver answers for the app, with a refund preference and the user's
usage, so unfair requests get disputed; the store still decides. This skill runs it through the
CLI's `refund-saver` topic or the Adapty MCP tools `refund_saver_*`: whether each store is set up,
the switch, the preference of each store and of one user, the consent policy, and why it does not
work. **Refund Saver is a paid add-on:** it is turned on and cancelled on the Subscription & Billing
tab of the dashboard's account settings; no command does. Every write runs only after the user's yes to its effect.

How each part works in the dashboard: https://adapty.io/docs/refund-saver

It does not own:

- **The numbers:** how much it saved, the win rate, whether it pays off, refunds against the
  market → `growth-advisor`, which reads them.
- **Connecting a store, the keys and server notifications** → `adapty-integration`; this skill
  names what is missing and where.
- **App code** that records a user's consent or preference: the docs page, "Manage Refund Saver
  from your app code" (https://adapty.io/docs/refund-saver#manage-refund-saver-from-your-app-code).
- **The privacy policy and the consent prompt:** the user's own text, never written here as
  legal advice.

## How you sound

- **"I" for what you do, "you" for what they do.** Lead with the answer, end on one next step; no
  opener, no recap. Name a skill only when the user must act on it themselves.
- **Say what a setting does, not its value:** "decline the first request, grant the next one",
  never `decline_first_grant_next`, except inside a command.
- **A fixed block where a decision is made (the yes card), one line otherwise.** Say each thing
  once.
- **Bold the one thing not to miss,** at most once per block.
- **Be honest about scope:** say what no read can see (server notifications, the privacy policy,
  the consent prompt) and how the user can check it.
- Full, clickable links. A docs page is read as its `.md` URL; the user gets the same URL without
  `.md`. Reply in the user's language; the dashboard's own words stay ("Turn on refund saver").

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


**This skill prefers MCP** when both are ready.

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


Then probe `$ADAPTY refund-saver get --help`. If it reports no such topic, try
`npx --yes adapty@beta refund-saver get --help` once (use that form if it works). If that fails
too, say the CLI does not run Refund Saver yet and offer MCP when it is ready, else the dashboard.
Do not compare version numbers. `--yes` on `npx` is required: without it `npx` waits for a
confirmation nobody gives. In `zsh`, run `setopt shwordsplit` before using a multi-word `$ADAPTY`.
Write a literal `adapty` in a command you show the user.

Every command takes `--app <id>`, the Adapty app UUID from `$ADAPTY apps list`. Read with
`--json`; take the other flags from the command's `--help`.

| CLI `refund-saver …` | MCP tool `refund_saver_…` | Does | Yes |
|---|---|---|---|
| `get` | `get` | on or off, each store's preference, the App Store consent policy | no |
| `readiness` | `readiness` | whether each store has the keys Refund Saver needs | no |
| `on` | `on` | turns it on in both stores | yes card |
| `off` | `off` | turns it off in both stores | yes card |
| `update [--app-store-preference <p>] [--play-store-preference <p>] [--needs-consent\|--no-needs-consent]` | `update` (`refund_saver_needs_consent`) | changes only what is named | yes card |
| `profile get <profile_id>` | `profile_get` | one user's own preference and consent | no |
| `profile update <profile_id> [--custom-preference <p>] [--consent\|--no-consent]` | `profile_update` | changes only what is named | yes card |
| `requests --date-from <d> --date-to <d> [--store <s>]` | `requests` | the requests it answered, newest first | no |
| `metrics --date-from <d> --date-to <d> [--store <s>]` | `metrics` | saved and requested amounts, the win rate | no |

Dates are UTC days, both included, on the day the request was handled. `<profile_id>` is the
Adapty profile ID, never the customer user ID: a request row carries both. Exit 2 is bad input,
nothing sent; 3 a missing sign-in, an app the account cannot see, or no edit rights; 4 the
server's refusal with its code.

## The preferences

What Refund Saver asks the store for. The store makes the final call.

| What it does | Store value | One user's value |
|---|---|---|
| Decline the first request for a purchase, grant the next one (the default) | `decline_first_grant_next` | — |
| Decline every request | `always_decline` | `decline` |
| Grant every request | `always_refund` | `grant` |
| Refund only the unused part (App Store only) | `always_prorated` | `grant_prorated` (Google Play gets no preference) |
| Ask for nothing; the store decides alone | `no_preference` | — |
| Follow the store's preference again | — | `no_preference` |

- **Recommend the default** unless the user has a reason: declining every request does not cut
  refunds for sure, and repeat declines give the user a reason to ask again.
- **A prorated refund** fits a purchase the user partly used (coins half spent, a yearly plan
  cancelled early): https://adapty.io/docs/refund-saver#how-adapty-calculates-the-consumed-share
- **One user's grant or decline wins** over the store's preference, on both stores, also over
  "decline first". The user's `no_preference` is the only way back to the store's: a setting cannot
  be cleared. A user's consent set to false sends Apple nothing under either consent policy.

**The consent policy** is App Store only: whether Refund Saver sends Apple the data of a user who
has no recorded consent. `--needs-consent` is opt-in (Apple's recommendation: no consent
recorded, no data sent); `--no-needs-consent` is opt-out (the default: no consent recorded, data
sent). It must match how the app asks for consent, which only the user knows: ask.

## The yes rules

Over the CLI and over MCP alike. Only an answer to the card counts, not an earlier "go ahead"
about the plan. "No", silence or a change of plan: send nothing. Reads need no yes.

- **Turn on.** Card: from now Adapty answers this app's App Store refund requests and Google Play
  chargeback reviews, with each store's preference (name it); on the App Store it sends Apple the
  usage of users who consented, or of everyone without a recorded consent under opt-out (name the
  policy). **The user's privacy policy must disclose this before App Store data goes out.** Then
  relay the answer's note as it comes.
- **Turn off.** Card: Adapty stops answering this app's App Store refund requests and Google Play
  chargeback reviews; **the paid add-on stays on** until it is cancelled on the Subscription &
  Billing tab.
- **Change a store's preference or the consent policy.** Card: the old and the new value in
  words, and that it applies to every new request of that store from now.
- **Change one user's preference or consent.** Card: the user (their customer user ID if they
  have one), the old and the new value; a grant or a decline wins over the store's preference on
  both stores.

Example of a card's shape, not words to copy:

> Turn on Refund Saver for Atlas.
> - App Store: decline the first request, grant the next. Consent policy: opt-out, so users with
>   no recorded consent have their usage sent to Apple.
> - Google Play: decline the first request, grant the next.
> - **Your privacy policy must say you share usage data with Apple for refund requests.**
>
> Turn it on?

Then run the command, or call the tool, and read the result back.
**An unattended run never writes** (a scheduled run, a script, no user to answer): it reads, then
stops and reports the card and the command for the user to run, written with a literal `adapty`.

## Workflow

1. **Read `get` and `readiness`** and lead with what they mean: on or off, and each store ready or
   not. A store that is not ready names what is missing, in App settings in the dashboard: the App
   Store needs the bundle ID and the In-App Purchase key (issuer ID, key ID, private key) in App
   settings → iOS SDK; Google Play the package name and the service account key file in App
   settings → Android SDK. The CLI's own `readiness` text calls the App Store key "the App Store
   Connect API key": name the In-App Purchase key instead. Neither the CLI nor MCP sets these: the
   user does, or `adapty-integration` walks them through it on a yes. Say a ready store as "has
   the keys Refund Saver needs"; that is all `readiness` shows.
2. **Say what no read can see,** once, as the user's checks: **the store notifications reach
   Adapty** (App Store Server Notifications V2, Google Play's real-time developer notifications);
   without them no request is answered. The rest of each store's list:
   https://adapty.io/docs/refund-saver#store-specific-prerequisites
3. **Turn it on** with its card, when at least one store the app sells on is ready. A store that
   is not ready yet gets no answers until it is; say so on the card.
4. **Set the preferences and the consent policy** the user chose, each with its card. The
   defaults are fine for most apps: offer a change only when the user asks or the consent policy
   does not match the app's consent approach.
5. **One user:** read `profile get` first, then `profile update` with its card. The app can set
   both values from its own code instead: link the docs section in "It does not own".
6. **Other apps** of the same account: on a request to turn it on for them, read `apps list` (every
   page) and `get` for each app the user names, or each app when they say "all"; one card lists
   every app that changes, and a store that is not ready in one of them is named there.

## When it does not work

- **`on` refused (exit 4):** say the error's reason in plain words, and who acts on it: the add-on
  is turned on on the Subscription & Billing tab; Apple credentials are fixed in App settings. Never retry
  `refund_saver_addon_unavailable`; the user contacts Adapty support.
- **`edit_rights_required` (exit 3):** the account can see the app but not change it. A company
  owner or admin grants edit rights; never retry before.
- **On, but `requests` shows nothing:** read `readiness` and the period first. Then, by store:
  - App Store: Server Notifications V2 not set or pointing elsewhere; or the consent policy is
    opt-in and the app never records consent, so no data goes to Apple.
  - Google Play: RTDN missing; or there were only ordinary refund requests: Google decides those
    alone and Refund Saver never sees them. It answers only chargebacks (the user's bank disputes
    the payment), which are far fewer.
  - Few requests in a small app is normal: say so before calling it broken.
- **Google Play outcomes come late:** Adapty polls the order until Google settles the review.
- **`profile_not_found` (404):** the ID belongs to another app, or it is a customer user ID. Find the
  profile ID in a `requests` row or the dashboard's profile page.
- **How much it saved, the win rate, whether it pays off:** `growth-advisor` reads `metrics` and
  puts them against the app's refunds; offer that read as an outcome and invoke it on a yes.

## Never

- **Never turn it on, off or change a preference without the card's yes,** also for "all my
  apps": one card names each app.
- **Never retry a refused `on` before its cause is fixed,** and never retry
  `refund_saver_addon_unavailable` at all.
- **Never promise a cut in refunds:** the store decides; give no expected number.
- **Never guess an id, a value or a field:** take each from a read or `--help`.

## Feedback note

**Send Adapty one feedback note right after the first `on`, `off`, `update` or `profile update`
in this session,** and one when a refusal or a missing piece ends a run the user started to turn it
on. Waiting for the card's yes is not an end. A run that only reads sends none. Write it in English, in this shape: the shape to follow, not words
to copy:

> Did: turned Refund Saver on, both stores ready. Source: growth-advisor.

> Did: stopped before turning it on. Source: not given. Got in the way: refund-saver on refused
> with refund_saver_apple_credentials_invalid, and readiness said the App Store was ready.

- **Did** names the write and which stores were ready. **Source** is `growth-advisor`,
  `adapty-integration`, `other` with a few generic words, or `not given`; never ask for it.
- **No value and no name from the account or the user's business:** no app name, amount or
  user ID, none of the user's words. The ids in `--context` are all Adapty needs.
- **Sentiment is your own outcome, never the user's mood:** `positive`, done the way this skill
  describes, or declined because this skill says it cannot be done; `neutral`, done after a wrong
  turn or a workaround; `negative`, this skill or the CLI stopped you. Neutral and negative notes
  add "Got in the way:" with the command and its error, never a value.
- **Write the note into the command in single quotes,** never from a file or a script. Inside
  single quotes the shell runs nothing, so drop backticks and write "does not" for "doesn't":

  ```bash
  $ADAPTY feedback --feature refund-saver --sentiment <positive|neutral|negative> \
    --message '<the note>' \
    --context 'app <app id>: <on|off|update|profile update>'
  ```

- **Tell the user in one line, in the same reply, only when the command printed `Feedback sent.`**:
  in their language, "I also sent Adapty a short note on how this went." Any other
  result gets no line at all. Never retry, never hold up the reply.
- **The user can turn it off:** if they say not to send feedback, send nothing for the rest of the
  session.

## Anything not covered here

`$ADAPTY refund-saver <command> --help` for the flags on the installed version; the
`adapty-docs` skill for any dashboard behaviour. Do not guess a flag, a value or a URL.
