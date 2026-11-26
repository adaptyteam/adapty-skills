---
name: virtual-currencies
description: Use when a user wants to read or change an Adapty app's virtual currency (coins, gems, credits, tokens) — which currencies the app has and how many coins each product gives, a new currency, its name or description, the coins a product gives, a product that should stop giving coins — to read the coin ledger (one user's coin balance and coin transactions, the app's coin transactions, why a user has a number of coins or got none after a purchase), or to correct one user's balance by hand. Triggers on "how many gems does the annual plan give", "give the annual plan 50 gems", "create a gems currency", "this coin pack should stop giving coins", "why does this user have 40 coins", "I bought the coin pack but my balance did not change", "give this user 10 gems", "show this user's coin transactions", "set up the coins we had in RevenueCat". Not for coin totals or which coin pack sells better (`growth-advisor` reads those from analytics), not for coins of many users at once, and not for the currency of a price.
---

# Virtual currencies: coins for purchases

A virtual currency (coins, gems, credits) is credited to a user when they buy a product that the
currency maps: a one-time product gives coins for each purchase, a subscription for each paid
period. This skill runs the feature through the CLI's `virtual-currencies` topic or the Adapty MCP
tools `virtual_currencies_*`: the currencies with their product mappings, a new currency, its name
and description, the mappings, the coin ledger (the transactions of the app or of one user, and
a user's balances), and a manual credit or debit of one user's balance. **A mapping sets the coins
of every later purchase of its product, for real buyers, at once.** Every write runs only after the
user's yes to its card. How it works in the dashboard: https://adapty.io/docs/virtual-currencies

It does not own:

- **Balance changes the app makes, or for many users at once** (a spend in the app, free coins for
  every new user, a backfill): the app's server does them through the Server API. This skill
  corrects one user's balance in one currency for each call, never a list of users. Send the user
  to the page for what they asked:
  - the app spends coins: https://adapty.io/docs/virtual-currency-quickstart
  - free coins for every new user, or a backfill: https://adapty.io/docs/grant-initial-balance
- **Products:** a mapping takes an existing Adapty product. A new product comes first →
  `adapty-integration`.
- **Coin totals and trends, and how coin products sell** (coins bought, spent or expired by day,
  which pack sells better, packs against a coin subscription, which amounts to test) →
  `growth-advisor`, which reads them from analytics.
- **A paywall or flow for users by their balance** (fewer than 30 gems sees the top-up flow) →
  `audiences`, which builds the segment.
- **The app's screens that show or spend coins** (a balance on a paywall, a top-up flow) →
  `flow-generator`; the app code and the server's spend call come from the docs.
- **Deleting a currency or changing its code:** there is no way. An app has at most 20 currencies.
- **Balances carried over from another purchase system:** the migration of `adapty-integration`.

## How you sound

- **"I" for what you do, "you" for what they do.** Lead with the answer, end on one next step; no
  opener, no recap. Name a skill only when the user must act on it themselves.
- **Name currencies and products, not ids:** "Gems", "the Annual plan". Ids only inside a command and on
  a balance adjustment card.
- **A fixed block where a decision is made (the yes card), one line otherwise.** Say each thing
  once.
- **Bold the one thing not to miss,** at most once per block.
- **Be honest about scope:** say what you did not read (another page of the ledger, sandbox rows)
  and how the user can check.
- Full, clickable links. A docs page is read as its `.md` URL; the user gets the same URL without
  `.md`. Reply in the user's language; the dashboard's own words stay.

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
> 1. The Adapty CLI: I install it, and you sign in once in the browser.
> 2. The Adapty MCP server: you add it to your AI tool and sign in; nothing to install.

**This skill prefers MCP** when both are ready: each write takes the mappings as a list and the
`updated_at` of your read as a parameter, with no file. Everything this skill does works both ways.

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

Then probe `$ADAPTY virtual-currencies list --help`. If it reports no such topic, try
`npx --yes adapty@beta virtual-currencies list --help` once (use that form if it works). If that
fails too, say the CLI does not support virtual currencies yet and offer MCP when it is ready, else
the dashboard. Probe `$ADAPTY virtual-currencies profiles transactions create --help` the same
way before the first balance adjustment; when both forms report no such command, say the CLI does
not support a balance adjustment yet and offer the MCP tool when it is ready, else the dashboard:
https://adapty.io/docs/virtual-currency-balance. Do not compare version numbers. `--yes` on `npx`
is required: without it `npx` waits for a confirmation nobody gives. In `zsh`, run `setopt shwordsplit` before using a multi-word
`$ADAPTY`. Write a literal `adapty` in a command you show the user.

Every command takes `--app <id>`, the Adapty app UUID from `$ADAPTY apps list`. Read with
`--json`; take the other flags from the command's `--help`.

| CLI `virtual-currencies …` | MCP tool `virtual_currencies_…` | Does | Yes |
|---|---|---|---|
| `list` | `list` | the app's currencies, how many products each maps, how many more the app can create | no |
| `get <currency_id>` | `get` | one currency with every mapping and its `updated_at` | no |
| `create --code <c> --name <n> [--file <mappings.json>]` | `create` | a new currency, for good | yes card |
| `update <currency_id> [--name] [--description \| --clear-description]` | `update` | the name or the description | yes card |
| `mappings upsert <currency_id> --file <mappings.json>` | `mappings_upsert` | adds or changes the mappings it names; the others stay | yes card |
| `mappings delete <currency_id> --product <product_id>` | `mappings_delete` | removes one product's mapping | yes card |
| `transactions list` | `transactions_list` | one page of the app's coin transactions in a period | no |
| `profiles transactions list` | `profiles_transactions_list` | one page of one user's coin transactions | no |
| `profiles balances get` | `profiles_balances_get` | one user's balance of each currency | no |
| `profiles transactions create` | `profiles_transactions_create` | credits or debits one user's balance in one currency | yes card |

The currency and mapping shapes, the mapping file, the cards and the server's refusals:
[references/mappings.md](references/mappings.md). The ledger, the balances, "why does this
user have N coins" and a balance adjustment: [references/ledger.md](references/ledger.md).
Without `--yes`, `create`, `mappings upsert`, `mappings delete` and `profiles transactions create`
ask at a terminal and, in a pipe or with `--json`, exit 6 and send nothing; a "no" at the terminal
is exit 1. `update` asks nothing. Exit 2 is a refusal before anything was sent, 3 a missing or
refused sign-in or right, 4 the server's refusal with its own text, 5 no answer from the server.

## The yes rules

Over the CLI and over MCP alike. Only an answer to the card counts, not an earlier "go ahead"
about the plan. "No", silence or a change of plan: send nothing.

- **Reads need no yes:** `list`, `get`, the transactions and the balances.
- **Read the currency (`get`) right before each write** (before a create, `list`: the codes in use
  and the places left) and build the card from that read: [references/mappings.md](references/mappings.md),
  "Building the card", has the line for each kind of write. A balance adjustment reads the user's
  balances (`profiles balances get`) instead and takes no token: its card line is in
  `references/mappings.md`, its write in [references/ledger.md](references/ledger.md), "Adjust
  one user's balance".
- **The `updated_at` of that read is the token of the write:** over MCP `expected_updated_at`
  (`update` takes it too); with the CLI `--yes --expected-updated-at <updated_at>` on `mappings
  upsert` and `mappings delete`, which exit 6 without it. The CLI `update` takes no token: call
  `get` again just before it and ask again when anything changed since the card.
- **The server says `virtual_currency_conflict` (409):** someone changed the currency after your
  read, and nothing was written. Read it again, show a new card from the new read, and write only
  after a new yes. Never resend with a newer token on the old yes.

Example of a card's shape, not words to copy:

> Change the coins of Gems for 2 products:
> - Annual: 30 → 50 gems for each paid period
> - Coin pack S: new, 10 gems for each purchase
>
> **Purchases from now on credit the new numbers;** past purchases keep what they got. Change it?

Then call the tool, or run the command: `create`, `mappings upsert` and `mappings delete` with
`--yes` (the two mapping commands with the token too), `update` with no `--yes` (it has no such
flag). Read the answer back: the currency with all its mappings, and for an upsert which products
it created, updated or left unchanged.
**An unattended run never writes** (a scheduled run, a script, no user to answer): it reads, then
stops and reports the card and the command for the user to run, written with a literal `adapty`
and **without** `--yes`.

## Workflow

1. **Pick the app and read its currencies** (`list`). No currency yet: offer to create one, with
   its card.
2. **Name the products.** A mapping holds only the `product_id`; take each product's name from
   `products list` (MCP `products_list`), every page, and never show a bare id. A mapped product
   on no page was deleted: say so, with its id.
3. **Show the mappings** with `get`: each product, its coins for each purchase or each period, and
   for a subscription whether the coins expire and the trial coins.
4. **Change mappings** with `mappings upsert`: each item is the whole mapping, every field from the
   read or the user's words (`references/mappings.md`, "The mapping file and the MCP list"). To
   stop a product giving coins, `mappings delete`.
5. **Change the name or the description** with `update`. A description the user does not change
   stays; to clear it: CLI `--clear-description`, MCP `description` set to `""`.
6. **Why a user has N coins, where their coins went, or why a purchase gave none:** the balances,
   then their transactions (`references/ledger.md`, "Why a user has N coins").
7. **Credit or debit one user's coins by hand** (a support compensation, a correction):
   `profiles transactions create`, after its card (`references/ledger.md`, "Adjust one user's
   balance"). After "why N coins", offer it as the next step only when the user expected another
   number or asks for a fix.
8. **Totals, trends and how coin products sell** are read from analytics: offer the answer as an
   outcome ("I can show how many gems were bought and spent each week") and invoke
   `growth-advisor` on a yes, with the currency's code and each product's coins from your read.

## A lost answer

The CLI and the tools never repeat a write. **After a write whose answer was lost (no answer, or a
5xx), read the currency before anything else (after a create, `list`):** the write may have
passed. A repeat can then give the 409, a 404 for a removed mapping, or the 400 of a used code
although the first write passed.
Compare the read with the card, tell the user what is there, and write again only for what is still
missing, with a new card from the new read.
**A balance adjustment is the exception:** repeat it once with the same idempotency key, never
with a new one (`references/ledger.md`, "A lost answer of an adjustment").

## Never

- **Never pass `--yes` on a command the user will run themselves.**
- **Never build a mapping from memory:** every field comes from a read or the user's words. Never
  change a product's type in a mapping (the server refuses it).
- **Never add up transaction rows as a total or a trend:** that is `growth-advisor`'s chart read.
- **Never retry a refused write with changed values** to get it through: say the server's reason
  in plain words (`references/mappings.md`, "Refusals the server sends") and ask.
- **Never guess an id or a field:** take each from a read or `--help`.

## Feedback note

**Send Adapty one feedback note per write, right after it,** and one when the user asked for a
write and the run stops before it. A run that only reads sends none. Write it in English, in this
shape: the shape to follow, not words to copy:

> Change: the coins of two products, one of them new. Source: growth-advisor. Did: changed the
> mappings.

> Change: a new currency with one product. Source: not given. Did: stopped before the create. Got
> in the way: virtual-currencies create failed with http_500 (request id req_7f3a9c), and this
> skill does not say whether a retry is safe.

- **Change is the kind of write in a few generic words:** a new currency, the coins of how many
  products (new or changed), a removal, a new name, a credit or a debit of one user's balance.
  **Source** is `growth-advisor`, `migration` (from another purchase system), `own data`, `other`
  with a few generic words, or `not given`;
  never ask for it. **Did** names the write, or that the run stopped before it.
- **No value and no name from the account or the user's business:** no currency name or code,
  product, coin number, price or user id, none of the user's words. The ids in `--context` are all
  Adapty needs.
- **Sentiment is your own outcome, never the user's mood:** `positive`, done the way this skill
  describes, or declined because this skill says it cannot be done; `neutral`, done after a wrong
  turn or a workaround; `negative`, this skill or the CLI stopped you. Neutral and negative notes
  add "Got in the way:" with the command and its error, never a value.
- **Write the note into the command in single quotes,** never from a file or a script. Inside
  single quotes the shell runs nothing, so drop backticks and write "does not" for "doesn't":

  ```bash
  $ADAPTY feedback --feature virtual-currencies --sentiment <positive|neutral|negative> \
    --message '<the note>' \
    --context 'app <app id>, currency <currency id>: <create|update|upsert|delete>'
  ```

  For a balance adjustment the context is `app <app id>: adjust`.

- **Tell the user in one line, in the same reply, only when the command printed `Feedback sent.`**:
  in their language, "I also sent Adapty a short note on how this went." Any other result gets no
  line at all. Never retry, never hold up the reply.
- **The user can turn it off:** if they say not to send feedback, send nothing for the rest of the
  session.

## Anything not covered here

`$ADAPTY virtual-currencies <command> --help` for the flags on the installed version; the
`adapty-docs` skill for any dashboard behaviour. Do not guess a flag, a field name or a URL.
