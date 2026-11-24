# Template: a coin balance, spend buttons and a top-up flow

Rules, shape and the reply: [custom-elements.md](../custom-elements.md). This file holds only what
is particular to coins (any virtual currency: gems, credits, energy).

**Fits** an app that sells a virtual currency and wants it in flows: the user's balance that stays
current while the flow is open, a button that spends coins on something with a spinner and a
result, and a top-up flow that sells coin packs when the balance is too low.

**First ask whether the balance changes while the screen is open:** a spend on that screen, or a
purchase after which the flow stays open. When it never does (the screen only shows the balance,
and a spend or a purchase closes the flow), the balance is a custom tag the app passes when it
opens the flow (`build.md`, "Something only the app knows: a custom tag"), with no app view to
write and no app release. Only a balance that changes on the open screen needs the
`currency_balance` box below.

## The usual shape: two flows

1. **A spend flow** on its own placement (out of energy, unlock a level): the balance box and one
   spend button box per option, plus a Close button outside the boxes.
2. **A top-up flow** on a second placement: the same balance box, a line "You need
   `<coins_needed>` more gems" with a custom tag the app fills when it opens the flow (fallback a
   dash), the packs in a product group whose cards each start the purchase, the coin subscription
   on a purchase button when there is one, a Close button and the footer links.
3. **The app** opens the spend flow, spends through its own server, and on a too-low balance closes
   it and opens the top-up flow; after a purchase it reads the new balance and opens the spend
   flow again.

## The boxes

| Box | Type | ID | Height | Fallback |
| :--- | :--- | :--- | :--- | :--- |
| the balance | `currency_balance` | the currency, such as `gems` | fixed, 28–40 pt | the currency's icon |
| a spend button | `spend_button` | the option, such as `energy_refill` | fixed, the button's height (48–56 pt) | a text: "Update the app to refill energy" |

```python
fk.custom_element('currency_balance', 'gems', fixed_h=32,
                  fallback=[fk.icon('Diamond', size_pt=24)])
fk.custom_element('spend_button', 'energy_refill', fixed_h=52,
                  fallback=[fk.text('Update the app to refill energy.', align='center')])
```

- **One Type for every spend button;** the ID tells the app which option it spends on. The same
  `currency_balance` pair in both flows is the same view, with no new app code.
- **The spend button is native, not a builder button with a custom action:** a custom action is
  one way, so the flow could show neither the spinner nor the result. The button's text and look
  come from the app, and change only with an app release.
- **Users without the view see no button,** only the fallback text: keep the Close button outside
  the boxes so they can leave.

## The coin numbers on the cards

**Each pack's coins on its card come from the currency's mapping, never from the brief or a
guess:** no product variable holds them. Offer to read them and invoke `virtual-currencies` on a
yes ("500 gems" for a pack, "300 gems every month" for a subscription). A card that promises other
numbers than the mapping gives is a promise the purchase does not keep. When the store title of
each pack already holds the number ("500 Gems"), the product title variable can show it instead.

## What the app's views do

- **The balance view** observes the balance the app holds and redraws when it changes, so a spend
  or a purchase shows at once. It shows a dash until the app has read a balance.
- **The spend button** sends the option to the app's own server, which spends the coins through
  Adapty's Server API with the secret key (never from the app: anyone with the key can change any
  balance). It shows a spinner while the spend runs, a checkmark when it goes through, and on a
  too-low balance hands the number missing to the top-up flow. Each tap carries its own
  idempotency key.
- **The app's server never credits coins for a mapped product:** Adapty credits them, and the
  user would get them twice.

Docs: the setup page in [Docs per platform](../custom-elements.md#docs-per-platform) and the
virtual currency pages: https://adapty.io/docs/virtual-currencies.md

## On the device

Sign in as a user with no coins and open the spend flow: the balance reads 0. Tap a spend button:
the spinner, then the top-up flow with the number missing. Buy a pack with a sandbox account: the
spend flow opens again with the new balance. Spend: the checkmark, and the flow closes.
