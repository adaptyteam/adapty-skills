# Store rules for screenshots and app code

The rule set `store-check.py` runs on a flow, written for a picture and for the app's own code.
Go through **every row**; a row you could not see goes under "Tell me, and I can check", never
under a pass. The evidence behind each rule is in [`mechanisms.md`](mechanisms.md) and
[`store-review.md`](store-review.md); the guidelines themselves are
[Apple's App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) and
[Google Play's Subscriptions policy](https://support.google.com/googleplay/android-developer/answer/9900533).

**How to read code.** A label says what a button claims; only its handler says what it does.
For each button on a selling or onboarding screen, follow the handler to the call it makes: a
purchase, a restore, opening a URL, closing the screen, navigating, a system prompt, a sign-in.
Search the whole app for the restore call and the system prompts, not only the paywall view:
a restore in Settings does not count for the paywall, but a shared footer view does.

**A screen sells** when it shows a price or a plan and has a button that starts a purchase.

## Required mechanisms — blockers

A selling screen without one of these is rejected. Say "will be rejected", with the guideline.

| Rule | In a screenshot | In code | Fix |
|---|---|---|---|
| **Restore** (App Store 3.1.1) | a "Restore purchases" link or button on the paywall | a button on the paywall (or a view it includes) whose handler calls the purchase library's restore, or StoreKit's sync of transactions | Add a "Restore purchases" link, usually under the purchase button |
| **Terms of Use link** (App Store 3.1.2) | a "Terms of Use" or "EULA" link | a button or link that opens the terms page's URL | Add a link that opens the Terms of Use page |
| **Privacy Policy link** (App Store 3.1.2) | a "Privacy Policy" link | a button or link that opens the privacy page's URL | Add a link that opens the Privacy Policy page |
| **A way out of the paywall** (someone who does not buy must be able to leave) | a close button or a "Not now" on the paywall; an icon with no text counts | a button whose handler dismisses the screen or navigates back, reachable from every selling screen; a sheet the system lets people swipe down also counts | Add a close button; an icon is enough |

**A link that only reads "Terms" is a question in a screenshot** — ask whether it opens the
page. In code, the URL answers it: a URL with "terms", "tos", "eula", "legal" or "privacy" in
its path is the link; any other URL, ask. A label with no handler (text styled as a link) is a
**blocker** in code and the same as missing, and so is a missing link when every other link is
plainly something else (the other legal page, a checkout). A legal link on a placeholder domain
(`example.com`, `localhost`, a staging host) is a question: the reviewer will open it. The
checker does not judge hosts; read the URLs `--screens` prints.

## Paywall shapes — risks

These have drawn rejections. Say "Apple has rejected", with the guideline, never "will reject".

| Rule | Store | In a screenshot | In code | Fix |
|---|---|---|---|---|
| **No free-trial toggle** (3.1.2) | iOS | a switch that turns a free trial on or off | a toggle or switch bound to a trial or offer flag that swaps the product or the price text | Show the trial and the plan without it as two plans the person picks between |
| **The billed amount is shown** (3.1.2(c)) | both | a per-week or per-month figure for a yearly plan, and the yearly price people are charged nowhere on the screen | price text built from a per-period figure (price divided by weeks or months) with no text that shows the full price | Show the price people are billed, for example "$79.99/year" |
| **The billed amount is the loudest price** (3.1.2(c)) | both | the per-week or per-month figure is bigger or bolder than the billed amount | the per-period figure's font is larger or heavier than the billed price's | Make the billed amount the largest, boldest price; keep the per-period figure smaller beside it |
| **The billing period is said** (3.1.2) | both | a subscription price with no "/year", "per month", "billed weekly" anywhere on the screen | no period text beside the price, and none in the footnote | Add the period: "/year" next to the price or "Billed yearly" under the button |
| **What happens after the trial is said** (3.1.2; Google Play) | both | "7-day free trial" with no price or "then" tied to it: on the same card or line, or under the same plan | trial text with no price, period or "then" text tied to the trial | Say it next to the offer: "Free for 7 days, then $79.99/year" |
| **No link to buy outside the app** (3.1.1) | iOS | a button that opens a web checkout or a payment page | a URL opened from a selling screen whose path names a checkout or a payment provider | A question: allowed on the US storefront, or with an Apple external purchase entitlement where one exists (the EU and a few other regions); ask where the app sells and which applies. **On Google Play**, digital subscriptions go through Play billing unless the developer is enrolled in one of Google's alternative billing or external offers programs for that country: ask |

## Onboarding shapes — risks

The screens around the paywall. On iOS a permission screen is the screen **before** the system
prompt; the person declines in the prompt itself.

| Rule | Store | In a screenshot | In code | Fix |
|---|---|---|---|---|
| **No Skip beside a permission prompt** (5.1.1(iv)) | iOS | a screen that asks for notifications, location, tracking, camera or health, with a "Skip", "Not now" or "Maybe later" next to its button; a Back arrow does not count | the screen's other button navigates on without calling the permission request | Keep one button that shows the prompt. **Never tell an Android-only app to remove it**: Google asks for a way to decline |
| **The prompt button says "Continue"** (Human Interface Guidelines, Privacy) | iOS | that button reads "Allow", "Enable", "Turn on" or "Grant" | the same button's title | Word it "Continue" or "Next" |
| **No reward for granting a permission** (5.1.2(i)) | iOS | the permission screen offers something: a free week, a discount, a bonus | the same screen's text | Remove the offer from that screen |
| **No copy of the tracking prompt** (Human Interface Guidelines, Privacy) | iOS | a screen that imitates the system tracking alert or says "tap Allow" | text that copies "Ask App Not to Track" or "Allow Tracking" | Explain the value in your own words, then show the real prompt |
| **No rating ask during onboarding** (5.6.1) | both | a "Rate us" step or stars before people have used the app, or any ask for a set number of stars ("Rate us 5 stars") | the system review request, or a link to the store's write-review page, on an onboarding screen | Ask later, after a moment people enjoyed, with the system's own review request; never ask for a set number of stars (5.6.3; the checker does not judge this part, read it from `--screens`) |
| **No sign-up wall** (5.1.1(v)) | iOS | signing in or creating an account is the only way past a screen | every button on the screen leads to sign-in | A question: needed only when the app's core features need an account; otherwise add "Continue without an account" |
| **No second offer on close** (5.6) | iOS | closing a paywall opens another paywall or a discount | the close handler navigates to another selling screen | Let close close |
| **The purchase button does not look like "Next"** (Google Play Subscriptions policy) | Android | the purchase button reads exactly like the buttons on the two screens before it ("Continue") | the purchase button's title equals the previous screens' forward buttons | Name the purchase: "Start free trial", "Subscribe" |

## Not checkable from a screen or from code

Say these when they apply, each with where to check:

- **Products approved in App Store Connect** before review sees the paywall, or the reviewer gets
  empty prices.
- **Terms and Privacy linked in the store listing too**, not only in the app.
- **Prices matching** the store listing and any marketing.
