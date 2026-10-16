---
name: audiences
description: Use when a user wants different users to see different paywalls or flows at the same placement — by country, language, app version, platform, revenue, subscription state, install date, a custom attribute, or attribution — or wants to create, edit or reuse an Adapty segment through the CLI. Triggers on "show this paywall only to users in Germany", "target users on version 2.0", "a cheaper paywall for non-payers", "users with my custom attribute should see…", "create a segment", "add an audience to my placement", "who sees which paywall".
---

# Audiences: who sees what at a placement

A **segment** is a set of filters, all of which a user must match. An **audience** is one entry in
a placement: one segment (or none), one paywall or flow, one `priority`. The placement checks its
audiences from the lowest `priority` up and serves the first one the user matches; the **default
audience** (`segment_ids: []`) is last and catches everyone else. Every change this skill makes is
live for real users the moment the placement is written.

This skill owns segments and audiences. It does not own:

- **The paywall or flow itself** → `flow-generator` builds and publishes it. An audience can only
  point at content that exists, and a flow only once it is `published`.
- **Moving paywall placements to flows** → `migrate-placements`.
- **Segments built from Apple Search Ads campaigns, ad groups or keywords** → `ads-manager`,
  workflow 13 (`asa segments create` resolves the Apple ids and keeps the dashboard's naming).
  Come back here to route the segment it returns.
- **An attribute the app has to send** (custom attributes, age, gender, customer user ID) →
  `adapty-integration` owns the SDK call. A segment over an attribute nobody sets matches nobody.
- **A/B tests on an audience** — not in the CLI. Send the user to
  https://adapty.io/docs/add-audience-paywall-ab-test.

## A/B tests: the CLI cannot see them, and a write ends them

**`placements get` leaves out any audience that runs an A/B test, without saying anything.** The
response looks complete: an audience with a running test simply is not there. `placements update`
then replaces every audience with the array you send, so the test's audience disappears. The
backend treats it as deleted and **stops the test**: it shows as Completed with no winner, and the
users it covered fall through to the next audience. The CLI prints `Placement updated!` with no
error and no warning. A finished test cannot be restarted. The dashboard offers only Duplicate (a
new test with no data) and Archive.

**A skipped priority (even a lone default at `priority: 1`) or no default audience (often
`"audiences": []`) means a test is hidden there: do not write; send the change to the dashboard.**

When neither shape shows, still ask before writing:

1. **Before any `placements update`, ask in one message:**
   > Before I change this placement: does any audience in **`<placement title>`** run an A/B test
   > right now? I can't see A/B tests from the CLI, and saving the placement from here would stop
   > the test with no winner. You can check on the placement's page in the Adapty dashboard.
2. **No test** → continue.
3. **A test, "not sure", or no answer** → do not write. Give the user the exact change to make in
   the dashboard (which audience, which segment, which paywall or flow, which position), where
   the test keeps running. Creating the segment through the CLI is still fine; only the placement
   write is off.

"Go ahead", "don't check back", or an earlier yes to the before/after table is not an answer to
this question. An unattended run never writes a placement.

## How you sound

- **"I" for what you do, "you" for what they do.** Lead with who will see what, end on one next step.
- **Name users, not ids.** "Users in Germany and Austria", "users on 2.0.0 or later". Ids appear
  only inside a command.
- **Before a write, show the placement's audiences before and after**, as a table in priority
  order: segment, what it serves. That table is the confirmation.
- Bold at most one thing per paragraph. Reply in the user's language.

## The CLI

Resolve `$ADAPTY` once, as the other Adapty skills do: `adapty --version`; if it lacks the command
you need, `npm i -g adapty@latest`, falling back to `npx --yes adapty@latest`. In `zsh` a
multi-word `$ADAPTY` needs `setopt shwordsplit`. Write commands out for the user with a literal
`adapty`.

`segments list` and `segments get` are old. **`segments create` and `segments update` ship after
0.9.3** — probe `$ADAPTY segments create --help` before planning a write. Two refusals are not flag
problems, so do not retry with variations:

- `unknown command` → the installed CLI predates the command; re-resolve `$ADAPTY`.
- `405` → the server has not opened segment writes yet. Build the segment in the dashboard
  (https://adapty.io/docs/segments), read its id with `segments list`, and continue at step 5.

| Command | What it does |
|---|---|
| `segments list --app <app> --page-size 100` | `id`, `title`, `description` only — no filters |
| `segments get --app <app> <id> --json` | adds `filters[]`, `profile_count`, `refresh_in_progress` |
| `segments create --app <app> --title <t> --filter <f> [--filter <f>…] [--description <d>]` | filters are ANDed |
| `segments update --app <app> <id> --title <t> --filter <f> […]` | **replaces the whole segment** |
| `placements list --app <app> --page-size 100 --json` | the default page is 20, so a short list hides placements |
| `placements get --app <app> <id> --json` | `title`, `developer_id`, `audiences[]` |
| `placements update --app <app> <id> --title <t> --developer-id <d> --audiences '<json>'` | **replaces every audience, and stops any A/B test on it** (see above) |

`--app` is the **Adapty** app UUID from `$ADAPTY apps list`. A filter is `field:OPERATOR:value[,value…]`:
`IN`, `NOT IN`, `>`, `>=`, `<`, `<=`, `BETWEEN`, or `field:IS NULL` / `field:IS NOT NULL` with no
value. There is no `=`: equality is `IN` with one value (`ip_country:IN:DE`). For a typed or
nested value, pass one JSON object:
`'{"field_name":"age","operator":">","value_list":[18]}'`. Numbers go in plain (`age:>:18`).

## Field names and values come from this table, never from a guess

The server refuses an unknown field name and accepts **almost any value** for a known one: a
misspelled state, a lowercase country, `pt-BR`, `female` all save a segment that matches nobody,
with no error. Only `paid_access_level` is checked (it must be a UUID). So take the name and the
value format from here. Labels are the dashboard's.

| `field_name` | Dashboard label | Values |
|---|---|---|
| `ip_country` | Country | ISO alpha-2, uppercase: `DE` |
| `store_country` | Country from store account | ISO alpha-2, uppercase |
| `locale` | Language | 2-letter ISO 639-1: `pt`, never `pt-BR` |
| `app_version` | App version (current) | strict SemVer: `2.0.0`, never `2.0` or `02.1.0` |
| `app_version_on_install` | App version (on install) | strict SemVer |
| `os` | OS | a version, compared as one: `17` |
| `platform` | Platform | `iOS`, `macOS`, `iPadOS`, `visionOS`, `Android` |
| `device` | Device | the model as stored: `iPhone 13` |
| `store` | (store) | `app_store`, `play_store`, `stripe`, `paddle`, `adapty` |
| `subscription_state` | Calculated subscription state | `subscribed`, `active_trial`, `auto_renew_off`, `subscription_cancelled`, `trial_cancelled`, `never_subscribed`, `billing_issue`, `grace_period` |
| `paid_access_level` | Paid access level | the access level's **UUID** from `access-levels list`, never its name |
| `subscription_product_id` | Subscription product | the Adapty product UUID from `products list` |
| `subscription_expiration_date` | Subscription expiration date | `YYYY-MM-DD` |
| `total_revenue_usd` | Calculated total revenue USD | a number |
| `age` | Age | a number |
| `gender` | Gender | `f`, `m`, `o` |
| `customer_user_id` | App User ID | usually `IS NULL` / `IS NOT NULL` |
| `install_date`, `created_at` | Installation date, Creation date | `YYYY-MM-DD` |
| `install_date_relative`, `created_at_relative`, `subscription_expiration_date_relative` | the same, as a relative range | `now-7d`, `now-3M`; comparisons only, no `BETWEEN` |
| `status` | Attribution: Status | `organic`, `non_organic`, `unknown` |
| `source` | Attribution: Source | `adjust`, `branch`, `apple_search_ads`, `appsflyer`, `custom` |
| `channel`, `campaign`, `ad_group`, `ad_set`, `creative` | Attribution: Channel, Campaign, Ad Group, Ad Set, Creative | the raw strings the attribution sends; for Apple Search Ads they are Apple ids, so route to `ads-manager` |

**Custom attributes** are `attributes__<key>@string` (`IN`, `NOT IN`, `IS NULL`, `IS NOT NULL`) or
`attributes__<key>@float` (comparisons too). The key is the one the app sets through the SDK, and
the suffix must match its type: a value stored with the other type counts as not set. No command
lists an app's keys, so take the key from, in order: an existing segment's `filters[]`
(`segments list`, then `segments get --json`), the app's code, or the user. Never guess a key.

**Last seen** is in the dashboard but not in this list: the server refuses it. A segment on it is
made in the dashboard.

## Ambiguous requests — ask, with the options

These look like one attribute and are two, or have a format that fails silently. Ask before
building, and say what each option means. Labels are the dashboard's (https://adapty.io/docs/segments).

| The user says | The choice | Why it matters |
|---|---|---|
| "users in Germany" | **Country** (latest IP, refreshed weekly, moves with VPNs and travel) or **Country from store account** (iOS 13+ only) | Pricing and legal copy usually want the store country |
| "on version 2.0", "updated to 2.0" | **App version (current)** or **App version (on install)** | "On install" silently drops everyone who upgraded |
| any app version | Strict SemVer: `2.0.0`, never `2.0` or `02.1.0` | An invalid version matches nobody, with no error |
| "never paid", "non-payers" | Which signal: total revenue, subscription state (`never_subscribed`), paid access level | Comparisons and `NOT IN` skip profiles where the attribute is unset, and filters in one segment are ANDed — so "zero **or** unset" is two segments in two audiences, never one segment with both filters |
| a language | 2-letter ISO 639-1 (`pt`, not `pt-BR`) | Extended locales match nobody |
| two conditions | Both (one segment, two filters) or either (two segments, two audiences) | One audience holds one segment, so "or" is two entries |

## Workflow

1. **Read the placement.** `placements list --page-size 100 --json`, match `developer_id`, then
   `placements get --json`. Record `title`, `developer_id`, and every audience. Ask the A/B-test
   question now, in the same message as the step 2 questions, so a "yes" is known before you plan
   a write. Note the
   `content_type` the entries carry: it is fixed for the placement. Asked to serve a flow at a
   `paywall` placement, or the reverse? The placement cannot; stop and route to
   `migrate-placements`.
2. **Translate the request** into filters with the table above. Ask every question it raises in
   one message.
3. **Reuse before create.** `segments list --page-size 100`, then `segments get --json` on any
   title that could match, and compare `filters[]`. A segment with the same filters is the one to
   use — say so. Never create a twin.
4. **Create** if nothing matches, with a title that says who is in it ("Germany & Austria, store
   country"). `profile_count` is `0` on creation and fills in later, so it proves nothing yet.
5. **Place the new audience directly before the default.** That is the only position where
   nobody who matches an existing segment changes what they see. If the request means the new
   audience should win over an existing one ("instead of what they see now", a user who could be
   in both), **name the overlapping segments and ask which should win**. Renumber priorities
   `0…n` with the default last.
6. **Build every entry with its `content_type`** and the matching id: `{"content_type":"paywall",
   "paywall_id":…}` or `{"content_type":"flow","flow_id":…}`, plus `segment_ids` (one id, or `[]`
   for the default) and `priority`. The CLI refuses an entry without them before sending.
7. **Confirm with the before/after table**, once the user has said the placement runs no A/B
   test. Then write all entries back with one `placements update`,
   reusing `title` and `developer_id` exactly.
8. **Verify** with `placements get --json`: same entries, your new one where you put it, one
   default, last.
9. **Close** with who sees what now, and two facts: the segment's count fills in after a delay
   (new profiles and attribute changes reach Adapty with a delay), and any attribute the app
   must send is `adapty-integration`'s job.

## Never

- **Never run `placements update` without the user's answer that the placement runs no A/B test.**
  The read cannot show one, and the write stops it for good.
- **Never change what a user outside the request sees without their explicit answer** — not when
  the user said "go ahead", not when the order "seems right". Moving a new audience above an
  existing one is exactly that change.
- **Never write a placement without passing back every audience you read.** An entry you omit is
  an entry you deleted.
- **Never delete an entry the CLI refuses when that entry came from `placements get`.** A refusal
  such as `content_type is required and must be "paywall" or "flow"` on an entry you did not write
  means your CLI is older than the API, and the entry is most likely a running A/B test. Re-resolve
  `$ADAPTY` once and retry the same list. If it still refuses, send the change to the dashboard.
  Deleting the entry makes the write go through and stops the test.
- **Never guess a field name, a custom attribute's key, or a value format.** Take them from the
  table above; the server accepts a wrong value and the segment matches nobody.
- **Never put a flow id in `paywall_id`**, or an entry without `content_type`.
- **Never `segments update` with only the filter you changed** — it replaces the segment; read it
  and pass back every filter you keep. A segment can serve several placements and A/B tests, so
  name that before editing a shared one; a new segment is often the safer change.
- **Never use `placements --paywall-id`.** It rewrites every audience into one default.

## Rationalizations

| What the agent told itself | What is actually true |
|---|---|
| "The user said to go ahead without checking back, so I run the writes without asking and send a summary message after." | Their yes covers their request. It does not cover moving VIP users off the VIP paywall, which is what putting the new audience first does to anyone in both segments. |
| "I put the new segment at priority 0 so DE/AT users reliably get the cheaper paywall." | Priority 0 also outranks every existing segment. "Before the default" is the position that changes nobody else. |
| "If the server rejects a field name or value, it reports one error per field. I'd fix the names from that error and re-run, without guessing further." | A wrong name is refused; a right name with the wrong meaning is accepted. Read the name off an existing segment. |
| "`app_version`, with value `2.0`." | Versions are strict SemVer. `2.0` matches nobody, with no error. Write `2.0.0`, and settle current versus on-install first. |
| "`placements get` returned two audiences, I passed back both plus mine, so nothing is lost." | An audience running an A/B test is not in the response at all. Passing back everything you read still deletes it and ends the test. |
| "I put the flow id in the audience's `paywall_id` field. The reference covers only paywalls" | Every entry carries `content_type`, and a flow entry carries `flow_id`. The placement's own entries show which one it takes. |

Quotes are verbatim from baseline runs without this skill (2026-10-12).

## Red Flags — STOP

- A new audience with a lower `priority` number than an existing segment's, and no answer from the
  user about who wins
- An `--audiences` array with fewer entries than `placements get` returned, plus one
- A `placements update` with no answer from the user to the A/B-test question
- A `field_name` or a value not in the table, or a custom attribute key nobody read off a segment, the code or the user
- An app version with fewer than three parts
- An entry from `placements get` removed after the CLI refused it
- "Country" in a filter and no answer to "IP or store account?"
- `placements list` without `--page-size 100`
- A planned write to a placement whose priorities skip a number, or that has no `segment_ids: []` entry

## Anything not covered here

`$ADAPTY <topic> <command> --help` for flags on the installed version; the `adapty-docs` skill for
any dashboard behaviour. Do not guess a flag, a field name, or a URL.
