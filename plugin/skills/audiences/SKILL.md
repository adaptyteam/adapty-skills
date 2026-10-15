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
- **Starting, stopping or building an A/B test** — not in the CLI. The CLI reads the tests on a
  placement and keeps them (next section). For the rest, send the user to
  https://adapty.io/docs/add-audience-paywall-ab-test.

## A/B tests on a placement: the CLI reads and keeps them

`placements get` shows an audience that runs an A/B test as an entry of its own kind (CLI 0.9.6 is
the first release that does): `{"content_type":"ab_test","ab_test_id":…,"ab_test_title":…,
"segment_ids":[…],"priority":…}`, or `"flow_ab_test"` on a flow placement. Send it back in
`--audiences` exactly as read (`ab_test_title` is optional on a write). The audience serves the
test's running content, so a test entry is not something you build or edit here.

- **A shared test** (`cross_ab_test`, `flow_cross_ab_test`) runs across several placements and
  shows read-only. Send each such entry back **unchanged** and never add, edit or reorder one. The
  backend counts its priorities and its default audience **apart** from the regular ones, so both
  groups can hold priority 0 and a default. You add and reorder only regular audiences.
- **A write that only adds a segment audience or only changes priorities is safe.** The test keeps
  running with the same start time, so the table needs no test line.
- **A write that changes a test is not, and the table must say so.** Three writes do: a running
  test's audience is replaced by a paywall or flow, or is missing from the list; its audience gets
  other segments; or the list carries a test id the placement does not run now. In the
  before/after table, show each test by its **title** and add one line per test: "test X stops with
  no winner; Y starts" (a stopped test shows as Completed with no winner), or "test X starts again
  with a new start time". Then **wait for the user's answer**, and write only after they confirm
  that table.
- **Read again just before the write.** Run `placements get` once more. If the placement differs
  from the read the user saw, show the new before/after table and ask again. An unattended run
  stops there and reports; it does not write.
- **Put on an audience only the test id it already carries.** The one exception is a test the user
  names as still a draft, and the table then says "test X starts on <who>". Never put the id of a
  test that runs on another audience or placement: the backend would move that test.
- **An unattended run may write a placement when the table has no test line.** A test line with no
  answer from the user means no write: give the exact dashboard change instead (which audience,
  which segment, which paywall or flow, which position), where the test keeps running. Creating
  the segment through the CLI is still fine.

An older CLI (CLI 0.9.5 and older) refuses these entries on write (see Never below). Tell the user
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
| `placements update --app <app> <id> --title <t> --developer-id <d> --audiences '<json>'` | **replaces every audience, so send every entry back, test entries included.** Nothing in the CLI warns when the list stops, starts or moves a test: the table does (see above) |

`--app` is the **Adapty** app UUID from `$ADAPTY apps list`. A filter is `field:OPERATOR:value[,value…]`:
`IN`, `NOT IN`, `>`, `>=`, `<`, `<=`, `BETWEEN`, or `field:IS NULL` / `field:IS NOT NULL` with no
value. There is no `=`: equality is `IN` with one value (`ip_country:IN:DE`). For a typed or
nested value, pass one JSON object:
`'{"field_name":"age","operator":">","value_list":[18]}'`. Numbers go in plain (`age:>:18`).

## Field names come from evidence, never from a guess

The server rejects an unknown field name, which looks like a safety net and is not one: the
dangerous mistake is a **valid** name with the wrong meaning, and that one is accepted silently.
Take a field name from one of these, in order:

1. **Confirmed names:** `ip_country`, `install_date`, `age`, `total_revenue_usd`, and the
   attribution fields `campaign`, `ad_group`, `creative`.
2. **An existing segment that already filters on it.** `segments list`, then `segments get --json`
   on the candidates, and copy `field_name`, `operator` and the value format from `filters[]`. This
   is also how a custom attribute's name and type suffix are found.
3. **Neither:** ask the user to build **the segment they actually need** in the dashboard — not a
   throwaway one to copy a name from — then reuse it by id. If more segments on that attribute
   will follow, read the field name off it (step 2) and create the rest through the CLI. Never
   iterate guesses against the server.

## Ambiguous requests — ask, with the options

These look like one attribute and are two, or have a format that fails silently. Ask before
building, and say what each option means. Labels are the dashboard's (https://adapty.io/docs/segments).

