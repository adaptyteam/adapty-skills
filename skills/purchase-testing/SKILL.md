---
name: purchase-testing
description: Use when a sandbox or test purchase does not work, or when someone is about to make their first one. Triggers on "my sandbox purchase isn't going through", "the purchase sheet doesn't appear", "I bought it but nothing happened", "the paywall is blank on my phone", "no event in the Adapty dashboard", "how do I test purchases", "test on a real device", "restore doesn't work". Diagnoses first, so nobody is sent back to a console before the cheap checks have run. Complements `adapty-integration`, which owns writing the code and connecting the stores.
---

# purchase-testing

## What this answers

**Why doesn't this purchase work — and what do I do about it?** Also the forward case:
someone whose code builds and whose stores are connected, about to run their first
sandbox purchase.

The value is the order. A purchase failure can live in five different places, and the
expensive ones involve a human clicking through a store console. So this skill checks
everything it can reach itself, first, and only then asks anyone to open a browser.

**This skill does not connect stores and does not write code.** Creating store products,
uploading an App Store In-App Purchase Key, setting up a Google Play service account and
RTDN, and writing the SDK calls all belong to `adapty-integration`. When a check here
lands on one of those, say so and route there rather than re-explaining it.

## The five layers

Every purchase failure sits in exactly one of these. Naming the layer before touching
anything is the whole method — the wrong guess costs a round trip through a console.

| Layer | What lives here | Who can check it |
|---|---|---|
| 1. Adapty dashboard | product, access level, placement, flow status | **you**, through the CLI |
| 2. App code | placement ID, call order, entitlement read | **you**, by reading the code |
| 3. Store ↔ Adapty connection | keys, service account, server notifications | the user — route to `adapty-integration` |
| 4. Store console | the product itself, its price, its state | the user |
| 5. Device / account | sandbox account, tester opt-in, purchase history | the user |

Layers 1 and 2 are free and instant. Run them before asking a single question.

> Anything product-side this skill does not cover — what a setting means, how a store
> integration behaves, an error code — use the **`adapty-docs`** skill to find it. Never
> assemble a docs URL from a topic name.

## Phase 1: Preflight — everything you can check without a human

Resolve `$ADAPTY` once, the way `adapty-integration` does:

```bash
npm i -g adapty@latest >/dev/null 2>&1 \
  && ADAPTY="adapty" \
  || ADAPTY="npx --yes adapty@latest"              # fallback: prefix not writable
$ADAPTY auth whoami
```

`--yes` on the fallback is load-bearing: without it npx stops to ask permission to install,
and a headless run has nobody to answer. In `zsh` a multi-word `$ADAPTY` is not word-split,
so run `setopt shwordsplit` once in the same shell; `command not found: npx --yes
adapty@latest` is that shell problem, never a missing CLI.

If that fails, say authentication is needed and stop; every check below reads the
account. Then, with the app id:

```bash
$ADAPTY placements list --app <APP_ID>
$ADAPTY products list --app <APP_ID>
$ADAPTY access-levels list --app <APP_ID>
```

> **`--page-size` defaults to 20** and the response carries `meta.pagination
> {count, page, pages}`. Reading page 1 and reporting its length under-reports any
> account with more than 20 placements or products. Page through to `pages`.

Five checks, in this order. Each one that fails names its layer and stops the guessing.

**1. The placement exists, and it is Live.** `placements list` returns `developer_id`
and `is_active` per placement. `is_active: false` means **Inactive** — the placement
serves nothing, and every symptom downstream is explained by it. This is the cheapest
possible find and nothing else in the chain reveals it.

**2. The app code asks for exactly that developer ID.** Grep the code for the
placement string and compare it to `developer_id` character for character. It is
case-sensitive. A mismatch is layer 2, it is yours to fix, and it needs no user at all.

**3. The placement serves what you think it serves.** `placements list` does not
return audiences — you need the detail call:

```bash
$ADAPTY placements get --app <APP_ID> <PLACEMENT_ID>
```

Each audience entry carries a `content_type` of `flow` or `paywall`, plus `flow_id` or
`paywall_id`. An empty `audiences` array is a placement with nothing attached, which
looks exactly like a broken SDK call from inside the app.

**4. If it serves a flow, the flow is published.** This is the single most common
cause of "I changed it and my phone still shows the old screen":

```bash
$ADAPTY flows config get --app <APP_ID> <FLOW_ID>
```

