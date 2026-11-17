# Placements: the evidence behind phase 6

The procedure comes first, below. The rest of this file holds the facts it rests on,
so the entry point does not carry a caveat an agent cannot act on at that step.

**Everything here holds against the default production API** — no `ADAPTY_API_URL`
override. Error strings are quoted exactly, because an agent routes on
them and a paraphrase is a bug.

## Attaching a flow to a placement: the procedure

**A published flow reaches nobody until a placement points at it.** The placement's **developer
ID** is the string the app fetches with, so publishing is the middle of the chain and not the end:
config → publish → placement → the app's call site. Offer this whenever a flow reaches
`published`. Never run it unasked — a placement cannot be undone.

**Three ways in.** You published it and polled to `published`; the user says they published it, in
the builder most likely; or this is where the conversation *starts* — then phase 1 has already sent
you here and phases 2-5 have no work to do.

**Verify the status yourself, whoever published it.** `flows get <FLOW_ID> --app <APP_UUID>` must
read `published`; `publishing` means poll, and anything else means it is not attachable yet.

**Then read the placements before proposing one** — one call answers both questions, whether this
location already has a placement and whether the ID you would propose is free:

```bash
$ADAPTY placements list --app "$APP" --page-size 100 --json    # the default page size is 20
```

Each placement's `type` is `flow`, `paywall` or `onboarding`. A `null` `type` (a placement made without
one) leaves it to `placements get` on the candidate: the `content_type` of its audiences.

| What `list` shows | What you do |
| :--- | :--- |
| nothing for this location | `placements create` with a new developer ID |
| a **flow** placement that should now point at this flow | `placements update` — it rewrites **every** audience, so pass back the ones you are keeping, A/B test entries (`flow_ab_test`) and shared ones (`flow_cross_ab_test`) exactly as `placements get` returned them. A write that replaces a running test, for instance this flow on the default audience a test holds, **stops that test**, and a placement write does not do that: route it to the **`ab-tests`** skill (`ab-tests stop`, which shows the user the exact effect first), then write the placement and read it again just before (changed: show the before/after table and ask again; unattended: stop and report). No answer → the change goes in the dashboard |
| a **paywall** or **onboarding** placement, even an unused one | **Nothing.** The type is fixed at creation and the write is refused. Propose a different ID and say why |
| a **flow** placement that already points at this flow, and *"nothing shows up in the app"* | Read whether anyone has started it, below, before sending them on |
| a placement where only **some** users should get this flow — a country, a version, a segment | The **`audiences`** skill. It adds a segment audience beside the existing ones without changing what anyone else sees |
| the user wants to **test this flow against another** (an A/B test: "split traffic", "run it 50/50", "start the test", "stop the test") | The **`ab-tests`** skill. It creates the test as a draft and starts, stops or replaces it only after the user sees the exact effect. Never start or stop a test with a `placements update` |

**When a placement already points at this flow and nothing shows up, read who started it** over the
last seven days, to today:

```bash
$ADAPTY flows metrics get "$FLOW" --app "$APP" --based-on placement \
  --date-from <seven days ago> --date-to <today> --date-type purchase_date --json
```

`unique_profiles_views` on a placement's node is how many users started the flow there; it updates
every few minutes, and the dates are required. Viewers on the placement the app fetches: the app
shows the flow, so ask what the user sees, on which build, and which audience they fall in. None:
the app does not fetch or render that placement yet, or the user is outside its audiences; the
app side is **`adapty-integration`**'s, with the developer ID. When `flows metrics --help` says the
command does not exist, skip this read and send them on the same way.

**The ID needs an explicit yes, and this is the fourth fixed block.** It is irreversible in a way
the phase-5 write is not: unique across every placement in the app whatever its type, no rename, no
delete from the CLI.

> Ready to point a placement at **`<flow name>`** (`<flow-id>`, `published`).
>
> - Developer ID: **`<id>`** — the string your app will fetch with.
> - Placement: `<new, titled "…">` / `<existing "…", now pointing at <what>>`
> - **Permanent.** IDs are unique across every placement in the app whatever its type, cannot be
>   renamed, and there is no delete from the CLI — a wrong one is spent.
>
> Create it?

On their yes, one call:

```bash
$ADAPTY placements create --app "$APP" --title "<Title>" --developer-id "<id>" \
  --audiences '[{"content_type":"flow","flow_id":"'"$FLOW"'","segment_ids":[],"priority":0}]'
```

