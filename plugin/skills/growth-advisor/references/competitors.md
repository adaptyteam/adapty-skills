# Competitors

Price rules compare the app with the apps the user competes with. Nothing in the Adapty CLI
returns competitors, their prices or category benchmarks, so this file is how you get the one
part you can get: competitor prices, from a list the user confirms or, when nobody can, from
your own picks, labelled as such.

## 1. Agree on the list

Propose 3-5 apps, then ask the user to confirm, remove or add.

- **Where your proposals come from,** in this order: apps the user names; the "You Might Also
  Like" apps on the app's own App Store page; a search of the App Store for the app's category,
  which also gives each app's id:

  ```bash
  curl -s "https://itunes.apple.com/search?term=${TERM}&entity=software&country=${COUNTRY}&limit=10"
  ```

  `TERM` is a few words for what the app does (`meditation+sleep`); each result's `trackId` is
  the `APP_ID` below. Pick apps in the same category that sell subscriptions. Each result's
  `userRatingCount` is a rough size signal: category leaders price higher than most apps, so
  include at most one and fill the rest with apps nearer the user's own size.
- **Shape of the ask** (an example of the form, not words to copy):

  > To compare your prices I need the apps you compete with. From your App Store page I'd pick
  > App A, App B and App C. Are those right, and is anyone missing? You can also skip
  > this, and I'll leave price changes out of the audit.

- **Fewer than 3 confirmed:** make no price recommendation. Say price tests need at least three
  competitors to compare against, and keep going with the other levers.
- **Nobody can answer** (the user said they are away, or the run is unattended): use your own
  3-5 picks and carry on to step 2. In the reply, name them as your picks ("compared with apps I
  picked: …"), make any price direction conditional on the user agreeing with the list, and ask
  them to confirm or replace it.

## 2. Read their prices

Each app's public App Store page lists up to ten in-app purchases with their names and prices,
for one storefront:

```bash
curl -sL -A "Mozilla/5.0" "https://apps.apple.com/${COUNTRY}/app/id${APP_ID}" -o page.html
```

`COUNTRY` is the two-letter storefront of the app's main market (`us`, `de`); `APP_ID` is the
number in the app's App Store link. Then read the text after `In-App Purchases`.

**If the store says no, stop.** An `HTTP 429`, or a page of about 1 KB with no `In-App
Purchases` section, means Apple is limiting requests. Do not retry in a loop, and never change
the user agent or route around the limit (for example by posing as a search crawler). Use
whatever pages you already have, fall back to the market medians in `market.md`, and say in the
reply that the store limited the lookup and the user can try again later.

What the page does **not** say, and what you do about it:

| Missing | What you do |
|---|---|
| The plan length. "Premium $79.99" and "Premium $69.99" can both be annual. | Infer the length from the name and the price level, mark each inferred one as a guess, and show the user your table before using it. |
| Trials and intro offers. | Not on the page. Ask the user, or say you could not see them. |
| Which plan the competitor's paywall shows first. | Not on the page. Only the competitor's paywall shows it; the user can screenshot it. |
| Google Play prices. | Not available this way. Say so for Android-only questions. |

The list is the top purchases, not all of them; an old price that is still sold can sit next to
the current one. When two prices plausibly fit one length, use the one the user confirms, or the
lower one and say so.

## 3. Use them

- **Show the table in the reply,** whether or not the user confirmed the list: one row per app,
  its plan lengths and prices, each inferred length marked as a guess. A range or an average
  alone cannot be checked, and the guesses are what the user is most likely to correct.

- **Average per plan length** across the confirmed competitors that sell that length. Never one
  outlier, and never one length's competitors for another length's price.
- Record which competitors sell which lengths; the plan-structure rules (`levers.md`) count them.
- In the reply, "your competitors" means a list the user confirmed. Your own picks are "the apps
  I compared you with" until they do. A competitor average is
  never a category average; the market medians in `market.md` are a separate number, named as
  such.
- **No confirmed competitors:** the median price for the app's region and category in
  `market.md` is a sanity check, not a price direction. Say a price sitting far above or below it
  is worth a test, and name it as the market median.