| The user says | The choice | Why it matters |
|---|---|---|
| "users in Germany" | **Country** (latest IP, refreshed weekly, moves with VPNs and travel) or **Country from store account** (iOS 13+ only) | Pricing and legal copy usually want the store country |
| "on version 2.0", "updated to 2.0" | **App version (current)** or **App version (on install)** | "On install" silently drops everyone who upgraded |
| any app version | Strict SemVer: `2.0.0`, never `2.0` or `02.1.0` | An invalid version matches nobody, with no error |
| "never paid", "non-payers" | Which signal: total revenue, subscription state, paid access level | Comparisons and `NOT IN` skip profiles where the attribute is unset, and filters in one segment are ANDed — so "zero **or** unset" is two segments in two audiences, never one segment with both filters |
| a language | 2-letter ISO 639-1 (`pt`, not `pt-BR`) | Extended locales match nobody |
| two conditions | Both (one segment, two filters) or either (two segments, two audiences) | One audience holds one segment, so "or" is two entries |

## Workflow

1. **Read the placement.** `placements list --page-size 100 --json`, match `developer_id`, then
   `placements get --json`. Record `title`, `developer_id`, and every audience, A/B test and
   shared test entries included. Note the `content_type` the entries carry: it is fixed for the
   placement. Asked to serve a flow at a
   `paywall` placement, or the reverse? The placement cannot; stop and route to
   `migrate-placements`.
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
7. **Confirm with the before/after table.** It carries a test line when the write would stop,
   start or move a test (see above); wait for the answer. In an interactive run the user still
   confirms the table. Only an unattended run writes without a wait, and only when no test stops,
   starts or moves. Read the placement again (`placements get`); if it changed since the read the
   user saw, show the new table and ask again. Then write all entries back with one
   `placements update`, reusing `title` and `developer_id` exactly.
8. **Verify** with `placements get --json`: same entries, your new one where you put it, one
   default, last, and every test entry still there with its `ab_test_id` and segments.
9. **Close** with who sees what now, and two facts: the segment's count fills in after a delay
   (new profiles and attribute changes reach Adapty with a delay), and any attribute the app
   must send is `adapty-integration`'s job.

## Never

- **Never write a placement whose test would stop, start or move before the user has confirmed a
  table that names the test**, and never on a placement that changed since the read they saw.
- **Never put a test id on an audience that does not already carry it**, except a draft the user
  named. A test id of another audience or placement moves that test.
- **Never edit, reorder or drop a shared-test entry** (`cross_ab_test`, `flow_cross_ab_test`).
- **Never change what a user outside the request sees without their explicit answer** — not when
  the user said "go ahead", not when the order "seems right". Moving a new audience above an
  existing one is exactly that change.
- **Never write a placement without passing back every audience you read.** An entry you omit is
  an entry you deleted.
- **Never delete an entry the CLI refuses when that entry came from `placements get`.** A refusal
  such as `content_type is required and must be "paywall" or "flow"` on an entry you did not write
  means your CLI is older than the API (CLI 0.9.5 or older), and the entry is a running A/B test.
  CLI 0.9.6 and later, meeting a kind they do not know, say `this CLI does not know this audience
  kind; update the CLI`: the same cause and the same rule. Tell the user to update the CLI,
  re-resolve `$ADAPTY` once and retry the same list. If it still refuses, send the change to the
  dashboard. Deleting the entry makes the write
  go through and stops the test.
- **Never guess a field name, a custom attribute's spelling, or a value format.** See the three
  sources above.
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
- A write that stops, starts or moves a test, and no confirmed table that names it
- A `placements update` with no `placements get` just before it
- An `ab_test_id` in the array that no audience of this placement carried when you read it, except a draft test the user named
- A `field_name` that is not in the confirmed list and was not read off an existing segment
- An app version with fewer than three parts
- An entry from `placements get` removed after the CLI refused it
- A shared-test entry that differs from the one `placements get` returned
- "Country" in a filter and no answer to "IP or store account?"
- `placements list` without `--page-size 100`

## Anything not covered here

`$ADAPTY <topic> <command> --help` for flags on the installed version; the `adapty-docs` skill for
any dashboard behaviour. Do not guess a flag, a field name, or a URL.
