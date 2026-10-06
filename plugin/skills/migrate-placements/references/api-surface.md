# The placement and publish surface

What the `placements` and `flows` API actually does, established by running the commands against
production rather than by reading prose about them. Where a claim rests on the CLI's source instead
of on a call, it says so.

**Error strings are quoted exactly. An agent routes on them, so a paraphrase here is a bug.**

Two things are still open and are named as open, not smoothed over — see
[what is still unverified](#what-is-still-unverified).

## Publishing, and the draft-attach gate

**A command's presence is not a version question, and it does not move monotonically.** `flows
publish` and `flows update` shipped in `0.8.3-beta.0`, were **absent from the `0.8.3` release**, and returned
after it — so *"at least 0.8.3"* admits a build without the command, and a numeric floor is not a
usable test. Phase 1 probes with `flows publish --help` for that reason.

**A placement cannot be attached to a draft flow.** The backend's own wording, on a `placements
create` naming a flow whose status is `draft`:

```
ApiError: Flow must be published before placing in a placement.
Code: validation_error
```

That is reached on the **create** path. On the *update* path the type check fires first, so it is
unreachable there. Hence the phase ordering: publish, poll
until `published`, then create the placement.

**The CLI now replaces that message, so do not route on the backend text.** `placements
create|update` match the backend string themselves and print their own, exiting **2**:

```
Cannot attach a draft flow to a placement — publish it first.
Publish:  adapty flows publish --app <APP> <FLOW>
  • Builder UI: https://app.adapty.io/flows/<FLOW>/builder
  • Adapty flows agent skill: https://adapty.io/docs/flow-generator-skill
```

The backend sentence is **not** in that output, so a check for *"Flow must be published before
placing in a placement"* matches on the older build and nothing on the newer one. Route on
**`Cannot attach a draft flow`** and treat the backend wording as the legacy form. Any other
refusal is relayed unchanged — the mixed-audience and type-change errors below still read exactly
as quoted.

**`flows publish` is asynchronous.** The status is `publishing`, never `published`. A run that
reports the flow as live off that response is reporting a state nobody observed. On a 400
(`validation_error`) it exits **1** with remediation links, one of which is
https://adapty.io/docs/flow-generator-skill.

Its success output grew in a later build and now hands you the next two commands:

```
Publishing started — status: publishing. This is asynchronous; the flow is NOT published yet.
Check progress:  adapty flows get --app <APP> <FLOW>   (wait for status 'published' or 'publication_failed')
If it fails:     adapty flows config get --app <APP> <FLOW>   (shows why)
```

Two things follow. The older single line — `Publishing started — status: publishing.` — is a
**prefix** of the longer one, so a prefix match survives both builds and an equality match does not.
And all three lines are **suppressed under `--json`**: a `--json` publish returns the flow object
alone, so the poll is on you either way.

**A failed publication is readable from the CLI.** `flows config get`'s envelope carries
`publication_status`, `publication_error` and `transform_error` beside the config, and
`transform_error` is the transform service's own objection to the attempt. They are passthrough
fields: where the API does not send them they are absent, which is not an error. `transform_error`
is a raw string — a JSON issues payload or a summary — and there is **no CLI helper to parse it**
(the type's own comment names a `parseFlowPublicationError` that does not exist in the CLI), so
quote it rather than deriving a cause of your own. `flow-generator` owns this diagnosis; this skill
only needs it when a phase-5 publish lands on `publication_failed`.

## Why every migration is a create

**A placement's content type cannot be changed after creation.** Against a server that accepts flow
audiences on `create`:

```
$ placements update --app <APP> <PLACEMENT> --title Main --developer-id main \
    --audiences '[{"content_type":"flow","flow_id":"<FLOW>","segment_ids":[],"priority":0}]'
ApiError: Placement type can not be changed.
Code: validation_error
```

**This is not a deployment gap.** A server with the placement-audience union fully deployed still
refuses it. So in-place conversion is impossible at the backend, not merely unimplemented in the
CLI, and every "migrate" operation is a `placements create`.

Two consequences worth stating separately:

- **Anything promising in-place conversion is wrong, including test plans.** `placements update`
  into a different content type is refused by the backend; do not design around it as though a
  future flag will land, and report it if you find it documented as working.
- **A wrongly-created placement is permanent.** The docs, verbatim: *"Placement IDs are unique
  across every placement in the app, whatever the type, so the same ID can't serve a flow in one
  place and a paywall in another."* ([placements.md](https://adapty.io/docs/placements.md)) So a
  new flow placement cannot reuse the paywall placement's ID, and placement delete is out of
  scope — there is no undo for a created placement. Every proposed ID is pre-checked against
  `placements list` and approved before anything is created.

## Finding a flow the user already has

**The dashboard converts a Paywall Builder paywall into a flow in one click**, and this skill has to
assume some of that has already happened. **Move to new builder**, on the paywall's own overview
page, recreates the paywall as a **draft** flow carrying its layout, its copy in every locale, and
its products with prices as variables ([Convert a paywall into a flow](https://adapty.io/docs/convert-paywall-to-flow.md)).
Adapty's own migration guidance is to convert rather than rebuild
([Migrate to flows](https://adapty.io/docs/migrate-to-flows.md)). Three facts from those pages line
up exactly with what this file measured, and are worth having in one place:

- the converted flow **does not take the paywall's placement**, and cannot take its ID either;
- it starts as a **draft**, so it is refused at attach until published;
- the paywall **stays live and unchanged**, which is what makes the whole migration additive.

`inventory` therefore reads two more paged lists, on by default:

| Read | Returns | Read for |
|---|---|---|
| `flows list` | `{id, name, status, updated_at}` | the flows that already exist, and their statuses |
| `paywalls list` | `{id, title, product_ids}` | the **titles** — an audience carries `paywall_id` and no name |

Both are `{data, meta.pagination}` behind the same `paginationFlags` as `placements list`, so both
default to **20 rows a page** and both go through the same exhaustion loop. Two paged reads whatever
the account size, against the one GET per placement already being spent.

**THE MATCH IS ON THE NAME AND NOTHING ELSE, because nothing else exists.** No field on a flow
records the paywall it was converted from, and no field on a paywall records the flow — there is no
back reference in either direction. So `match_existing_flows` compares normalized titles, reports
`exact` or `contains`, and never picks: the candidate goes to the user. Two failure directions, both
real and neither detectable:

- a name match can be a **coincidence** — hence proposal, never adoption;
- a **renamed** converted flow matches nothing, so an empty candidate list is not evidence that
  nothing was converted. Ask.

Matching is on **tokens, not substrings**. `main` is inside `Domain expert` and is not a name match;
a false candidate is worse than none, because the user is being asked to confirm the flow their
paying customers get served.

**Whether a paywall CAN be converted is not readable.** `PaywallDTO` is `{id, product_ids, title}` —
nothing says which builder made it — and **Move to new builder** appears only on legacy Paywall
Builder paywalls. So the skill describes the button and where to find it, and never asserts it is
there.

## Pagination

From `paginationFlags`, read off the flag declaration rather than the prose docs:

| | |
|---|---|
| `--page` | default **1** |
| `--page-size` | default **20**, max **100** |
| sent as | `page[number]` / `page[size]` |
| response carries | `meta.pagination {count, page, pages}` |

**The default of 20 is the trap.** One `placements list` call and a report of its length
under-reports the 150-placement app below by 130, with nothing in the output saying so —
`meta.pagination`
is there to be read, and a run that ignores it looks exactly like a run on a small app.
`migrate.py`'s `paginate()` owns this mechanically: it reads `pages` from page 1 and loops.

## Summary vs detail

**`placements list` returns `PlacementSummaryDTO` — `{developer_id, id, title}`, with no
`audiences`.** Only `placements get` returns `PlacementDetailDTO`, which carries `audiences?`.
There is no bulk read, so classifying N placements costs N GETs.

**`paywalls placements <paywall_id>` is un-paginated** — no `paginationFlags`, and `printList` is
called without pagination — and returns summaries only. It answers *which* placements use a
paywall; it does not carry the `segment_ids`, `priority` or `title` a write needs.

**And it is FILTERED, which limits it further than the missing fields do.** From the API source,
verbatim: *"Filtered to live (state=LIVE), paywall-typed
(content_type=PAYWALL), non-deleted placements."* So the reverse index **cannot find an inactive
placement at all** — a narrow "just these paywalls" run built on it silently sees only the live
ones, which is the wrong shape for a migration that may deliberately start with the inactive
placements. It also omits `is_active` by design (see below), so it cannot report what it filtered.

Cost for a 150-placement / 192-paywall app, which settles which primitive to enumerate on:

| Route | Calls | Yields what a write needs? |
|---|---|---|
| placement-first: `placements list` paged + N×`get` | 2 + 150 = **152** | **yes** |
| paywall-first: `paywalls list` paged + M×`paywalls placements` | 2 + 192 = 194, **then still** N×`get` | no |

**Enumerate placement-first and derive the paywall grouping by grouping on `paywall_id`.** The
reverse index is worth reaching for only on a narrow "just these paywalls" run, where M is small
and a full sweep is the wrong shape.

## The publishable floor

Measured with `flows config validate` (advisory, saves nothing) against the real transform service
in production, then with `flow-generator`'s `verify-config.py`:

| Config | `validate` | `verify-config.py` |
|---|---|---|
| `{"screens":[],"locales":[]}` — the CLI's **own example** | `Invalid flow input` | — |
| `{}` | `Invalid flow input` | — |
| one **empty** screen, no theme | `Generated JSON failed schema validation` | — |
| one **empty** screen, **full** theme | same | — |
| one `text`, **no theme** (903 B) | **`valid: true`** | **ERROR** `font.preset not in theme.typography: ['body']` |
| one `text` + `bg`/`ink` + `body` preset (1,160 B) | **`valid: true`** | **OK** |

Two findings.

**A screen must contain at least one element, and the theme is not required to publish.** An empty
screen fails no matter how much theme it carries, and a themed screen with one `text` passes. The
message for the empty case is the location-free `Generated JSON failed schema validation`, which
names no field — so an agent authoring its own stub rediscovers this floor by bisection, every run.

**The themeless variant passes the service and fails our own checker**, on a `body` preset the theme
does not declare. That is the documented trust order doing its job rather than a contradiction: a
clean `validate` is a floor, not a proof. The shipped `references/stub-flow.json` is the last row —
the artifact that clears **both** gates. **Its size depends on how you serialize it:** `wc -c` on the
shipped file reads **1,160** bytes (compact separators, as written), and the same document
re-serialized with `json.dumps`' default spacing reads 1,290 — which is the figure the original
measurement notes carry. Same config either way; quote the one whose measurement you mean.

## content_type is read-asymmetric

**`content_type` on a read is the discriminator for the whole placement-audience capability.** A
server that omits it from an audience entry does not model the paywall/flow union, and a flow
audience written to that server comes back `audiences.0.paywall_id: Field required` — the API
rejecting the union, not a malformed request. Production includes the field, so that refusal means
*this deployment is behind*, never *the capability does not exist*. `is_active` shipped alongside it
and is a second signal for the same thing. **So probe rather than assume, and degrade on those exact
error shapes** — that is what makes the capability moving under this skill a fact change rather than
a redesign.

| | |
|---|---|
| `placements get` audiences, in production | **include** `content_type` |
| a server without the placement-audience union | **omits** it from each audience |
| every write (`create`, `update`) | **requires** it |

So a read cannot be assumed to be writable back unchanged — it depends on the server. `migrate.py`'s `normalize_audience()` derives
it from whichever id field is present (`paywall_id` → `paywall`, `flow_id` → `flow`) and refuses to
guess when there is neither.

**That normalization is a compatibility shim, not a permanent transform — and it is a no-op on
production today.** Keep it anyway: it is what makes the skill work against a deployment that is
behind, and it must accept both shapes rather than injecting unconditionally. Its absence is now
the thing that would be a bug, not its presence.

The CLI validates the field itself, before any request. `audienceEntryProblem` (**exit 2**, no
request sent): `content_type` is required and must be one of `{paywall, flow}`; a paywall entry
requires `paywall_id`, a flow entry requires `flow_id`. Reported as `--audiences[<i>]: <problem>`.

**Exit 2 no longer means "nothing was sent".** The draft-flow refusal above also exits 2, and that
one is a *rejected* request rather than a withheld one. Both are safe to retry after fixing the
cause, and neither created a placement — but read the message before you conclude which happened,
because the two need different fixes (edit the argv, versus publish the flow and re-run).

## `is_active` — the scope filter

**Read from the API source rather than owner-stated.** The source comment, verbatim:
*"`is_active` is the placement activation state (true=Live, false=Inactive), matching the
dashboard."*

| | |
|---|---|
| shape | `is_active: true \| false` |
| declared on | **both** `PlacementSummaryDTO` and `PlacementDetailDTO`, read from `placement.is_active` |
| meaning | the **placement's activation state** — Live / Inactive, the dashboard's own toggle |
| explicitly not | traffic-derived, and not "has an audience configured" |

**Do not build finer edge behaviour than *true = Live, false = Inactive*** — that is all the source
defines.

**It is present in production, on `placements list` as well as `placements get`** — a `list` row
comes back as `['developer_id', 'id', 'is_active', 'title']`. That is what makes the pre-GET filter
a real saving rather than a hope, and it is why `--scope active` genuinely filters instead of
falling back. A server that does not carry the field is behind, and the fallback below is what the
skill does there.

**`paywalls placements` OMITS `is_active` PERMANENTLY, BY DESIGN.** The source excludes it
explicitly, `model_dump(exclude={'is_active'})`, with the reason: *"these placements come from the
paywall latest-placement query, which does not annotate the activation state, so the entity would
carry the meaningless getattr default. It is exposed only on the placement list/retrieve reads,
whose queryset annotates it."*

**That makes the `unknown` bucket required rather than defensive.** It is the permanent shape of an
endpoint this skill uses, not a hedge against release timing that can be simplified away — one of
our own read paths will always return placements with no activation state, and collapsing `unknown`
into `inactive` would mark every one of them disabled. Keep the third bucket.

**The consequence that shapes `migrate.py`: absence is a THIRD state.** `select_scope` partitions
active / inactive / **unknown** and never collapses the third into the second. Reading absence as
`false` on a server that does not carry the field would filter an entire account out and report an
empty migration — a silent, total failure that looks like a clean result, and the same class of
error as reading an audience with no `content_type` as having no type. An all-unknown set under
`--scope active` therefore **falls back to every row and records that it did**.

**And the withheld count is reported every run, kept alongside the count kept.** If the field's real
semantics turn out narrower than the status above, a filter would skip placements that needed
migrating and the user would never see them — so `describe_scope` produces the exclusion count from
the same code that makes the exclusion, and `plan` carries it into `summary.scope`.

**What it buys, in the mechanism's own terms.** The field is **declared on both DTOs in the API
source** and `list` costs 2 calls; the audiences are **measured** to be only on `get`, which costs
one per placement. So filtering the `list` result **before**
the GET loop turns a 150-placement app with 30 active from `2 + 150 = 152` calls into `2 + 30 = 32`.
Filtering after the loop yields a byte-identical inventory and saves nothing, which is why the scope
is an argument to `inventory` rather than something applied to its output.

**One thing about the field is asserted by the source and not measured: what `false` means.** The
source says disabled, matching the dashboard's own toggle; nothing here establishes that a `false`
placement is untrafficked rather than merely switched off. Do not infer traffic from it.

### If a server carries it on `get` only

**Keep the partition and the reporting; move the filter after the GET loop; drop the call-saving
claim.** Only the *position* of the filter depends on the field being on `list`, and three of the
four things it feeds need **activity** rather than the pre-GET position:

| Consumer | Needs | Survives `get`-only? |
|---|---|---|
| the phase-4 three-way scope choice | activity | **yes** |
| the phase-6 stub exposure count | activity | **yes** |
| the rehearsal order | activity | **yes** |
| `2 + 150` → `2 + 30` | the field on `list` | **no** — the only casualty |

So `--scope` stays and keeps filtering; it just stops being a saving. Do not remove it, and do not
leave the arithmetic claim standing — a flag whose documentation promises a saving it cannot deliver
is worse than one that says plainly it only narrows the plan.

## Confirmation asymmetry

**`flows publish` has a full confirmation contract, and `placements create|update` have none.** That
is the measured asymmetry and it is stated without a theory attached: nothing here establishes what
publishing can or cannot be undone by, and there is no unpublish command to appeal to.

`confirmMutation`, which `flows publish` uses:

- `--yes` / `-y` proceeds.
- `--json` **or** a non-TTY stdin **refuses** with exit **2** — `Re-run with --yes to apply it
  without a prompt.` Fail-closed, so a headless run cannot hang.
- Otherwise it prompts `Apply? [y/N]` on **stderr**, so `--json` stdout stays parseable.
- A non-`y` answer exits **1** — `Cancelled, nothing was sent.`

`placements create` and `placements update` have **no prompt and no preview** at any verbosity.
Whatever argv you hand them is sent. And the warnings are on the wrong path: the **deprecated**
`--paywall-id` form prints two stderr warnings, including that it *"will rewrite all audiences on
this placement"*, while the **recommended** `--audiences` form prints none — even though
`placements update` requires `--title` and `--developer-id` and sets `audiences: null,
paywall_id: null` before filling one, i.e. it is a **full replace**.

Worth reporting to the CLI/API team alongside QA case C7.

## Blind spots in the reads themselves

**`placements get` SILENTLY OMITS an audience that is neither paywall nor flow.**
`PlacementDetailDTO.factory` appends only `PAYWALL` and `FLOW` entries; the source's own test
`test_factory_skips_content_that_is_neither_paywall_nor_flow` exercises it with
`PlacementContentType.AB_TEST`. So a placement carrying an A/B-test audience **reports fewer
audiences than it has**, and every count derived from that read — including this skill's — is short
by exactly the entries the DTO dropped.

**We cannot detect it, and saying so is the honest answer rather than inventing a check.** The read
is the only view we have; a placement with 3 audiences of which 1 is an A/B test is
indistinguishable from a placement with 2. Nothing in the response says an entry was skipped, so
there is no count to compare against and no flag to test. The only way to know is to look at the
placement in the dashboard.

**What follows for the migration, stated precisely.** This skill creates and never updates, so
nothing is destroyed and the source placement keeps its A/B-test audience serving. But the **new
flow placement would not carry that audience**, because the read never showed it — so the migration
is incomplete in a way the plan cannot show. Disclose it wherever audience counts are reported:
they are counts of what the API returned, not necessarily of what exists.

## What the write requires, and why we carry values verbatim

From the same source, the audience array a `placements create` must satisfy:

| Constraint | |
|---|---|
| `segment_ids` per entry | **at most one** — a `field_validator` refuses more (see the legacy trap below) |
| exactly one entry | must have `segment_ids=[]`, the default, and it must hold the **highest priority** |
| `priority` values | must be **unique** across the array |
| `segment_ids` values | must be **unique** across the array |

**This is the argument for carrying `segment_ids` and `priority` over verbatim rather than
normalising them.** A valid source placement already satisfies every row above, so copying the
targeting unchanged yields a valid target by construction — while any normalisation we invented
(renumbering priorities, reordering, filling a default) could break a constraint the source was
respecting, and would change who sees what. `to_flow_audience` therefore copies and does not think.

**The one exception, and it is the legacy trap: a multi-segment audience is READABLE and
UNWRITABLE.** The `field_validator` capping `segment_ids` at one entry is deliberately bypassed on
the read paths — `model_construct`, commented *"bypass the 1-segment cap so legacy multi-segment
rows survive read round-trips"* — so a legacy row reads back perfectly and is refused on write.
Carrying it verbatim, which is right for every other field, therefore produces an argv the API will
reject at the one irreversible command in the skill. `migrate.py` detects `len(segment_ids) > 1`,
emits **no `command`** for that placement, and reports it as work the user must resolve in the
dashboard — it does not split or drop a segment, because that is a targeting decision.

## What is still unverified

Stated as open rather than smoothed over, because the skill's phases rest on it. Each one needs a
**write** to settle, which is why none of them has been.

- **A successful `placements create` with a published flow.** It is the one call the whole migration
  depends on, and testing it is a real production write that leaves a permanent, undeletable
  placement. Unknown until then: the success payload shape, whether `content_type` comes back on the
  *response to a create* — it does come back on every audience entry a `placements get` returns, but
  that is a different call — and whether a duplicate `developer_id` is refused client-side or by the
  backend.
- **Whether `flows publish`'s route is live.** It was last observed answering `http_404`, before the
  placement-audience capability landed — and since that capability *has* landed, the 404 is a
  plausible casualty of the same deployment. So it must not be assumed in either direction. It
  cannot be settled by a read: publishing is a `POST`, and even the cheapest probe — `flows create`
  a throwaway, then publish it — leaves a flow row that **cannot be deleted**. So phase 1 probes
  with `--help` and phase 5 degrades, and a 404 there is something you **observed**, never something
  you expected.
- **Whether `flows update --name` works.** Last observed `Method "PUT" not allowed`
  (`method_not_allowed`), and untested since. Renaming stays a builder action.
- **Whether a `dirty` flow is attachable.** Only `published` is treated as safe. Two CLI author
  comments point the same way and neither settles it: `flow-help.ts` calls its marker *"the backend
  message when a placement tries to attach an **unpublished** flow"*, and
  `PlacementFlowAudienceEntryDTO` says *"The flow must be `published` (not draft)"*. A comment is
  weaker than a measurement, so the row stands.
