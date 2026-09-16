# App Store: running the purchase

Preflight passed, so Adapty and the app agree. What is left is the store and the device.

Creating products in App Store Connect and connecting the App Store to Adapty are **not
here** — they belong to `adapty-integration`. If preflight landed on layer 3 or 4, route
there instead of working through this file.

## Pick the loop first

Two ways to test on iOS, and they answer different questions. Choosing wrong costs an
afternoon.

| | StoreKit configuration file | Sandbox |
|---|---|---|
| Setup cost | none — a file in Xcode | App Store Connect products, a sandbox account |
| Runs on | simulator or device | device (simulator works, device is the real test) |
| Access levels unlock | yes, locally | yes |
| **Reaches the Adapty dashboard** | **no** | yes |
| Server notifications exercised | no | yes |
| Good for | iterating on paywall and gating code | the answer to "does this actually work" |

**The trap is the bolded row, and it produces a false bug report.** Under a StoreKit
configuration file everything is local, so purchases never reach Adapty's servers — the
Event Feed stays empty and no server notification fires, *by design*. Someone who tests
this way and then checks the dashboard concludes the integration is broken when it is
working exactly as documented.

So: use a StoreKit file while iterating, and **never accept it as verification**. Phase 3
of the parent skill only means anything under sandbox.

Setup: https://adapty.io/docs/local-sk-files.md

## Sandbox

Full procedure: https://adapty.io/docs/test-purchases-in-sandbox.md — follow it rather
than working from memory, because the device paths have moved between iOS versions.

What that page will not shout loudly enough, and what actually goes wrong:

**A fresh sandbox account, every time.** Reusing one carries its purchase history, and a
product it already owns cannot be bought again — the failure looks like a broken purchase
flow rather than a used account. Plus addressing (`you+sb1@gmail.com`) reuses one inbox.

**Decline two-factor authentication** when signing in on the device. Accepting it makes
the account substantially harder to use for testing.

**Signing in happens in two places, and only one of them is right.** Sign *out* of
Settings → Your Apple Account → Media & Purchases, then sign *in* under
Settings → Developer → Sandbox Apple Account. Signing the sandbox account into Media &
Purchases directly is the single most common iOS testing mistake, and it produces a
purchase sheet that looks real and charges a real account.

Developer Mode must be on first (Settings → Privacy & Security → Developer Mode), or the
Developer menu is not there to find.

**Clearing purchase history is required for every repeat run** on the same account —
Settings → Developer → Sandbox Apple Account → Account Settings → Clear Purchase History.
Skipping it is what makes a second test behave differently from the first, which reads as
flakiness and is not.

**The TestFlight trap has no recovery.** If the app is opened even once before switching
to the sandbox account, TestFlight attributes the purchase, and purchase history cannot be
cleared for a TestFlight install without a sandbox account. Reinstalling alone does not
undo it: switch the account, clear history, *then* launch.

## Renewals

Sandbox compresses the clock. Up to 12 renewals, then it stops.

| Subscription | 1 week | 1 month | 2 months | 3 months | 6 months | 1 year |
|---|---|---|---|---|---|---|
| Renews every | 3 min | 5 min | 10 min | 15 min | 30 min | 1 hour |
| Grace period | 3 min | 5 min | 5 min | 5 min | 5 min | 5 min |

Use this to confirm the app handles renewals, billing retries and grace periods. **Do not
use it to predict production timing** — the schedule is a testing convenience, not a
scale model.

To take access away from a tester, cancel the subscription on the store side
(Settings → Developer → Sandbox Apple Account). Backdating an expiry or revoking the
access level through the API does not hold: sandbox auto-renews and the next sync
restores it.
