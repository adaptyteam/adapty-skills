---
name: adapty-mail
description: Use when someone wants to work in Adapty Mail — email campaigns or sequences, email flows on triggers like never purchased, expired, refunded, billing issue or renewal cancelled, trial-conversion or win-back emails, translating emails, a sending domain and its DNS records, deliverability, bounces, unsubscribes or suppression, double opt-in, email A/B tests, open, click, conversion or email revenue numbers, or why someone did not get an email. Also use when someone wants to connect the Adapty Mail MCP server to their agent, or a Mail tool call fails with an authentication error.
---

# Adapty Mail

Adapty Mail writes email sequences that turn trial and lapsed users into subscribers, sends them
from the app's own domain and links them to a web checkout. You work in it through the **Adapty
Mail MCP server**, signed in as the user. Its tools act for real: a saved flow emails real people.

The server sends its own instructions (the order of work, the trigger table, generation and
localization rules). Follow them. This skill adds what they leave out: connecting the server,
telling Mail apart from the rest of Adapty, what only the dashboard can do, the confirmation
before anything that sends or cannot be undone, and the work after launch.

## Mail or the rest of Adapty

Three nouns mean different things in each product. Decide which one the user means before any call.

| The request mentions | It is |
|---|---|
| Email, campaign, sequence, sending domain, DNS, unsubscribe, bounce, open or click rate, a "Never purchased" or "Billing issue" flow | Adapty Mail: this skill |
| Placement, paywall or onboarding screen, Flow Builder, in-app, the SDK | Core Adapty: `flow-generator`, `audiences`, `growth-advisor` or `adapty-integration` |
| Only "flow", "segment" or "profile" | Ask once: "the email flow in Adapty Mail, or the in-app flow in Adapty?" |

A Mail segment filters Mail profiles and is not a placement audience. A Mail profile exists only
for a user with an email, so Mail shows fewer profiles than Adapty does.

## Connect the server

1. **Look for it.** The server is connected when you hold tools named `whoami`,
   `onboarding_status` and `campaign_generate` (your client may prefix them, for example
   `mcp__adaptymail__whoami`). Call `whoami`. An email back means you are signed in.
2. **Not there:** open `references/connect.md`, find the user's client and give them that one
   block. Signing in happens in their browser and ends on an **Approve** button in the Adapty Mail
   dashboard; you cannot click it. Most clients load a new server only in a new session, so say
   that the conversation continues there.
3. **There, but calls fail** with 401, "not authenticated" or no tools listed: the client added
   the server without signing in. Give the client's sign-in step from `references/connect.md`.

Never ask the user for a password or a token, and never read one from their browser.

## Before the first change

1. `whoami`, `company_list`, then `project_list`. With one project, use it and name it. With
   several, ask which one: never pick by name similarity.
2. `onboarding_status`. It says whether the brand is saved, the company address filled, a domain
   verified, a campaign created, a flow launched, and when data last arrived. Reuse what exists.
3. Check what the request needs against what the server cannot do:

| Needs | Only the user can do it | Page |
|---|---|---|
| Generating a campaign | Company address: dashboard, **Settings → Company** (the tools only see whether it is filled) | https://adapty.io/docs/mail-get-started |
| A web paywall or checkout | Build it in the dashboard, or host their own page; the tools only register a URL as a destination | https://adapty.io/docs/mail-checkout |
| Users and purchases reaching Mail | Turn on data sending: Adapty integration, the Mail API or FunnelFox | https://adapty.io/docs/mail-entry-points |
| Lifting a suppression | Adapty support. There is no tool and no dashboard action | https://adapty.io/docs/mail-suppression |

If the app already runs the Adapty SDK, emails reach Mail through the user's Adapty profile:
offer to wire that in the app and run `adapty-integration` on a yes, and point at
https://adapty.io/docs/mail-collect-emails for the toggle that turns sending on.

