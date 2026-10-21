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

## The CLI

Resolve `$ADAPTY` once and use it for every call:

```bash
adapty attribution --help >/dev/null 2>&1 && ADAPTY="adapty" || {
  npm i -g adapty@latest >/dev/null 2>&1 && ADAPTY="adapty" || ADAPTY="npx --yes adapty@latest"; }
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
- `attribution_access_required` means the company has no Attribution access. Logging in again
  will not fix it; say so and stop.

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
