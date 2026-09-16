# Google Play: running the purchase

Preflight passed, so Adapty and the app agree. What is left is the store and the device.

Creating products in Google Play Console and connecting Google Play to Adapty (service
account, RTDN) are **not here** — they belong to `adapty-integration`. If preflight landed
on layer 3 or 4, route there.

Full procedure: https://adapty.io/docs/testing-on-android.md

## The ordering gate, before anything else

**Google Play will not let you create in-app products or subscriptions until a signed AAB
carrying the `com.android.vending.BILLING` permission has been uploaded to a track.** So
on an Android-first app the upload comes *before* the products exist, which inverts the
order everything else implies. If the Subscriptions and In-app products pages are empty or
disabled, this is why — it is a one-time gate, not a misconfiguration.

Say this out loud when it applies. A user who reads "create your products" first, finds a
disabled page, and has no explanation assumes their account is broken.

## Three things gate a purchase, and all three are silent

There is no error for any of these. Products simply do not load, or the sheet never opens.

**1. The account is a license tester.** Google Play Console → Settings → License testing,
license response `RESPOND_NORMALLY`. It must be a Google account signed in on the test
device, and it cannot be the developer account itself.

**2. A signed build is on a closed track.** Local debug builds never trigger Play billing —
this is the single most common "the purchase sheet doesn't appear." Upload a signed
APK/AAB to a closed track.

> **You do not need to roll out the release.** Uploading to the track is enough. Our
> older guidance walked users through Review release → Start rollout, which is real work
> for no benefit. Wait a few minutes for processing.

**3. The tester opened the opt-in URL, on the test device.** From the track's *How testers
join your test* section. **Skipping this means products will not load** — and nothing
anywhere says so. Opening it marks the Play account for testing; it has to happen on the
device that will run the purchase.

## Installing and buying

Install from Play after opting in. Sideloading the signed APK is faster to iterate on and
works, *provided* the tester account is signed in on the device — billing is keyed to the
account, not to the install source.

Then trigger the paywall and buy. The Play purchase sheet should show your product's real
name and price; a sheet that shows neither means the product is not active in the console,
which is layer 4.

## Renewals

Sandbox renewals are compressed, and Adapty's own docs route to Google for the schedule
rather than restating it — do the same:
https://developer.android.com/google/play/billing/test#subs

## Getting unstuck

**"Item already owned"** — a previous test purchase was never consumed. Cancel or refund
the order under Google Play Console → Order management. Do not work around it by minting a
new product ID; that leaves a permanent product behind and Adapty's store IDs are
immutable once created.

**Products list is empty** — check the product ID *and the base plan ID* against the
console, character for character. A subscription whose base plan is not activated returns
nothing, with no error to read.