`status` is `draft`, `dirty`, or `published`. **`dirty` means the flow has unpublished
edits, and its placement keeps serving the last published version** — so the dashboard
shows the new design and the device shows the old one, with no error anywhere. `draft`
means it was never published at all. Both are the user's click in the builder; you can
say precisely which one and why.

The same response carries `publication_status` and, on a failed publish,
`publication_error` and `transform_error`. If publication failed, quote that string —
it is the transform service's own objection, and it is more specific than anything you
could infer.

**5. The products carry store IDs and an access level.** `products list` and
`products get` return `access_level_id` and a `vendor_products` map. A product with no
store ID for the platform under test can never resolve a price, and a product whose
`access_level_id` does not match the level the app checks grants nothing on purchase —
the purchase succeeds and the user stays locked out, which is the most confusing
symptom in the whole surface.

**Report the preflight as one short block before doing anything else**, so the user can
see what was ruled out. Then go to the layer that failed, or to Phase 2 if all five pass.

## Phase 2: Run the purchase

All five preflight checks pass, so the dashboard and the code agree. What is left is
the store and the device.

Read the reference for the store under test and follow it:

- **App Store** → `references/app-store.md`
- **Google Play** → `references/google-play.md`

Each is the execution path only — test account, device state, the purchase itself.
Anything about connecting the store to Adapty routes back to `adapty-integration`.

## Phase 3: Verify — what "it worked" actually means

A completed purchase dialog is not the finish line. Four things, and the last two are
the ones that get skipped and then get apps rejected:

1. **The event reached Adapty.** [Event Feed](https://app.adapty.io/event-feed), within
   about ten minutes. Slower than that, or absent, is layer 3 — server notifications or
   RTDN — and routes to `adapty-integration`.
2. **The access level is active on the profile.** Not "the purchase succeeded" — the
   app's own entitlement read returns true. These are different claims and only the
   second one is what gates features.
3. **Restore works on a clean install.** Delete the app, reinstall, sign in with the
   same store account, run restore. This is the check nobody runs and Apple always does.
4. **A renewal lands.** Sandbox subscriptions renew on an accelerated schedule, so this
   costs minutes, not a month. The store reference carries each store's timings.

## Phase 4: Diagnose

When something fails, localize before you fix. The **pattern** of what works narrows
the layer faster than any single symptom.

| What you see | Layer | Read it as |
|---|---|---|
| Paywall never appears, no error | 1 | Placement inactive, empty audiences, or an unpublished flow — Phase 1 finds all three |
| Paywall appears, prices missing or empty | 1 or 4 | Product IDs disagree between Adapty and the store console, or the store product is not active |
| Old design on device, new one in the builder | 1 | `dirty` flow — the placement serves the last published version |
| Purchase sheet never opens | 5 | Device or account state: wrong sandbox account, tester not opted in, app not installed from the store |
| Purchase completes, nothing unlocks | 1 | The product's access level is not the one the app checks |
| Purchase completes, no dashboard event | 3 | Server notifications / RTDN — route to `adapty-integration` |
| Works for you, not for a teammate | 5 | Account state, not configuration — compare the two accounts before touching anything else |

Two rules that keep a diagnosis honest:

- **A suspicious-looking value is not evidence, and a clean-looking one is not a fix.**
  Say which layer you localized to and what observation put it there.
- **A purchase you cannot reproduce is not fixed.** Re-run Phase 3 after every change,
  because sandbox state is sticky — an account that already owns the product produces a
  different failure from the one you were chasing.

## What you cannot check from here

State these rather than letting the user assume the pass was total:

- **Anything on the device.** You cannot see which store account is signed in, whether
  the tester opted in, or what the purchase sheet showed. Every layer-5 finding is a
  question you ask, never a check you ran.
- **Whether the store console matches.** `products list` tells you what Adapty believes
  the store ID is. Only the console tells you whether a product with that ID exists,
  is priced, and is active.
- **Production behavior.** Sandbox uses different accounts, different servers, and an
  accelerated clock. A working sandbox purchase is necessary and not sufficient.

## What you print

Two fixed blocks, and everything else is one line or omitted.

**The preflight result**, before anything else: the five checks, each pass or fail with
the value you actually read, and the layer of the first failure.

**The ask**, when you reach a layer you cannot check: the exact thing to do, the exact
values already filled in (placement developer ID, product IDs, flow name), and what to
report back. Never send someone to a console without telling them what to look for.

Say each thing once. A user hunting a broken purchase is already frustrated; a wall of
narration between them and the next action is a cost, not thoroughness.
