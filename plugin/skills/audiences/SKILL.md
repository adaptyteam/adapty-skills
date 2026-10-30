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
- **Starting, stopping, replacing or building an A/B test** → `ab-tests`. It owns the life of a
  regular paywall or flow test and shows the user the exact effect before each one-way step. This
  skill reads the tests on a placement and keeps them (next section); it never starts or stops one.
  Two requests from `ab-tests` are yours, not a hand-back:
  - **A segment for a test:** Workflow steps 2–4 only (translate, reuse, create). Return the
    segment's id and title, and read or write no placement.
  - **A row for a test to start on,** at a position below another audience: add the segment as a
    regular audience at that position, showing the content those users see now, so nobody's
    screen changes. The full workflow applies, its table included. Return; `ab-tests` starts the
    test on that row.

## A/B tests on a placement: the CLI reads and keeps them

`placements get` shows an audience that runs an A/B test as an entry of its own kind (CLI 0.11.0 is
the first release that does): `{"content_type":"ab_test","ab_test_id":…,"ab_test_title":…,
"segment_ids":[…],"priority":…}`, or `"flow_ab_test"` on a flow placement. Send it back in
`--audiences` exactly as read (`ab_test_title` is optional on a write). The audience serves the
test's running content, so a test entry is not something you build or edit here.

- **A shared test** (`cross_ab_test`, `flow_cross_ab_test`) runs across several placements and
  shows read-only. Send each such entry back **unchanged** and never add, edit or reorder one. The
  backend counts its priorities and its default audience **apart** from the regular ones, so both
  groups can hold priority 0 and a default. You add and reorder only regular audiences.
- **A write that adds or moves a row below every test row leaves the tests as they are.** A row
  added or moved above a test row takes the users that match both from that test: they leave the
  test. Say so and name the test in the table the user sees. Every test row goes back as read, so
  the start time stays.
- **A rename** (`placements update` with a new title) sends every audience row back exactly as
  read, test rows included.
- **A write that changes a test is not safe, and this skill does not make it.** Three writes do:
  a running test's audience is replaced by a paywall or flow, or is missing from the list; its
  audience gets other segments; or the list carries a test id the placement does not run now.
  Stopping a test belongs to `ab-tests` (`ab-tests stop` with `--winner`, `--other` or
  `--no-content`) and starting one to `ab-tests start`; each shows the user the exact effect
  first. Say so, hand the user to `ab-tests`, and come back for the placement write after the
  test has stopped (read the placement again then).
- **Read again just before the write.** Run `placements get` once more. If the placement differs
  from the read the user saw, show the new before/after table and ask again. An unattended run
  stops there and reports; it does not write.
- **Put on an audience only the test id it already carries.** Never put any other test id on an
  audience, a draft included: starting a test belongs to `ab-tests`. The id of a test that runs on
  another audience or placement would move that test.
- **An unattended run may write a placement when the write leaves every test as it is.** A write
  that would change a test is not made: report it and name the `ab-tests` step. Creating the
  segment through the CLI is still fine.

An older CLI (CLI 0.10.0 and older) refuses these entries on write (see Never below). Tell the user
to update the CLI, and re-resolve `$ADAPTY`, which fetches the latest; do not compare version
numbers.

## How you sound

- **"I" for what you do, "you" for what they do.** Lead with who will see what, end on one next step.
- **Name users, not ids.** "Users in Germany and Austria", "users on 2.0.0 or later". Ids appear
  only inside a command.
- **Before a write, show the placement's audiences before and after**, as a table in priority
  order: segment, what it serves. That table is the confirmation. Show an A/B test by its title,
  never its id.
- Bold at most one thing per paragraph. Reply in the user's language.

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

**A command with no tool, and a script that runs `$ADAPTY`, need the CLI** (`feedback` and
`segments create` have no tool). Run that step with the CLI when it is ready. Otherwise skip the
feedback note without a word, and for any other step say it needs the CLI and offer to set it up.

**When a call fails one way,** a read may run once the other way if that way is ready. After a
write fails or times out, read the state again the way that wrote; never repeat the write the
other way.

**Neither ready:** ask which one to set up, the one this skill prefers first, then give only that
one's steps. Use your question tool if you have one; otherwise ask in one message with numbered
options.

- **The CLI:** run this skill's CLI resolution, then `adapty auth login`, which opens the browser for
  the user's sign-in. The Claude app also needs Adapty's domains allowed first:
  https://adapty.io/docs/developer-cli-cowork.md
- **MCP:** the server is `https://mcp.adapty.io/mcp`, and the user signs in in the browser.
  - Claude Code: `claude mcp add --transport http --scope user adapty https://mcp.adapty.io/mcp`,
    then `/mcp`, pick `adapty`, **Authenticate**.
  - Codex CLI: `codex mcp add adapty --url https://mcp.adapty.io/mcp`, then
    `codex mcp login adapty`.
  - The Claude app: Settings → Connectors → **Add custom connector**, with the URL above.
  - Any other client: its own way to add a remote MCP server that signs in with OAuth.

  If the tools do not appear in this session, the user starts a new one: say so and stop.

Example of the question's shape, not words to copy:

> I can reach your Adapty account in two ways. Which one should I set up?
> 1. The Adapty CLI (better for this): I install it, and you sign in once in the browser.
> 2. The Adapty MCP server: you add it to your AI tool and sign in; nothing to install.

**This skill prefers the CLI:** `segments create` and `segments update` have no tool, and a
new segment is most of its work. With MCP only, say so in one line and offer the CLI; on a no,
go on over MCP, and build a new segment in the dashboard the way the `405` line in "The CLI"
says.

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
| `placements get --app <app> <id> --json` | `title`, `developer_id`, `audiences[]` (A/B test entries included) |
| `placements update --app <app> <id> --title <t> --developer-id <d> --audiences '<json>'` | **replaces every audience, so send every entry back, test entries included.** Nothing in the CLI warns when the list would stop, start or move a test: keep every test entry as read (see above) |

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
   `placements get --json`. Record `title`, `developer_id`, and every audience, A/B test and
   shared test entries included. Note the `content_type` the entries carry: it is fixed for the
   placement. Asked to serve a flow at a `paywall` placement, or the reverse? The placement
   cannot; stop and route to `migrate-placements`.
2. **Translate the request** into filters with the table above. Ask every question it raises in
   one message.
3. **Reuse before create.** `segments list --page-size 100`, then `segments get --json` on any
   title that could match, and compare `filters[]`. A segment with the same filters is the one to
   use — say so. Never create a twin.
4. **Create** if nothing matches, with a title that says who is in it ("Germany & Austria, store
   country"). `profile_count` is `0` on creation and fills in later, so it proves nothing yet.
5. **Place the new audience directly before the regular default.** That is the only position where
   nobody who matches an existing segment changes what they see. If the request means the new
   audience should win over an existing one ("instead of what they see now", a user who could be
   in both), **name the overlapping segments and ask which should win**. Renumber the regular
   priorities `0…n` with the default last, test entries included (a priority change alone keeps a
   test running). Leave every shared-test entry exactly as read.
6. **Build every entry with its `content_type`** and the matching id: `{"content_type":"paywall",
   "paywall_id":…}` or `{"content_type":"flow","flow_id":…}`, plus `segment_ids` (one id, or `[]`
   for the default) and `priority`. The CLI refuses an entry without them before sending. An A/B or
   shared test entry goes back as read.
7. **Confirm with the before/after table**, each test entry shown by its title, and a test that a new row above it takes users from marked in the table. An interactive run
   waits for the user's yes; only an unattended run writes without a wait, and only when every
   test entry goes back as read. Read the placement again, then write all entries back with one
   `placements update`, reusing `title` and `developer_id` exactly.
8. **Verify** with `placements get --json`: same entries, your new one where you put it, one
   default, last, and every test entry still there with its `ab_test_id` and segments.
9. **Close** with who sees what now, and two facts: the segment's count fills in after a delay
   (new profiles and attribute changes reach Adapty with a delay), and any attribute the app
   must send is `adapty-integration`'s job.

## Never

- **Never write a placement that would stop, start or move a test.** That is `ab-tests`. Never
  write on a placement that changed since the read the user saw.
- **Never put a test id on an audience that does not already carry it.** Starting a test is
  `ab-tests`; the id of a test that runs elsewhere moves that test.
- **Never edit, reorder or drop a shared-test entry** (`cross_ab_test`, `flow_cross_ab_test`).
- **Never change what a user outside the request sees without their explicit answer** — not when
  the user said "go ahead", not when the order "seems right". Moving a new audience above an
  existing one is exactly that change.
- **Never write a placement without passing back every audience you read.** An entry you omit is
  an entry you deleted.
- **Never delete an entry the CLI refuses when that entry came from `placements get`.** A refusal
  such as `content_type is required and must be "paywall" or "flow"` on an entry you did not write
  means your CLI is older than the API (CLI 0.10.0 or older), and the entry is a running A/B test.
  CLI 0.11.0 and later, meeting a kind they do not know, say `this CLI does not know this audience
  kind; update the CLI`: the same cause and the same rule. Tell the user to update the CLI,
  re-resolve `$ADAPTY` once and retry the same list. If it still refuses, send the change to the
  dashboard. Deleting the entry makes the write go through and stops the test.
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
| "I put the flow id in the audience's `paywall_id` field. The reference covers only paywalls" | Every entry carries `content_type`, and a flow entry carries `flow_id`. The placement's own entries show which one it takes. |

Quotes are verbatim from baseline runs without this skill (2026-10-12).

## Red Flags — STOP

- A new audience with a lower `priority` number than an existing segment's, and no answer from the
  user about who wins
- An `--audiences` array with fewer entries than `placements get` returned, plus one
- A placement write that stops, starts or moves a test
- A `placements update` with no `placements get` just before it
- An `ab_test_id` in the array that no audience of this placement carried when you read it
- A `field_name` or a value not in the table, or a custom attribute key nobody read off a segment, the code or the user
- An app version with fewer than three parts
- An entry from `placements get` removed after the CLI refused it
- A shared-test entry that differs from the one `placements get` returned
- "Country" in a filter and no answer to "IP or store account?"
- `placements list` without `--page-size 100`

## Anything not covered here

`$ADAPTY <topic> <command> --help` for flags on the installed version; the `adapty-docs` skill for
any dashboard behaviour. Do not guess a flag, a field name, or a URL.
