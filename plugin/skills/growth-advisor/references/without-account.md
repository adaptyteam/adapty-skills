# Without an Adapty account

The user sends a store link, screenshots, or the app's code, and there are no numbers to read. You
still answer in full: hypotheses ranked from what they sent, the market and the evidence library,
and an offer to bring Adapty in so the next answer runs on their real numbers.

## When this applies

A paywall screenshot alone with no numbers is `paywall-teardown`'s job, and onboarding screens
alone are `onboarding-teardown`'s: invoke that skill and stop. This path takes a store link, the
app's code, or the onboarding and paywall screens together with a question about the app's money.

- **No sign of Adapty** (they did not say they use it, and the code, when you have it, has no
  Adapty SDK in its dependencies): start here. Do not install or run the CLI to find out.
- **Adapty is in the app or they say they use it:** resolve `$ADAPTY` and run `apps list` once.
  When it lists the app, run the audit instead and use what they sent as the screenshot or code.
  When it says they are not logged in, or the app is not there, start here.

Never hold the answer back for a sign-in or an integration. Both are the last Next step.

## What you read

| They sent | Read |
|---|---|
| An App Store or Google Play link | Fetch the page once, as a browser would. Read the category, the subscriptions in the in-app purchase list by name (plan lengths, a lifetime, two products of one length), the languages, the rating, and what reviews say about paying. A trial shows only where a subscription is marked "Free Trial"; a product with no such mark has an unknown trial, never "no trial". The paywall's default plan never shows. A Google Play page lists no products: ask for the paywall. The listing's screenshots are marketing, not the paywall. When the page will not load or is rate limited, say so in one line and ask for screenshots: never retry with another user agent, a proxy or a cache |
| Screenshots | What each screen is, in the order you took them, said in one line. Plan lengths, which plan is preselected, which carries a trial, what the button says, Restore, Terms and Privacy, the language |
| The app's code | Find the purchase call and its product IDs, the paywall screen, and the onboarding screens in order. Read the copy from the string files and the locales that exist, which product is preselected, which carries a trial (a comment, a StoreKit configuration file, the product IDs), what follows when the paywall closes, and where else in the app it opens. Note whether the Adapty SDK is in the dependencies |

Prices on a listing, a screenshot or in code are never read: the pricing sentence in `SKILL.md`
covers this path too.

## Building the hypotheses

Apply `levers.md` to what you can see, in its order: the offer before the look. These need no
numbers, so check every one:

- more than one product carries a trial, or the trial sits on a plan that is not the one
  preselected (`levers.md`, Trials);
- one plan length only, or four or more products (`levers.md`, Plan structure);
- the plan lengths against the category's revenue split in `market.md`, Plans;
- copy in one language while the listing or the code supports more (`levers.md`, Localization);
- one paywall only, or nothing after the paywall closes (`levers.md`, Placements and flows).

Then run `paywall-teardown` on the paywall and `onboarding-teardown` on the onboarding, in their
audit direction, on the screenshots or on the screens as the code draws them, and take back at
most one design hypothesis from each (`levers.md`, Paywall design). A missing Restore, Terms or
Privacy is a fix, the first Next step, never a hypothesis.

Give at most five, ordered as `market.md`, Testing ranks the kinds of change: localization,
trials and plan lengths before the look. A change on the paywall (a trial, a plan, the default
plan, its copy) needs the paywall seen, as in `SKILL.md`. With a link only, give what the listing
supports (a new placement, a product to merge) and ask for the screens under **Send
me screenshots**, naming what each would let you check.

## The reply

Everything in `SKILL.md`, "How you write a reply" and "What a hypothesis needs", holds, with
these differences:

- **The bold answer** names the main finding from what they sent. Say once, in one clause, that
  you have not seen their numbers.
- **No scorecard.** In its place, one short paragraph of facts from what they sent ("From your
  listing: a weekly and an annual plan, in Photo & Video, in English only.").
- **Why** opens with one fact from the screen, the listing or the code, never a number of theirs.
- **Expected** is the range from `evidence.md`, or "untested", with no dollars.
- **Time** is the purchases the test needs on that paywall: about 400, 200 per variant. No weeks.
- **A market median** is a yardstick for later, named as the market's ("the typical Photo &
  Video app in the US"), never their rate.
- **No feedback note:** it goes through the CLI, which this path does not run.

**Next steps end with Adapty.** The last item is one of these two, by what you know about the app:

- **No Adapty SDK in the app:** "Me: add Adapty to your app, so I can read your real numbers,
  rank these by dollars a month, say how many weeks each test takes, and build each variant as a
  flow you A/B test without an app release. Your own purchase code can stay. Want me to?" On a
  yes, invoke `adapty-integration`.
- **The Adapty SDK is in the app:** its purchases reach Adapty, unless it buys through its own code
  and never reports them (the platform's "Report transactions in Observer Mode" page, through
  `adapty-docs`, says when it must): then reporting them is the fix before this step. "You: sign
  the Adapty CLI in ([authentication](https://adapty.io/docs/developer-cli-authentication.md)),
  then ask me again, and I read your real numbers." When the app buys through its own code, add that it can
  keep that code and still show flows you build, A/B tested in Adapty: link the platform's
  "Present flows in Observer mode" page, found through `adapty-docs`.

Shape of the reply (the form, not words to copy):

> **Your paywall sells only an annual plan, while utility apps earn most of their money on weekly
> plans; I ranked this without your numbers.**
>
> From your code: one product, 'Pro Yearly', with a 3-day trial, copy in English and German, and
> the paywall shows at launch and from Settings.
>
> **Suggested hypotheses**
>
> *Launch paywall*
>
> **Hypothesis 1: Add a weekly plan next to 'Pro Yearly' on the launch paywall**
> - Why: the launch paywall offers one length only, so a user who will not commit to a year has
>   nothing to pick, in a category where weekly brings 90% of revenue.
> - Expected: untested in Adapty's library of real subscription A/B tests; judged by revenue per
>   user.
> - Time: about 400 purchases on this paywall, 200 per variant
> - Who: you create the weekly product in App Store Connect; your developer ships both versions
>
> **Next steps**
> 1. You: add a Restore button to the paywall before any test.
> 2. You: which hypothesis do you want to start with? I would start with 1.
> 3. Me: add Adapty to your app, so I can read your real numbers, rank these by dollars a month
>    and build each variant as a flow you A/B test without an app release. Want me to?