The flow form of `--audiences` is the normal path — accepted against production. Every refusal,
which of them is yours to fix, the `update` variant and the dashboard fallback:
[placements.md](placements.md).

**Then hand the ID over and stop.** Past the custom-tag call site in phase 5, this skill does not touch app code:

> **Live at `<developer-id>`.** https://app.adapty.io/placements/flows/`<PLACEMENT_UUID>`
>
> Nothing in your app changes yet — it still has to fetch this placement and render what comes
> back. The **`adapty-integration`** skill owns that end: give it this developer ID and it wires
> the fetch and the rendering into your call sites.

**That link takes the placement's UUID, not its developer ID** — the two are different fields and
only the UUID routes. `placements create` prints it as `id`. The middle segment is the placement's
*type*, so a flow placement is `/placements/flows/…` and a paywall one would be
`/placements/paywalls/…` ([placements.md](placements.md)).

## Why the flow audience is the normal path

A placement audience entry is a union: either a paywall entry carrying `paywall_id`, or a flow
entry carrying `flow_id`. That union shipped to the API late, and a server that predates it models
an audience as paywall-only and refuses the flow form with
`audiences.0.paywall_id: Field required`.

**Production models the union, and the read-only discriminator is `content_type`.** A server
without the union omits `content_type` from every audience entry it returns; a server with it
includes the field. Every entry read back across several apps carries it:

```json
{"segment_ids": [], "priority": 0,
 "content_type": "paywall", "paywall_id": "…"}
```

`is_active`, declared in the same rollout, is present on both `placements list` and `placements
get` — a second, independent confirmation.

So the flow form is the expectation and the refusal is the edge case. It can still be real on an
older or self-hosted deployment, which is why phase 6 routes on it rather than assuming.

**What this does not settle:** whether `flows publish`'s route is live. That needs a `POST`, and
the cheapest safe probe — `flows create` a throwaway, then publish it — leaves a flow row that
cannot be deleted. So the publish half stays behind phase 5's probe-and-degrade rule and is not
claimed here either way.

## The two write commands

Both take `--audiences` as a JSON array, both require `--title` and `--developer-id`, and both
validate entries locally before sending anything.

```bash
# new placement
$ADAPTY placements create --app "$APP" --title "<Title>" --developer-id "<id>" \
  --audiences '[{"content_type":"flow","flow_id":"'"$FLOW"'","segment_ids":[],"priority":0}]'

# an existing FLOW placement, repointed
$ADAPTY placements update --app "$APP" <PLACEMENT_UUID> --title "<Title>" --developer-id "<id>" \
  --audiences '[{"content_type":"flow","flow_id":"'"$FLOW"'","segment_ids":[],"priority":0}]'
```

**`update` rewrites every audience on the placement.** There is no partial edit, so an entry you do
not pass is an entry you deleted — read the placement first and pass back the ones you are keeping.
A placement with segment-specific content is where this costs someone real work.

**Pass every A/B test entry back as read.** `placements get` shows an audience that runs a test as
`{"content_type":"flow_ab_test","ab_test_id":…,"ab_test_title":…,"segment_ids":[…],"priority":…}`
(CLI 0.11.0 is the first release that does), and a test shared across placements as
`flow_cross_ab_test`, read-only. Send each back unchanged; an entry you leave out is a test you
stopped. Put on an audience only the test id it already carries, never the id of a test that runs
elsewhere (the backend would move it).

**A write that replaces a running test stops it, and a placement write is not how a test stops.**
That is the case when the flow goes on an audience that holds a test, when a test's audience is
missing from the list, and when a test's audience gets other segments. Nothing in the CLI warns
about it. Route it to the `ab-tests` skill: `ab-tests stop` (with `--winner`, `--other` or
`--no-content`) shows the user the exact effect and waits for the yes. Write the placement after
the test has stopped, and read it again just before the write: if it changed since the read the
user saw, show the new before/after table and ask again (an unattended run stops and reports). No
answer means the change is made in the dashboard instead. A segment audience added or moved above a
test's audience takes the users that match both from that test; below it, the test is not
touched. Either way every test row goes back as read. Starting, stopping or replacing a test on purpose
belongs to the `ab-tests` skill.

