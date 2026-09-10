# Placements: the evidence behind phase 6

Phase 6 holds the decisions and the two commands. This file holds what they were measured against,
so the entry point does not carry a caveat an agent cannot act on at that step.

**Everything here was measured against the default production API** — no `ADAPTY_API_URL`
override — by running the commands. Error strings are quoted exactly, because an agent routes on
them and a paraphrase is a bug.

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
| `--audiences[<i>]: content_type is required and must be "paywall" or "flow"` | missing or misspelled — there is no implicit paywall |
| `--audiences[<i>]: a flow entry requires flow_id` | flow entry, no `flow_id` |
| `Invalid placement ID format.` | `update` with a non-UUID placement id |

From the server:

| Message | What it means | What you do |
| :--- | :--- | :--- |
| `Cannot attach a draft flow to a placement — publish it first.` (exit 2) | the flow is not `published`. The CLI substitutes this for the backend's own `Flow must be published before placing in a placement.`, so route on the CLI wording and treat the backend sentence as the legacy form | publish, poll to `published`, retry |
| `Placement type can not be changed.` (`validation_error`) | the target is a paywall placement. A placement's content type is fixed at creation | propose a different developer ID; never try to convert |
| `audiences.0.paywall_id: Field required` | the union is not deployed on that server | stop calling the CLI, hand over the dashboard route below |

## The dashboard URLs

Read from the dashboard's own route table (`apps/web/src/app/Routes.tsx`) rather than from the
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
(`PlacementFlowList.tsx`, `cell.row.original.placementId`). So the developer ID, the string the app
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
