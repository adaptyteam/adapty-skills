# Migration Reference: Retiring a Paywall in favor of a Flow

Read this **on demand only**, when all three of these are true:

- `migrationSource` is set,
- `paywallApproach` is `flow_builder`,
- the app shows a paywall the migration replaces. Either the app's own code renders it — layout, copy,
  and product list written by hand, in the app's UI framework — or it came out of the source's own
  visual builder (for RevenueCat, a Paywall Editor paywall the app presents through RevenueCatUI).

**`flow_builder` is the user's own Phase 2 answer, never an inference** — not from the source having
a builder paywall, and not by default on a run with nobody to answer; without it this file does not
apply.

That combination is the one case where the migration does not preserve the app's UI. Everywhere else
`references/migration.md` section 4 holds: keep the source's working UI and swap the SDK underneath
it. Here the user already asked for the replacement in Phase 2, so the paywall itself is being
retired — but only on the terms below, and never before the flow that replaces it is live.

Platforms: iOS, Android, React Native, Flutter, Kotlin Multiplatform. Capacitor and Unity have no
Flow Builder option in Phase 2, so this file never applies to them.

---

## 1. The hard gate

**The gate is that the flow is live, not who built it.** The `flow-generator` skill builds the
flow from the spec in section 3, and publishes it and points a placement at it on the user's word;
the dashboard is the fallback, on the routes SKILL.md Phase 3 Step 5 defines. Either way the user
approves the rebuilt screen before it is published. No amount of code gets you a rendering paywall
until the flow is published and placed, so that is the gate everything else queues behind — not a
step you sequence at your convenience.

Two consequences, and neither is negotiable:

- **Create no placement on a flow_builder run until the flow it points at is published.**
  `references/migration.md` section 3 already reserves the placement ID when the source's paywall
  came out of the source's own visual builder. A hand-built paywall reaches the same outcome by a
  different route: the flow needs that ID, and a **paywall** placement created on it blocks the flow
  placement with that ID permanently. So while the flow is a draft or does not exist,
  `$ADAPTY placements create` is not a command you run at all — not for the source's
  default offering, not for one the code names, not "to have something to point the code at". Once
  the flow is published, create it as a **flow** placement on that reserved developer ID, per
  SKILL.md Phase 3 Step 5's Flow Builder path and its five preconditions; where that route is
  refused, every placement here is created in the dashboard instead, attached to its flow.
- **When `placements list` already shows a paywall placement on the offering's ID, the flow gets
  `<developer_id>_flow`**, created as above once the flow is published; the paywall placement stays,
  and the code falls back to it until then (section 7).
- **The paywall swap is atomic.** Fetch, presentation, purchase, and entitlement gating move to
  Adapty together, in one stage, or none of them move. Section 7 explains the specific way a partial
  swap ships an app that still builds and still locks paying users out.

## 2. Order of operations

Each step needs the one above it to have really happened, so do not start one on the promise of
another:

