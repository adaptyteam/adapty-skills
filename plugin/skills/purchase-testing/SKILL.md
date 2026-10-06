---
name: purchase-testing
description: Use when a sandbox or test purchase does not work, or when someone is about to make their first one. Triggers on "my sandbox purchase isn't going through", "the purchase sheet doesn't appear", "I bought it but nothing happened", "the paywall is blank on my phone", "no event in the Adapty dashboard", "how do I test purchases", "test on a real device", "restore doesn't work". Diagnoses first, so nobody is sent back to a console before the cheap checks have run. Complements `adapty-integration`, which owns writing the code and connecting the stores.
---

# purchase-testing

## What this answers

**Why doesn't this purchase work — and what do I do about it?** Also the forward case:
someone whose code builds and whose stores are connected, about to run their first
sandbox purchase — often straight after `adapty-integration` hands over.

The value is the order. A purchase failure can live in five different places, and the
expensive ones involve a human clicking through a store console. So this skill checks
everything it can reach itself, first, and only then asks anyone to open a browser.

**This skill does not connect stores and does not write code.** Creating store products,
uploading an App Store In-App Purchase Key, setting up a Google Play service account and
RTDN, and writing the SDK calls all belong to `adapty-integration`. When a check here
lands on one of those, offer the outcome ("I can add the code that closes the paywall
after a purchase. Want me to?") and invoke `adapty-integration` on a yes.

## How you sound

Every message, not only the fixed blocks:

- **A patient colleague who knows in-app purchases.** The user is often testing a
  purchase for the first time. Assume they may know nothing about sandbox accounts or
  store consoles; when they ask, answer plainly and use their own app as the example.
  Friendly through patience, never through filler. Someone chasing a broken purchase is
  already frustrated, so the next action comes before any explanation.
- **"I" for what you do, "you" for what they do.** Lead with the answer; end on the one
  thing they need to do next. No opener ("I checked…"), no recap, no "let me know if…".
- **Plain words over raw values.** Show a value only when the user will type it or see
  it elsewhere: a placement ID, a product ID, a menu path, a URL. Never field names
  (`is_active`), never "layer 2", never skill or tool names, never the paths of files you
  saved while working.
- **Bold at most one thing per paragraph.** A label the user must pick or match (a test
  card, a menu item) goes in quotes, not bold.
- **Full, clickable links to the exact page.**
- **Could not check it? Say how they can** — where to click and what they should see.
  Do not know something? Look it up before saying so — the CLI, the code, the
  `adapty-docs` skill.
- **Offer the outcome, never the skill that will do it.**
- **Reply in the user's language.** Menu names and buttons stay exactly as the phone or
  the console shows them.

## The five layers

Every purchase failure sits in exactly one of these. Naming the layer before touching
anything is the whole method — the wrong guess costs a round trip through a console.
**The layers are how you think, not how you talk:** tell the user *where* the problem is
("in your code", "in App Store Connect", "on the phone"), never a layer number.

| Layer | What lives here | Who can check it | Say it as |
|---|---|---|---|
| 1. Adapty dashboard | product, access level, placement, flow status | **you**, through the CLI | "in the Adapty dashboard" |
| 2. App code | placement ID, call order, entitlement read | **you**, by reading the code | "in your code" |
| 3. Store ↔ Adapty connection | keys, service account, server notifications | the user — `adapty-integration` fixes it | "the connection between the App Store and Adapty" |
| 4. Store console | the product itself, its price, its state | the user | "in App Store Connect" / "in Play Console" |
| 5. Device / account | sandbox account, tester opt-in, purchase history | the user | "on the phone" / "the test account" |

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

If that fails, tell the user to run `adapty auth login` and stop; every check below reads
the account. Then, with the app id:

```bash
$ADAPTY apps get <APP_ID> --json
$ADAPTY placements list --app <APP_ID>
$ADAPTY products list --app <APP_ID>
$ADAPTY access-levels list --app <APP_ID>
```

`apps get` also returns the app's `secret_key`. **Never show it to the user** or copy it
anywhere; nothing in this skill needs it.

> **`--page-size` defaults to 20** and the response carries `meta.pagination
> {count, page, pages}`. Reading page 1 and reporting its length under-reports any
> account with more than 20 placements or products. Page through to `pages`.

Five checks, in this order. Each one that fails names where the problem is and stops the
guessing.

**1. Adapty knows the app's store identity.** `apps get` returns `apple_bundle_id` and
`google_bundle_id`. The one for the platform under test must be set, and it must match the
app's own bundle ID or package name (in the Xcode project or `applicationId` in Gradle). A
`null` means Adapty cannot verify purchases with that store at all: the store takes the
money, the paywall reports an error, and nothing reaches the Event Feed. That is the store
connection, and `adapty-integration` sets it up — offer it. The ID alone is not the
connection: Adapty also needs the store's credentials (the In-App Purchase key; a Google
Play service account), which only the dashboard takes. `apps update --apple-bundle-id` or
`--google-bundle-id` sets the ID from here, but offer the whole connection, never the ID
alone as if it were the fix. While it is missing, it is the problem: never tell the user
"nothing is broken". Do not take "I've connected the store" on trust; this read is free.