**Never `--paywall-id`.** It is deprecated in favour of `--audiences` (the CLI prints a warning to
stderr), and on `update` it carries a second warning worth quoting: it *"will rewrite all audiences
on this placement … If the placement has segment-specific paywalls, they will be replaced by a
single default audience."*

## Every refusal, and who owns it

Local, before any request — exit 2, nothing sent:

| Message | Cause |
| :--- | :--- |
| `Invalid --audiences JSON: …` | not parseable |
| `--audiences must be a JSON array of audience entries.` | parsed to a non-array |
| `--audiences[<i>]: each entry must be a JSON object` | an entry is a scalar |
| `--audiences[<i>]: content_type is required: …` | missing — there is no implicit paywall |
| `--audiences[<i>]: this CLI does not know this audience kind; update the CLI` | a kind this CLI lacks. **On an entry you read from `placements get` and did not write**, tell the user to update the CLI and re-resolve `$ADAPTY` once, and if it still refuses, send the change to the dashboard. Never delete the entry; it is a running A/B test, and the write would stop it |
| `--audiences[<i>]: a flow entry requires flow_id` | flow entry, no `flow_id` |
| `Invalid placement ID format.` | `update` with a non-UUID placement id |

From the server:

| Message | What it means | What you do |
| :--- | :--- | :--- |
| `Cannot attach a draft flow to a placement — publish it first.` (exit 2) | the flow is not `published`. The CLI substitutes this for the backend's own `Flow must be published before placing in a placement.`, so route on the CLI wording and treat the backend sentence as the legacy form | publish, poll to `published`, retry |
| `Placement type can not be changed.` (`validation_error`) | the target is a paywall placement. A placement's content type is fixed at creation | propose a different developer ID; never try to convert |
| `audiences.0.paywall_id: Field required` | the union is not deployed on that server | stop calling the CLI, hand over the dashboard route below |

## The dashboard URLs

Read from the dashboard's own route table rather than from the
address bar, so the params are named rather than guessed:

| Route | Page |
| :--- | :--- |
| `/placements/flows` | the flow placement list |
| `/placements/flows/:placementId` | one flow placement |
| `/placements/flows/:placementId/metrics/` | its metrics |
| `/placements/flows/create` | the create form |
| `/placements` | **redirects** to `/placements/flows` |

Two things the route names but a URL does not.

**`:placementId` is the placement UUID, not the developer ID.** The list row type carries both as
separate fields — `placementId` *and* `developerId` — and the navigation uses `placementId`
(read from the dashboard's placement list code). So the developer ID, the string the app
fetches with, does **not** route: substituting it gives a page that cannot resolve. `placements
create` prints the UUID as `id`.

**The middle segment is the placement's type**, and the three are parallel routes —
`/placements/flows/…`, `/placements/paywalls/…`, `/placements/onboardings/…`. A flow placement under
the paywall segment is the wrong page, which is another reason a flow can never be attached to a
paywall placement: they are not the same object with a different payload.

There is no app id in the path — the dashboard resolves the app from its own app filter — so the
link is correct only for whoever is already scoped to that app.

## The dashboard route

The fallback for the last row above, and the route a user takes when they would rather not have you
write to their account at all:

[Adapty Dashboard → Placements](https://app.adapty.io/placements) → **Create placement** → set the
**Developer ID** to the exact string the app will fetch with → attach the flow under the **All
Users** audience → save.

## Why the developer ID gets its own approval block

It is permanent in a way a config write is not. The docs, verbatim: *"Placement IDs are unique
across every placement in the app, whatever the type, so the same ID can't serve a flow in one
place and a paywall in another."* ([placements.md](https://adapty.io/docs/placements.md)) There is
no rename and no delete from the CLI, so a wrong ID is spent — the user has to invent a different
one and the app code has to change to match.

That is also why a **paywall** placement is not a candidate even when its ID is the one everybody
wants: attaching a flow to it is refused, and it permanently occupies the string.

## The handoff, and where this skill stops

Phase 6 ends at the developer ID. The app side — fetching the placement, rendering what comes back,
and the call sites that do it — belongs to the **`adapty-integration`** skill, which takes the
developer ID as its input. This skill never edits app code, and naming the SDK's fetch method here
would be a claim about an API surface it does not own.

**No CLI command exports a fallback file.** The user downloads it from the **Fallbacks** button on
the Placements page: https://adapty.io/docs/fallback-flows.md.
