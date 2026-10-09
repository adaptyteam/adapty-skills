# Adapty Skills

[![skills.sh](https://skills.sh/b/adaptyteam/adapty-skills)](https://skills.sh/adaptyteam/adapty-skills)

Subscriptions are the part of a mobile app nobody wants to build and everybody has to — SDK wiring, paywall UI, store config, then the ads and tests that make it pay.

**These skills hand that whole surface to the agent you already have open.**

```
> /adapty-integration

  Detected Flutter — pubspec.yaml, ios/ and android/ present

? Paywall approach          → Flow Builder (no-code editor)
? Integrations              → Amplitude, AppsFlyer
? Adapty app                → Create a new one

  Creating app, access level, products and placement via the Adapty CLI…
  Fetching flutter-sdk-overview docs before writing Stage 1…
```

**Supported platforms:** iOS · Android · Flutter · React Native · Unity · Kotlin Multiplatform · Capacitor

## The toolkit

Every install below gives you the whole toolkit — and it grows, so an update brings new skills with it.

| Skill | What it does | Needs |
|---|---|---|
| [`adapty-integration`](#integrating-the-sdk) | Sets up in-app purchases end to end — dashboard, SDK, paywall, store config — or moves you over from another purchase system | Adapty CLI |
| [`growth-advisor`](#growing-revenue) | Reads your subscription numbers, finds where the app leaves money, and gives you a test plan per placement — prices, plans, trials, countries, offers — then builds the tests that are flows | Adapty CLI |
| [`adapty-attribution`](#reading-ad-attribution) | Reads your Adapty Attribution data: which channels, campaigns, ads and countries pay back, trial quality, weekly changes, predicted payback, and why an ad network's numbers differ from Adapty's | Adapty CLI, Adapty Attribution |
| [`ads-manager`](#managing-apple-search-ads) | Runs your Apple Search Ads: performance across campaigns and keywords, bid and budget changes, search-term harvesting, campaigns on and off | Adapty CLI, Apple Ads account |
| [`flow-audit`](#auditing-a-flow) | Answers "did I forget anything?" before you publish a flow — triggers, products, variables — with a verdict and ranked fixes | Adapty CLI |
| [`flow-generator`](#building-flows-and-paywalls) | Builds a paywall or onboarding flow, or changes one you have: translate it, rewrite the copy, add or reorder screens, add tabs and plan pickers, wire quiz branching | Adapty CLI |
| [`migrate-placements`](#migrating-placements-to-flows) | Moves an app from paywall placements to flows — creates the new flow placements alongside your existing ones and hands back the old→new mapping and the one call to change | Adapty CLI |
| [`onboarding-teardown`](#tearing-down-an-onboarding-flow) | Reads an onboarding flow — described, screenshotted, or as a config — and ranks what to change and test, seam with the paywall included | nothing |
| [`paywall-teardown`](#tearing-down-a-paywall) | Reads any paywall — yours, a competitor's, a work in progress — and ranks what to change and test | nothing |
| `purchase-testing` | Gets your first sandbox purchase through, and when one fails, checks your dashboard and app code before sending you to a store console, then names the layer that broke | Adapty CLI |
| `adapty-docs` | Answers a question about Adapty — a dashboard setting, a limit, an API endpoint, an SDK method — from the right page of Adapty's docs | nothing |

The Adapty CLI comes from `npm install -g adapty`. You don't have to keep it current — the skills check the version themselves and fetch a newer one when they need it, rather than telling you a command doesn't exist.

## What you can ask

Say what you want the way you'd brief a colleague. You don't need to name a skill; your agent picks the right one:

- "Add subscriptions to my Flutter app with Adapty."
- "We're on RevenueCat today and want to switch our iOS app over to Adapty."
- "My sandbox purchase on the iPhone isn't going through. Why?"
- "Add a German translation to my paywall flow."
- "Before I ship this paywall flow to paying users, did I miss anything?"
- "Here's my paywall. What should I test to convert better?"
- "Audit my app. What should I test next to grow revenue?"
- "Revenue dropped last month. Why?"
- "Which of my ad channels actually pays back? Should I move budget from TikTok to Meta?"
- "How did my Apple Search Ads campaigns do last week, and which keywords should I pause?"

## Install

### Claude Code

```bash
claude plugin marketplace add adaptyteam/adapty-skills
claude plugin install adapty-skills@adapty
```

Then run `/reload-plugins` inside Claude Code. One plugin, `adapty-skills`, carries every skill in the repo.

<details>
<summary><strong>Already installed as <code>adapty-sdk-integration</code>?</strong></summary>

<br>

That handle still works and still updates, so nothing breaks if you do nothing. To move over, install the new one and remove the old one — leaving both installed loads the same skills twice:

```bash
claude plugin install adapty-skills@adapty
claude plugin uninstall adapty-sdk-integration@adapty
```

The skill you invoke is now `/adapty-integration` (previously `/adapty-sdk-integration`).

</details>

### Codex

```bash
codex plugin marketplace add adaptyteam/adapty-skills
codex plugin add adapty-skills@adapty
```

Then start a new thread, so Codex picks up the skills. One plugin, `adapty-skills`, carries every skill in the repo.

To pull later changes:

```bash
codex plugin marketplace upgrade
codex plugin add adapty-skills@adapty
```

### Any agentic CLI

The [skills CLI](https://skills.sh) installs into any supported agent — Cursor, Copilot, Codex, Gemini CLI, Zed, Amp, and more:

```bash
npx skills add adaptyteam/adapty-skills --all
```

`--all` is `--skill '*' --agent '*' -y`: every skill, every agent it detects, no prompts. Drop it and the CLI asks which ones you want, which is fine at a keyboard but hangs in a script.

For one skill only, name it:

```bash
npx skills add adaptyteam/adapty-skills --skill ads-manager
```

Skills installed this way don't update automatically. To get the latest later:

```bash
npx skills update
```

### Copy the directories

The skills are portable directories under `plugin/skills/`, and every CLI below reads the same Claude-style `SKILL.md` format — so copying them into place works. The `plugin/skills/*` glob takes all of them.

**GitHub Copilot CLI** — [docs](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills):

```bash
git clone https://github.com/adaptyteam/adapty-skills.git
cp -r adapty-skills/plugin/skills/* ~/.copilot/skills/
```

**OpenAI Codex CLI** — [docs](https://developers.openai.com/codex/skills). The [plugin](#codex) is the better route unless you want one project scoped to its own copy. Use `~/.agents/skills/` for personal, `<repo>/.agents/skills/` for project:

```bash
git clone https://github.com/adaptyteam/adapty-skills.git
cp -r adapty-skills/plugin/skills/* ~/.agents/skills/
```

**Gemini CLI** — [docs](https://geminicli.com/docs/cli/skills/):

```bash
gemini skills install https://github.com/adaptyteam/adapty-skills --path plugin
# or manually:
git clone https://github.com/adaptyteam/adapty-skills.git
cp -r adapty-skills/plugin/skills/* ~/.gemini/skills/
```

## Integrating the SDK

Working in-app purchases: dashboard, SDK code, paywall, store config. Open your mobile project in your agentic CLI and run:

```
/adapty-integration
```

(In CLIs that don't map slash commands to skills, "Use the adapty-integration skill" does the same. That holds for every skill below.)

The skill takes over from there. It will:

1. **Detect the platform** from the project structure
2. **Ask three questions** — paywall approach, third-party integrations, and whether to use an existing Adapty app or create a new one
3. **Configure the Adapty dashboard** via the Adapty CLI
4. **Implement the SDK** stage by stage, fetching the latest docs before writing each piece of code
5. **Verify each step** with build checks and visual checkpoints before moving on

You'll be asked for your Adapty credentials and a few decisions along the way — the rest is automated.

### Flow & paywall approaches

- **Flow Builder** (recommended) — Adapty renders paywalls *and* onboarding in a no-code editor; nothing to build. On Unity and Capacitor this is Paywall Builder, the previous generation, which does paywalls only
- **Custom paywall** — you build the UI; Adapty provides products and handles purchases
- **Observer mode** — keep your existing StoreKit / Billing code; Adapty tracks events only

## Growing revenue

A growth review of your app from its own numbers, the way a subscription growth manager would run one.

```
/growth-advisor
```

It reads your revenue, renewals, trials, installs and refunds through `adapty analytics`, with your placements, paywalls and products, then asks what it cannot see: what you have tested before, which apps you compete with (it reads their prices from their App Store pages once you confirm the list, or from its own picks, named as such, when you are not there to confirm), and your paywall if you want design ideas too. You get back what your numbers say and a short test plan grouped by placement, in the order to run it. Each test names the reason from your own data, the metric that decides it, and an expected range from real A/B tests on subscription apps, or says plainly that it is untested.

**It changes nothing live without your yes.** A test that is a flow — an offer after the paywall closes, a seasonal paywall, a paywall at a new moment in the app — is built by `flow-generator` after your yes. You choose how users get it: an A/B test in the dashboard (the default, and the only way to know what it did), a new placement, or an existing placement for some or all of its users. Before it changes an existing placement it saves what is there, asks you to confirm no A/B test is running on it, and tells you exactly who will see what. Prices, trials and A/B tests are yours to change in the store and the dashboard; it gives you the exact values and the steps. After a test ends, tell it what won and it plans the next one.

## Reading ad attribution

An analyst on your Adapty Attribution data, measured against the subscription revenue Adapty holds for every user.

Open your terminal in any directory and ask for it:

```
/adapty-attribution
```

It carries ten playbooks: ranking channels and campaigns by payback and deciding where budget goes, judging a young campaign at a horizon it has actually reached, trial-to-paid quality by campaign, a weekly digest with week-over-week flags, countries and stores, the winning ads inside a campaign, refund-heavy traffic, predicted payback, reconciling an ad network's numbers with Adapty's, and diagnosing a drop in installs.

**It only reads.** Every call goes through `adapty attribution`, which changes nothing. Apple Search Ads spend is not collected by Attribution, so the skill reads it through Ads Manager and reports it on its own line, in its own currency. Setup questions — connecting Meta, TikTok or Google Ads, tracking links, the web pixel, Stripe or Paddle — go to the docs pages that own them.

## Managing Apple Search Ads

An analyst on your ad account — bids, budgets, keyword harvests, dead-ad diagnosis.

You need a connected Apple Search Ads account and an active Ads Manager subscription — `adapty asa whoami` tells you where you stand.

Open your terminal in any directory and ask for it:

```
/ads-manager
```

It covers ten workflows: orienting on your account, reporting performance, launching a campaign (seeded from Adapty's keyword recommendations when you have no keyword list), harvesting keywords from search terms, a bid-and-budget optimization pass, pausing or resuming, running ads against a custom product page, diagnosing an ad that isn't serving, rule-based automations, and a competitor check.

**It treats your ad account as live money.** There is no delete and no undo in this surface, so the skill confirms before every write, never invents an ID or a budget, prefers small keyword batches, and pins idempotency keys so a re-run can't double-apply. Reads and automation dry runs are free, and it uses them freely.

## Auditing a flow

The broken product binding, caught before your users find it. `flow-audit` answers one question: **is this Flow Builder flow ready for production?**

**It's read-only.** It never calls `flows config update`, `products create`, or `flows create` — it fetches the flow's config and cross-references it against your live dashboard (catalog, access levels) to catch what an offline checker can't, like a bound product that doesn't exist or a card whose copy claims a period the product doesn't have.

```
/flow-audit
```

(Or "audit my flow" / "is this ready to publish?")

It checks six families — triggers, store compliance, products, variables, localization, and placeholders — plus whether any placement shows the flow, and comes back with a plain-language verdict (**Ready to publish**, **Not ready to publish yet: n things to fix first**, or **Almost ready: n things I could not check**), numbered findings that each say what is wrong, why it matters to a real user, and how to fix it, and a **What happens next** section: what to answer first, what the agent can fix for you, and what only you can do in the dashboard. It answers in your language.

**It never certifies what it couldn't see.** A question it can't answer from the data — can the host app dismiss this paywall on its own, are your products approved in App Store Connect — keeps the verdict from reading a bare **Ready to publish** until you've weighed in. When you want something fixed, it offers to do it and hands the findings to `flow-generator`, which owns the actual write.

## Building flows and paywalls

Describe the screen you want and get it built — or change one you already have, without opening the editor. `flow-generator` writes an [Adapty Flow Builder](https://adapty.io/docs/adapty-flow-builder) flow as JSON.

**It authors new flows, and it transforms flows that exist.** Authoring is what most people reach for: product IDs come from your catalog (it asks which to use before designing anything), and the only things it will never invent are uploaded images and videos, real store prices, and proof numbers like ratings — those it asks you for, or leaves visibly out. Transforming your own flow is the safer path when you have one — theme, fonts, locales and products are inherited, so everything the skill writes is real.

It reads and writes the config through the Adapty CLI, so you don't export or upload anything by hand, and it sorts out the CLI itself rather than telling you a command doesn't exist.

```
/flow-generator
```

It runs five phases: authenticate, work out whether to create a flow or edit an existing one, validate the config, preview it and iterate until it looks right, then save and ask before it publishes. Validate and preview both run on a local file, so the agent gets it right before anything reaches your dashboard.

Four transforms:

- **Add a locale** — extend the flow's locales and fill in every localizable field
- **Rewrite copy** — change wording without touching structure
- **Screens** — add, remove, or reorder, repairing the navigation that a deletion breaks
- **Branching and conditions** — selectable groups, option IDs, and the conditional actions that route on them

**It saves to a draft; publishing is a separate word from you.** A newer CLI has a publish command, but the skill never folds it into a save — it asks first. And the publish endpoint isn't in production yet, on any account, so for now it hands you the editor's publish button instead. There is no delete command at all, so removing a flow stays yours. Every write after the first carries the flow's `updated_at` as an optimistic lock, so a save can't quietly overwrite an edit someone else made in the meantime — it fails instead. It asks before creating a product. And because a config can save cleanly and still not render, the agent screenshots the preview and looks at it before telling you it's done.

## Migrating placements to flows

You have [placements](https://adapty.io/docs/placements.md) pointing at paywalls, and you want them pointing at [flows](https://adapty.io/docs/adapty-flow-builder.md) instead. `migrate-placements` reads every placement in the app, works out which ones are worth moving, and creates the flow placements for you.

```
/migrate-placements
```

**None of this is in production yet, on any account** — neither the publish endpoint nor the placement audience a flow needs — so the skill probes for the capability first and, until it ships, hands you [Placements](https://app.adapty.io/placements) in the dashboard instead of a half-finished migration.

**Placements are created, never converted.** A placement's content type is fixed the moment it exists — the backend refuses a change — so there is no in-place upgrade to be had. Every migration is a new placement standing next to the old one.

That shape is what makes it safe: **your paywall placements are left untouched, and that is the rollback.** Ship the new call, and if anything looks wrong, point the app back at the old ID — nothing was taken away.

The cost is the ID. A new placement **cannot reuse** the old developer ID (IDs are unique across every placement in the app, whatever its type) and a placement cannot be deleted, so a name you regret is permanent. Every proposed ID is shown to you for approval before anything is created.

One flow per distinct paywall, reused across every placement that pointed at it — two placements sharing a paywall get one flow, not two. You get back the old→new mapping, and the single call in your code that has to change.

**The migration is not done when the placements exist.** Nothing reaches users until the app ships the new call, so the last row of the report is yours.

## Tearing down a paywall

A screenshot turned into a ranked list of things to test. Like [`onboarding-teardown`](#tearing-down-an-onboarding-flow), it needs **no CLI, no account and no credentials** — it reads what you give it and writes nothing anywhere.

Paste a paywall screenshot and say roughly nothing:

```
/paywall-teardown
```

(Or just drop the image in — "here's my paywall" is enough.)

You get back a read of the vertical and its trust axis, a line on what's already working, and 5–8 prioritized rows: the named pattern, the specific change applied to *your* screen, where that pattern shows up across categories, and an expected-impact range. It handles competitor screenshots and half-finished designs too.

**It also works forwards.** Ask for a paywall instead of a critique of one — or hand an agent "add a paywall screen" with no design attached — and the library becomes the reference the agent designs against: a build list of the patterns that belong on the screen for your category, in priority order, plus the short list of real values it refuses to invent for you (your actual rating, your actual review count, your actual outcome data, your hero asset). Then it grades the result and fixes what it finds, rather than handing you a report on a screen it just built. `flow-generator` calls it at both ends for exactly this — before it writes the config, and again over the render — so a generated screen is held to the same library a live one would be. If you *do* give a design reference, that reference wins; the library only fills what it leaves unsaid.

Impact ranges are expected effect calibrated from Adapty's teardowns of top subscription apps across many verticals — not measured lift for your app. Ship the tests and get your own numbers.

## Tearing down an onboarding flow

The same treatment, one level up: the **sequence** rather than the screen. It needs no CLI, no account and no credentials either.

Onboarding is a sequence, and that is the one thing a screenshot cannot show — so this one starts with a short interview instead of an upload:

```
/onboarding-teardown
```

Six questions, one at a time, each answerable with a tap or a line: your category, how long the flow is, what the first screen is, whether you ask what users want and give them something personalized back, when the paywall appears, and when you ask for permissions. Answer three of six and it still delivers.

You get back your flow written out as a line (often the first time anyone has seen it that way), what's already working, 5–8 prioritized rows, and a paragraph on **the seam** — whether the paywall reflects what onboarding just spent five screens capturing. That seam is where the expensive findings live: a goal question with nothing behind it, a loader promising a personalized plan that the next screen doesn't deliver.

**Hand it a flow config and it stops interviewing.** The sequence, the branching, the goal capture and the paywall's position are all in the file; it reads them and asks only what the JSON cannot say — your category, and whether the app truly delivers the payoff the flow promises.

**It also works forwards**, the same way its paywall counterpart does. Ask for an onboarding rather than a critique of one and the library becomes the reference: a skeleton chosen for your category from what your app can actually back, a per-screen build list, and the short list of things it refuses to invent — a projected outcome nobody modelled, real proof numbers, an asset nobody has a file for. `flow-generator` calls it at both ends, so a generated sequence is held to the same library a live one would be.

One constraint it will tell you about rather than quietly working around: **a flow cannot request a permission.** It can render the soft prompt that makes the ask land better, but the system dialog belongs to your app code — so permission-timing findings arrive as a handoff, not as something the builder can ship for you.

## How it keeps you safe

- **Your live app changes only when you say so.** `flow-generator` never publishes a flow on its own, and overwrites an existing flow only after you say yes to the exact change. A brand-new flow is saved as a draft.
- **Existing placements are never converted.** `migrate-placements` creates new flow placements beside your paywall ones, which stay as your rollback, and shows every new ID for your approval first.
- **Ad spend changes wait for you.** `ads-manager` names each bid, budget, keyword or campaign change in chat and runs it only after your yes.
- **You see your account before anything is created.** `adapty-integration` reads what already exists in your Adapty dashboard and tells you what it will use and what it will add, then writes code only in your project.
- **Growth plans change a live placement only on your yes.** `growth-advisor` reads your numbers, saves a placement before changing it, and asks you to confirm no A/B test is running there first, since the CLI cannot see one.
- **Five skills only read.** `flow-audit`, `adapty-attribution`, `adapty-docs`, `paywall-teardown` and `onboarding-teardown` change nothing in your account.

## Where it works

The skills are built for agents that can run commands on your machine: Claude Code, Codex, Copilot CLI, Gemini CLI and similar. Eight of the eleven need a shell and the Adapty CLI signed in to your account.

`paywall-teardown`, `onboarding-teardown` and `adapty-docs` need neither, so they also work in Claude chat and Cowork, where the other skills cannot reach your Adapty account.

## Requirements

- An agentic CLI that supports the Claude Skills format — [Claude Code](https://claude.com/claude-code), [GitHub Copilot CLI](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills), [OpenAI Codex](https://developers.openai.com/codex/skills), or [Gemini CLI](https://geminicli.com/docs/cli/skills/)
- An [Adapty account](https://app.adapty.io/) (free tier works)

Adapty SDK overviews: [iOS](https://adapty.io/docs/ios-sdk-overview) · [Android](https://adapty.io/docs/android-sdk-overview) · [Flutter](https://adapty.io/docs/flutter-sdk-overview) · [React Native](https://adapty.io/docs/react-native-sdk-overview) · [Unity](https://adapty.io/docs/unity-sdk-overview) · [Kotlin Multiplatform](https://adapty.io/docs/kmp-sdk-overview) · [Capacitor](https://adapty.io/docs/capacitor-sdk-overview)

### Corporate environments with a domain allowlist

If your agent runs somewhere with restricted outbound network access — Claude Cowork on a corporate plan, a managed sandbox, an egress proxy — an administrator has to allow both:

```
adapty.io
*.adapty.io
```

**List both.** A wildcard does not cover the apex domain in most allowlist implementations, and the apex is where almost everything goes: the skills fetch documentation from `adapty.io/docs/...` (the large majority of requests), the dashboard is `app.adapty.io`, and the Adapty CLI talks to `api-admin.adapty.io` and, for Apple Search Ads, `api-asa-admin.adapty.io`. Allowing only `*.adapty.io` blocks the docs the agent reads before writing any code.

## What the skills run, fetch and send

The skills are instructions and a few local helper scripts. They run nothing on their own: everything below happens because your agent follows a skill, inside your agent's own permission prompts.

**They collect nothing and call no Adapty endpoint of their own.** No telemetry, no analytics beacon, no feedback upload. Nothing from your conversation, your code or your files leaves your machine except through the calls listed here.

| What | When | Where it goes |
|---|---|---|
| The **Adapty CLI** (`npm install -g adapty`, or `npx adapty` where a global install is not possible) | Every skill except the two teardowns, to read and change your Adapty dashboard | `api-admin.adapty.io`, and `api-asa-admin.adapty.io` for Apple Search Ads, signed in as you through the CLI's own `adapty auth login` |
| **Adapty docs pages** | Before the agent writes code or answers a product question | `adapty.io/docs`. The fetch carries a `?ref=skill-<token>` tag: a random token the agent makes up for that session, so Adapty can see which pages get read together. It contains nothing about you or your project |
| **SDK version lookups** | Once per integration, to pin the current SDK release | `api.github.com`, `pub.dev`, Maven Central, depending on the platform |
| **Flow config schema** | When `flow-generator` checks a config | `app.adapty.io/flow-schema/latest.json`, cached in your temp directory |
| **Flow previews** | When `flow-generator` renders a screen for you to look at | Your flow config is opened in Adapty's preview page (`app.adapty.io`) in a local headless Chrome. The preview link for a phone is `mobile-app.adapty.io` |
| **Competitors' App Store pages** | When `growth-advisor` compares your prices: the apps you confirmed, or its own picks when you are away | `apps.apple.com` and the public App Store search at `itunes.apple.com`, read without signing in |
| **Images you hand over** | Only when you give `flow-generator` an image for a flow | Uploaded to your Adapty account's media library through the CLI |
| **Optional helper packages** (`ajv`, `playwright`, `qrcode`) | Only for the schema check, the Playwright preview and the QR code, each installed once into `~/.cache/` | The npm registry |

`ads-manager` changes bids, budgets, keywords and campaign status in your Apple Search Ads account. It names every change in chat and waits for your yes before it runs one; it never moves money between accounts.

## Privacy, license and support

- **Privacy.** The skills process data only inside your agent session and through the calls above. Whatever the Adapty CLI returns, such as campaign numbers, product IDs or flow content, enters your agent's context and reaches the model provider you use with it, like any other tool result. Your Adapty account is covered by [Adapty's privacy policy](https://adapty.io/privacy/) and [terms](https://adapty.io/terms/).
- **License.** [MIT](LICENSE).
- **Security.** Report a vulnerability privately — see [SECURITY.md](https://github.com/adaptyteam/adapty-skills/blob/main/SECURITY.md).
- **Support.** Open an [issue](https://github.com/adaptyteam/adapty-skills/issues), or email [support@adapty.io](mailto:support@adapty.io).