**2. The placement exists, and it is Live.** `placements list` returns `developer_id`
and `is_active` per placement. `is_active: false` means **Inactive** — the placement
serves nothing, and every symptom downstream is explained by it. This is the cheapest
possible find and nothing else in the chain reveals it.

**3. The app code asks for exactly that developer ID.** Grep the code for the
placement string and compare it to `developer_id` character for character. It is
case-sensitive, and the dashboard shows the placement's *name* more prominently than its
ID, which is where `"Main"` against `main` comes from. A mismatch is yours to fix and
needs no user at all.

**4. The placement shows something, and it is live.** `placements list` does not return
audiences — you need the detail call:

```bash
$ADAPTY placements get --app <APP_ID> <PLACEMENT_ID>
```

Each audience entry carries a `content_type` of `flow` or `paywall`, plus `flow_id` or
`paywall_id`. An empty `audiences` array is a placement with nothing attached, which
looks exactly like a broken SDK call from inside the app. Then check what it shows:

- **A flow** — it must be published. This is the single most common cause of "I changed
  it and my phone still shows the old screen":

  ```bash
  $ADAPTY flows config get --app <APP_ID> <FLOW_ID>
  ```

  `status` is `draft`, `dirty`, or `published`. **`dirty` means the flow has unpublished
  changes, and its placement keeps serving the last published version** — so the builder
  shows the new design and the phone shows the old one, with no error anywhere. `draft`
  means it was never published. Both are the user's click in the builder. On a failed
  publish the response also carries `publication_error` and `transform_error`: quote
  that string, it is the transform service's own objection.
- **A paywall** — `$ADAPTY paywalls get --app <APP_ID> <PAYWALL_ID>` returns its title
  and `product_ids`; there is nothing to publish. The CLI cannot see whether the paywall
  has a Paywall Builder layout, so if the code renders it with Adapty's own paywall UI,
  name that as something you could not check.

**5. The products carry store IDs and an access level.** `products list` and
`products get` return `access_level_id` and a `vendor_products` map. A product with no
store ID for the platform under test can never resolve a price, and a product whose
`access_level_id` does not match the level the app checks grants nothing on purchase —
the purchase succeeds and the user stays locked out, which is the most confusing
symptom in the whole surface.