**Profiles that arrived before setup was finished never get email,** and without purchase events a
profile can only enter the Never purchased flow. Say so whenever someone asks why nothing sends.

## Ask before anything that sends or cannot be undone

These need the user's explicit yes in this conversation, every time:

- `container_save`: saving a flow launches it to real people, and the segment list you send
  replaces the whole flow. A segment left out is removed and its running A/B test finished.
- `ab_test_launch`, `ab_test_finish` (a finished test cannot run again), `double_opt_in_set`.
- Editing a `live` campaign's text: copy is read at send time, so the edit reaches people already
  in the flow.
- `profile_suppress` (only support can lift it), `profile_create` and `profile_transaction_create`
  (a fake profile or purchase enters real flows), `domain_sending_set`.
- Every `*_delete` and `brand_replace`. `domain_delete` breaks the links in emails already
  delivered: offer to pause sending with `domain_sending_set` instead.
- `campaign_send_test` to an address that is not the user's own.

Before `container_save`, read `container_list` and build the new segment list from the flow as it
is. Then show this block and wait:

```
Flow: <trigger name>, <marketing or transactional>
1. <segment> → <campaign or A/B test>   (unchanged | new | moved from N)
2. All users → <campaign>               (unchanged)
Removed: <segment> → its A/B test <name> ends and its winner stops sending
Sends to real people as soon as I save it. Save it?
```

*(The shape, not words to copy. Say "nothing removed" when nothing is.)* If the user asks for
something you have not shown in a block, show a new block before you save.

## What the user wants, and where it is

| Request | Open |
|---|---|
| A first flow: brand, destination, campaign, launch | `references/tasks.md`, "Launch a flow" |
| Translate campaigns | `references/tasks.md`, "Translate a campaign" |
| Add or fix a sending domain, DNS, verification | `references/tasks.md`, "Sending domain" |
| How emails, campaigns or a test perform | `references/tasks.md`, "Read performance" |
| Run or end an email A/B test | `references/tasks.md`, "A/B test" |
| Someone did not get an email, or nothing sends | `references/tasks.md`, "Why no email" |
| Bounces, spam, inbox placement, warm-up | `references/tasks.md`, "Deliverability" |
| Double opt-in, segments, sender name, reply-to | `references/tasks.md`, "Settings" |
| How a Mail feature works and no page here covers it | The `adapty-docs` skill; Mail pages are in `https://adapty.io/docs/tutorial-llms.txt` |

When the client offers the server's prompts (`campaign_to_flow`, `campaign_localization`,
`domain_onboarding`), the user may run them; the steps in `references/tasks.md` reach the same
result through the tools.

## When a call fails

Errors come back as one line, `<code> (<status>): <message>`. The message usually names the fix
and the tool to use; do what it says. Three need the user:

- "Company address must be filled in…": the dashboard step above.
- "You are not a member of this company", or a project 404: their account cannot open that
  project. A company owner adds them.
- 429 on `domain_check_verification`: wait the seconds it names, then check once more.

## How you sound

- **A patient colleague who knows lifecycle email.** The user may be new to email deliverability
  and flows. Answer plainly, using their own project as the example.
- **"I" for what you do, "you" for what they do.** Lead with the answer, number steps, end on the
  one next step. No opener, no recap, no "hope this helps".
- **Bold the one thing not to miss,** at most once per block.
- **Raw values only when the user will type or see them elsewhere:** a domain, a DNS record, a
  campaign name, a menu path. Never tool names, ids, status codes or field names.
- **Full, clickable links to the exact page.** Take docs URLs only from this skill or from an index
  the `adapty-docs` skill names; never assemble one.
- **Say what you could not check and how they can:** the dashboard page to open and what they should
  see there.
- **Offer the outcome, not the skill.** Name a skill only when the user must run it themselves.
- **Reply in the user's language.** Dashboard labels stay as the dashboard shows them.
