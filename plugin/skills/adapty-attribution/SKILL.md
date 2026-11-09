---
name: adapty-attribution
description: Use when someone asks how their ad campaigns, channels, ad sets, ads, countries or keywords are performing in Adapty Attribution — ROAS, payback, CPI, cost per trial, installs, trial-to-paid, refunds, predicted revenue — which channel or campaign to scale or cut, where to move budget, why installs dropped, why Meta, TikTok or Google report different numbers than Adapty, or how to set up Adapty Attribution with Meta, TikTok, Google Ads, custom tracking links or a web funnel.
---

# Adapty Attribution

Adapty Attribution matches installs and web purchases to ad clicks and reports them against the
subscription revenue Adapty already holds for every user. You read it through the Adapty CLI's
`attribution` topic, which is read-only: nothing you run here changes a campaign, a link or a
setting.

Open `references/playbooks.md` when a question matches one of its playbooks. It holds the
commands, the reading and the reply shape for each common question.

## Which "attribution" the user means

| The question is about | Where it goes |
|---|---|
| Campaign, channel, ad or country performance in Adapty Attribution | This skill |
| Setting up Meta, TikTok, Google Ads, tracking links, the web pixel, Stripe, Paddle or FunnelFox for Adapty Attribution | The `adapty-docs` skill. Start at [Get started](https://adapty.io/docs/user-acquisition.md) or [Integrations](https://adapty.io/docs/ua-integrations.md) |
| AppsFlyer, Adjust, Branch, Singular, Tenjin, Airbridge or another MMP connected to Adapty | The `adapty-docs` skill. Start at [Attribution integrations](https://adapty.io/docs/attribution-integration.md) |
| Apple Search Ads bids, budgets, keywords or campaigns | The `ads-manager` skill |
| SDK code in the app | The `adapty-integration` skill |

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

**This skill prefers MCP** when both are ready.

## The CLI

Resolve `$ADAPTY` once and use it for every call:

```bash
adapty attribution --help >/dev/null 2>&1 && ADAPTY="adapty" || {
  npm i -g adapty@latest >/dev/null 2>&1
  adapty attribution --help >/dev/null 2>&1 && ADAPTY="adapty" || ADAPTY="npx --yes adapty@latest"; }
```

If `$ADAPTY attribution --help` still reports no such topic, try `npx --yes adapty@beta attribution
--help` once before telling the user the topic is unavailable. `--yes` is required: without it
npx waits for a confirmation nobody will give. In `zsh`, run `setopt shwordsplit` before using a
multi-word `$ADAPTY`. When you show a command to the user, write a literal `adapty` in it.

- Find the app id with `$ADAPTY apps list`.
- Run `$ADAPTY attribution metrics` and `$ADAPTY attribution dimensions` before your first
  report, and take metric and dimension names from them. Family names such as `d{N}_roas` are
  templates: pass `d7_roas`, never `d{N}_roas` or `d07_roas`.
- Campaign, ad set and ad filters take ids. Get them from `$ADAPTY attribution values --dimension
  campaign` (or `adset`, `ad`) and match entities across periods by id, never by name.
- Run reports one at a time. The service runs only a few queries per company at once, and
  `report` and `values` are never retried for you. On `attribution_busy`, wait
  `retry_after_seconds`, then run the call once more.
- `attribution_access_required` means the company has no Attribution access, so spend, CPI and
  ROAS are out of reach. Logging in again will not fix it; say so once and run no more
  `attribution` calls. A question about which channel brings users, subscribers or money is
  still answerable from the app's subscription analytics: invoke `growth-advisor` now and answer
  it in this reply, by installs, trials, trial-to-paid and revenue per channel, saying spend and
  ROAS are not in them. Only a question about spend, CPI or ROAS itself ends here.

## Apple Search Ads spend is not in Attribution

Attribution collects ad spend from Meta, TikTok and Google Ads only. Apple Search Ads rows carry
installs and revenue, and every spend-based metric on them — spend, CPI, ROAS, ad profit, cost per
trial — is `null`. No setting, connection or wait changes that, and connecting Apple Ads does not
either: its spend and ROAS live in Ads Manager, a separate report. When you say where to find them,
say it this way: **"Apple Search Ads spend and ROAS are in Ads Manager. They will not appear next
to the other channels in Attribution."**

To judge Apple Search Ads next to the other channels:

1. Get its spend and ROAS through the `ads-manager` skill, which owns the `asa` commands, for the
   same dates (the call is in `references/playbooks.md`, playbook 1). If `$ADAPTY asa whoami` says
   Apple Ads is not connected, the user connects it in Ads Manager, and its numbers appear there,
   not in Attribution.
2. Report it as its own line, marked as coming from Ads Manager. Name its currency, which is the
   campaign group's currency, not USD, and read it from `asa orgs list`.
3. Never add Ads Manager spend into Attribution rows or totals, and never compute one ROAS from
   Ads Manager spend and Attribution revenue. The two attribute installs differently.
4. The same holds for a spend figure the user gives you. Turn it into a threshold instead of a
   ROAS: "Apple Search Ads beats TikTok if its August spend was under $X" or "it pays back at a CPI
   under $Y", where X and Y come from its Attribution revenue.

If the user has no Apple Ads access, leave Apple Search Ads out of any ranking, say why, and give
its Attribution installs and revenue.

## How you sound

- **A patient colleague who knows ad measurement and subscriptions.** The user may be new to
  them. Answer plainly, using their own campaigns as the example.
- **"I" for what you do, "you" for what they do.** Lead with the answer and end on the one next
  step. No opener, no recap.
- **Name what every number is.** The revenue basis (gross, proceeds or net), the currency, and
  whether a value is realized so far or predicted. Say ROAS as a percent or a multiple, not both
  mixed in one table.
- **Say what you could not see and where they can check it.** The CLI reads reports, not
  integration settings, event mappings or ad-network dashboards.
- **Full, clickable links to the exact page.** Take docs URLs only from this skill or from an
  `llms.txt` index the `adapty-docs` skill names; never assemble one.
- **Reply in the user's language.**