1. Access levels created (`references/migration.md` section 3 — one per active source entitlement).
2. **Real** products created, with real store product IDs. Deferred products (SKILL.md Phase 3
   Step 4 — IDs not in the code, or Google Play's AAB prerequisite) defer everything below, because
   a flow with no products to attach is not worth building twice.
3. Rebuild spec in hand — section 3. For a hand-built screen, extract it **before** any code
   changes, while the screen is still intact and readable; for a source-builder paywall, ask for it.
4. The flow is built, **published**, and attached to its placement on the reserved developer ID —
   `flow-generator` builds it from the section 3 spec (SKILL.md Phase 3 Step 5, Route B), and the
   user approves the rebuilt screen before it is published. Route D, the dashboard, when the CLI
   refuses.
5. Code swap, atomic per section 1, in the platform reference's Stage 2 Flow Builder section.
6. Checkpoint on a device: flow renders, products appear, a sandbox purchase completes, access level
   is granted.
7. Only then: delete the old paywall — the screen, or the source's paywall presentation calls — and
   remove the source SDK — section 6.

## 3. Get the rebuild spec before you delete anything

The spec is `flow-generator`'s build brief, and on a run that cannot build the flow it is the
user's. Where it comes from depends on who built the old paywall.

### 3a. A hand-built screen: extract it from the code

Copy, product order, badge text, and locales live in the code you are about to delete, and `git`
history is not a rebuild brief — once the screen is gone, anything you did not record is gone with
it.

Read the paywall screen and every file it pulls strings, assets, or products from. Then copy this
template into `ADAPTY_SETUP.md` under the **Rebuild as flows** heading that
`references/migration.md` section 5.3 already defines, one block per paywall screen, and fill in
every field. `not present` is a valid value; a field left out is not — a reader cannot tell an
element the screen never had from one you did not look for.

```
**Screen:** <name> — <file:line>
**Shown from:** <each entry point, file:line> → placement developer ID <id — from the source's own
  offering identifier per `references/migration.md` section 3; if the code never names one, say so
  here and treat the ID as inferred, which section 3 requires you to disclose>
**Unlocks:** <access level ID>
**Products, in display order:**
| # | Store product ID | Label as rendered | Price string as rendered | Badge | Preselected |
|---|---|---|---|---|---|
**Trial / intro offer:** <copy, verbatim, and the condition under which it renders>
**Copy, verbatim and in order:** headline · subhead · feature bullets · CTA label(s) · footnote and
  legal line
**Controls:** close (and any delay before it appears) · restore · Terms URL · Privacy URL · every
  other button or link, with what it does
**Assets:** images, video, icons — by file path · fonts — family and weight · colors — as hex ·
  dark-mode variants
**Locales:** every locale the screen ships in, and where the strings live
**Conditional rendering:** segment checks, remote-config flags, A/B branches, first-launch-only
  rules — each with its file:line
**Computed values:** every string the code calculates rather than reads — per-month price derived
  from an annual product, "save 40%", countdowns
```

**When the screen ships in more than one locale**, put the per-locale string inventory in a sibling
`ADAPTY_FLOW_SPEC.md` and link it from that heading, so the rest of the handoff stays readable. The
rest of the spec stays inline in `ADAPTY_SETUP.md`.

### 3b. A source-builder paywall: ask for screenshots

Its design lives in the source's dashboard, not in the code, so nothing in the project can be
extracted. Ask the user for it, once per paywall, in this block. What each line is for:
one screenshot is one state, so the plan selection and the trial line each need their own; copy
transcribed from images is where typos come from, so other locales come as text; images come out
of a screenshot flattened, so the originals come as files; and the offering identifier is the
reserved placement ID, the one fact you cannot read off a picture.

> To rebuild **`<offering id>`**'s paywall as a flow, send me:
>
> 1. A screenshot of it with each plan selected, and one showing the trial offer if it has one.
> 2. The text for every other language it ships in — an export or a paste, not screenshots.
> 3. The original image files, and the font's name or file if it uses a custom one.
>
> The prices in the screenshots don't matter; the flow shows each store's live price.

*(The shape of the block, not words to copy:)*

> To rebuild **`default`**'s paywall as a flow, send me:
> 1. A screenshot with Annual selected, one with Monthly selected, and one with the 7-day trial showing.
> 2. The German and French text, pasted.
> 3. `hero.png` and the name of the headline font.
> The prices don't matter; the flow shows each store's live price.

Record the offering ID, the products the offering carries in display order, and the access level in
the section 3a template, and mark every field the screenshots answer as `from screenshot`. Never type
a price you read off a screenshot into the spec as copy. If the code does not name the offering —
the app presents the current one — add a line to the block asking which offering it is, and never
fill the ID in yourself. When nobody is there to answer, put the
block in `ADAPTY_SETUP.md` under **Rebuild as flows** as the user's next step, and stop there for
this paywall.

## 4. Build it with `flow-generator`, and decide what it cannot reach

Invoke `flow-generator` with the spec, the screenshots if you have them, the asset file paths, and
the products from section 2. It owns everything about the flow: which builder element each part of
the screen becomes, binding the products and price variables, uploading images, adding the locales, and
comparing its render against your reference until they match. Do not map elements yourself, and do
not answer its questions on the user's behalf.

It hands back a list of what the flow format cannot build — an element, an asset it cannot upload, a
behavior with no builder counterpart. **That list is the user's decision, not your omission.** Copy
it into the spec under **No builder counterpart**, with what each item does today, and give the user
the two options: ship the flow without it, or keep this screen on a custom paywall fed by Adapty
products (the `custom` path in the platform reference's Stage 2) while other placements use flows.

If what makes the screen work is bespoke animation, interaction, or business logic, you are looking
at the evidence `references/migration-architecture.md` row 4 weighs for keeping a custom paywall. Say
so to the user and record it. Do not silently change `paywallApproach` — that choice is theirs.

## 5. What the swap needs that the old paywall never had

A flow is not a drop-in for the old paywall, whether the app rendered it or the source's UI library
did. Four things the old one did implicitly now need code, and all of them are checkpoint failures if
missed:

- **Button actions arrive as events.** Close, restore, Terms, Privacy, and any custom button in the
  flow emit actions your code handles — they are no longer your own tap handlers. Every behavior you
  recorded under **Controls** needs a handler here: `https://adapty.io/docs/handle-paywall-actions.md`
  (iOS), `https://adapty.io/docs/android-handle-paywall-actions.md`,
  `https://adapty.io/docs/flutter-handle-paywall-actions.md`,
  `https://adapty.io/docs/react-native-handle-paywall-actions.md`,
  `https://adapty.io/docs/kmp-handle-paywall-actions.md`.
- **Purchase outcomes arrive as events too**, not as the return value of a button callback. The
  platform reference's Stage 2 Flow Builder section lists the events page for the platform.
- **Offline is no longer free.** The old screen rendered from compiled-in strings; a flow is fetched,
  so without a local fallback the paywall is blank on a cold offline launch — a regression a device
  test on wifi never shows. Set one up: `https://adapty.io/docs/fallback-flows.md`, with the
  platform side in `references/<platform>.md`.
- **Locale is now a parameter.** The old screen picked up the OS locale through the platform's own
  localization. A flow renders the locale you pass when you build its configuration, so pass the
  user's — a hardcoded `"en"` ships English to every user who had translations before. The exact call
  is in the platform reference's Stage 2.

One more thing the spec surfaces, and it is a question rather than a change: the old screen was
probably one file reused from several entry points. Placements are how a flow differs per entry
point, so the rebuild *could* give each entry point its own — but `references/migration.md`
section 3 still governs how many you create, one per offering the app actually uses, and splitting
one offering across three placements is a change to how the app monetizes, not a migration step.
Put the option to the user with the entry points you recorded, and create the extra placements only
if they ask for them.

## 6. Delete the old screen last, and only on evidence

Delete the paywall screen and its purchase code — for a source-builder paywall, the calls that
present it — **after** the section 2 step 6 checkpoint passes on a
device: the flow rendered, products appeared, a sandbox purchase completed, the access level was
granted. Not after the code compiles, not after the flow previews correctly in the dashboard.

Then remove the source SDK and grep for its symbols, per `references/migration.md` section 4.

The screen's UI code is the only rollback that exists for a flow that renders blank in production, so
until that checkpoint passes it stays. Note in `ADAPTY_SETUP.md` that users on app versions built
before this release keep seeing the old screen, and read
`https://adapty.io/docs/migrate-to-flows.md` for the roll-out half of that problem — the page is
written for a different starting point, so take only its guidance on not disrupting users on older
versions.

## 7. If the flow cannot be built this session

Headless runs and users who will not open the dashboard now are normal. What you do depends on one
thing `placements list` shows: **is there already an Adapty paywall the app can sell through?**

**Yes — a paywall placement already holds the offering's ID, with its products.** Then the whole
purchase path can move to Adapty now, and the swap is complete rather than partial:

- Fetch the flow from `<developer_id>_flow` (section 1). While that fetch fails, fall back to the
  paywall placement on `<developer_id>`, rendered by the app's own screen — so keep that screen, with
  its products, purchase and gating rewired to Adapty per the platform reference's Stage 2.
- An offering whose paywall came out of the source's visual builder has no Adapty placement to fall
  back to. Leave its ID free for the flow and fall back to the placement standing in for the source's
  current offering; when that one is missing too, to the first placement the lists showed.
- Remove the source SDK, per `references/migration.md` section 4.
- Put at the **top** of `ADAPTY_SETUP.md`: the flow does not show until it is published; what shows
  instead until then; and how to publish it — `flow-generator` builds and publishes it from
  screenshots of the current paywall, then a flow placement on `<developer_id>_flow`.

**No — nothing in Adapty can stand in for the paywall.** The rule is section 1's: **no partial
swap.** Concretely, on this run:

- Install and activate the Adapty SDK, wire user identification and logout, and set up the
  integrations. All of it is independent of any placement.
- **Leave the entire purchase and entitlement path on the source system**, with the source SDK still
  installed and the paywall screen untouched. Adapty does not own purchases yet, so it cannot grant
  access levels yet — repointing the app's "is premium" check at Adapty before the swap locks paying
  users out of what they bought. This is the specific way a partial swap breaks an app that still
  builds and still ships.
- Create no placement (section 1). Create access levels and products only where section 2 steps 1–2
  are genuinely satisfied.
- Extract the rebuild spec anyway (section 3) — it is the deliverable that makes the deferred work
  possible, and the code it comes from is still intact right now.

Then write the remainder into `ADAPTY_SETUP.md` as ordered, ready-to-run steps: build the flow (or
review and publish the draft, with its link, if one was saved), create the placement on the reserved developer ID,
then the exact code edits left (fetch, presentation, purchase, gating, action handlers), then the
deletion. Say plainly that the app is shipping with two purchase
systems installed and Adapty not yet in charge, and that this is a safe pause point rather than a
finished state.

That last point is where `references/migration.md` section 4's rule — remove the source SDK, because
two initialized SDKs double-report purchases — meets this one. The files do not disagree: that rule
describes the state a migration must *finish* in, and it is exactly why the interim state here has to
be written down as unfinished rather than left for someone to discover. The source SDK stays only
until the swap it is standing in for can happen, and the handoff has to name it as the reason the
migration is not done.