**Report the preflight before anything else** (the block is under
[What you print](#what-you-print)). Then go to what failed, or to Phase 2 if all five
pass.

## Phase 2: The first purchase, one step at a time

All five preflight checks pass, so the dashboard and the code agree. What is left is the
store and the phone, and only the user can touch those. **This is a conversation, not a
document:** the user does a step, comes back, and you take the next one. Send one step
per message.

| Step | Who | What | How long |
|---|---|---|---|
| 1. Checked from here | you | the preflight, including the store identity | — |
| 2. Set up the test account and the phone | the user | the store reference's setup | about 5 minutes |
| 3. Buy | the user | open the paywall, buy, read the purchase sheet | a minute |
| 4. Confirm it reached Adapty | the user | [Event Feed](https://app.adapty.io/event-feed), then the user's profile | up to 10 minutes |
| 5. Restore, then a renewal | the user | restore on a clean install; wait for one renewal | 5–10 minutes |

The steps for each store live in its reference — follow the one for the platform under
test, and take from it only what the current step needs:

- **App Store** → `references/app-store.md`
- **Google Play** → `references/google-play.md`

Anything about connecting the store to Adapty routes back to `adapty-integration`.

Three rules for the walk:

- **Every message opens with where you are**, in one line: "Step 3 of 5 done: Apple
  completed the purchase." The user cannot hold the plan between messages; you restate it.
  That holds when they skipped ahead or a step went wrong, too: say which step they are
  at.
- **Give only the current step.** Re-test tips belong to the re-test, the TestFlight trap
  to the moment TestFlight comes up, renewals to step 5. Front-loading them buries the
  one thing to do now.
- **End on one reply line** that names what to send back ("Reply "done", or tell me what
  you saw instead"), so any answer moves the walk forward. Never a second offer of what
  the message already offered.

What each step means, so nobody stops early:

- **Step 3 is not the finish line.** A purchase sheet that says it is done means the
  store took the purchase. It says nothing about Adapty or the app.
- **Step 4: the event reached Adapty, and the access level is active.** The event appears
  in the [Event Feed](https://app.adapty.io/event-feed) within about ten minutes; opening
  it leads to the user's profile, which must show the access level as active (all
  profiles: https://app.adapty.io/profiles/users). Slower than that, or absent, is the
  store connection and routes to `adapty-integration`. **Sandbox purchases never appear
  in the analytics charts** — only in the Event Feed and on profiles — so a user who looks
  at the charts sees nothing and concludes it failed; say where to look. The CLI cannot
  read events or profiles, so this step is always the user's.
- **Step 5: restore works on a clean install, and a renewal lands.** Delete the app,
  reinstall, same test account, run restore — the check nobody runs and Apple always
  does. Sandbox renews on a compressed clock, so a renewal costs minutes; the store
  reference carries each store's timings.
- **A purchase that did not reach Adapty is not lost.** The test account owns it. Once the
  cause is fixed, restoring brings it in; never ask for a new purchase or an account
  reset. Say this when the fix is done and you send them to restore, not before.

**Before telling the user what the screen should do after a purchase, read what the code
does.** Some setups close the paywall on their own after a successful or pending purchase —
Adapty's default Android event listener does; some never close it — a SwiftUI paywall
presented with a constant `isPresented` never does. So a paywall that stays up after the
store said the purchase went through means two different things:

- **The code would have closed it** — this is a signal, never "expected". A pending payment
  (on Android, a "slow test card"), a purchase error the code swallows, or a purchase
  Adapty could not verify. Ask for the log (`adb logcat | grep -i adapty`, or the Xcode
  console), check the store identity from check 1, and localize before step 4.
- **The code does nothing after a purchase** — then it is expected: say so, judge the test
  by step 4 rather than by the screen, and offer to add the code.

## Phase 3: Diagnose

When something fails, localize before you fix. The **pattern** of what works narrows
the layer faster than any single symptom.

| What you see | Layer | Read it as |
|---|---|---|
| Paywall never appears, no error | 1 or 2 | Placement inactive, empty audiences, an unpublished flow, or a placement ID that differs by case — Phase 1 finds all four |
| Paywall appears, prices missing or empty | 1 or 4 | Product IDs disagree between Adapty and the store console, or the store product is not active |
| Old design on the phone, new one in the builder | 1 | Unpublished flow changes — the placement serves the last published version |
| Purchase sheet never opens | 5 | Phone or account state: wrong sandbox account, tester not opted in, app not installed from the store |
| Purchase completes, nothing unlocks | 1 or 2 | The product's access level is not the one the app checks, or the app never reads it |
| The store took the purchase, but a paywall that closes on success stays up | 3 or 5 | Adapty could not verify it (check 1: store identity), a pending payment, or an error the code swallows — the log says which |
| Purchase completes, no event in Adapty | 3 | Server notifications / RTDN — `adapty-integration` fixes the connection |
| Works for you, not for a teammate | 5 | Account state, not configuration — compare the two accounts before touching anything else |

Two rules that keep a diagnosis honest:

- **A suspicious-looking value is not evidence, and a clean-looking one is not a fix.**
  Say where you localized it and what observation put it there.
- **A purchase you cannot reproduce is not fixed.** Walk steps 3–5 again after every
  change, because sandbox state is sticky — an account that already owns the product
  produces a different failure from the one you were chasing.

## What you cannot check from here

State these rather than letting the user assume the pass was total, and say how they can
check each one:

- **Anything on the phone.** You cannot see which store account is signed in, whether
  the tester opted in, or what the purchase sheet showed. Every phone or account finding
  is a question you ask, never a check you ran.
- **Whether the store console matches.** `products list` tells you what Adapty believes
  the store ID is. Only the console tells you whether a product with that ID exists,
  is priced, and is active — name the ID and where to look it up.
- **Events and profiles.** The CLI has no command for either; step 4 is the user's.
- **Production behavior.** Sandbox uses different accounts, different servers, and an
  accelerated clock. A working sandbox purchase is necessary and not sufficient.

## What you print

Every message has the same four parts, in this order, and nothing else:

1. **One bold line with the answer to what the user asked**: what happened, or what is
   wrong. The progress line during the walk ("Step 3 of 5: …").
2. **Why**: two sentences at most, counted, and only when line 1 does not already say it.
   A second possible cause goes here in brackets, not in its own paragraph. If the
   mechanism needs more, stop at two and let them ask; never explain the store's internals
   unprompted. The limit never cuts a second cause that changes what the user should do
   (a sandbox subscription that has expired by now, so a restore would find nothing): that
   goes in brackets.
3. **Next**: one action. Instructions the user follows go here as a numbered list, with the
   exact place, the values already filled in and what they should see.
4. **One reply line**, and the only offer in the message. If Next already asked "Want me
   to?", the reply line is the answer to it, not a second ask.

**Answer the question they asked, not the one your preflight answered.** Line 1 and Next
are about their symptom or question. A preflight problem that does not cause it, such as a
missing store connection behind an error the store raised before Adapty was involved, gets
exactly one sentence after Next ("Separately: Adapty isn't connected to the App Store
yet; that's the next thing to fix.") — never the headline, never the next step, and never
the reasons or the steps for it; those come when it is the thing being fixed. When the preflight
problem *is* the cause, it is the answer.

Two extras, both only where they apply: the checks table (in the preflight message only),
and one line for something you could not check, saying where the user can check it — only
when it could explain their symptom. A check that has nothing to do with what they asked is
left out, not listed.

Each thing is said once. Leave out whatever the user does not need to act on now: later
steps, what happens after the fix, "everything else is ready" (the table says it),
"waiting won't help" when you have already said why nothing arrived, a list of docs pages
when you have offered to walk them through it. Aim for under ~120 words outside the
table and the numbered list. The examples show the shape, not words to copy.

**The preflight result**, before anything else. When everything passed, it is one line
("Your dashboard and your code are ready for a test purchase.") and the walk starts in the
same message. When something failed:

> **Adapty isn't connected to Google Play yet, so a test purchase wouldn't reach it.**
> Google would take the payment and your paywall would show an error.
>
> Next: connect Google Play to Adapty: your package name `com.example.app` plus a
> service account key, about 20 minutes.
>
> | Check | Result |
> |---|---|
> | Adapty knows your app's package name | **No:** it's empty |
> | The placement exists and is live | Yes, `main` |
> | Your code asks for exactly that ID | Yes, `"main"` in `PaywallActivity.kt` |
> | The placement shows something | Yes: the paywall "Premium", with one product |
> | The product has a Google Play ID and an access level | Yes: `com.example.premium.monthly`, access level `premium` |
>
> I can't see Play Console from here: check that the base plan `monthly` shows as "Active".
>
> Reply "go" and I'll walk you through the connection.

Never print a row for a check that does not apply.

**A step of the walk**, from step 2 on:

> **Step 2 of 5: set up a test account and your phone.** About 5 minutes.
>
> 1. In App Store Connect, open Users and Access → Sandbox → Test Accounts and create a
>    new tester with an email you have never used for an Apple ID.
> 2. …
>
> Reply "done", or tell me what you saw instead if a menu isn't where I said.

**A diagnosis**, when something went wrong:

> **Step 3 of 5: Google Play took the purchase, but it didn't reach Adapty.**
>
> Your paywall closes itself once Adapty confirms a purchase, and Adapty can't confirm it
> until Google Play is connected. (If you picked "Slow test card", it may also still be
> pending.)
>
> Next: connect Google Play to Adapty, about 20 minutes. I'll take you through it one
> screen at a time.
>
> Reply "go" to start, or tell me if you used the slow test card.
