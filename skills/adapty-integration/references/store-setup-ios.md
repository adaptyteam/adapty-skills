# iOS Store Setup: Before Your First Sandbox Purchase

All code is written and builds. Before you can test purchases, three external things must be configured. Work through them in order — each step depends on the previous one.

Present this entire checklist to the user with the **exact product IDs and placement IDs from Phase 3 already filled in**. The user follows the steps; you answer questions.

---

## Part 1: Create products in App Store Connect

Adapty products need matching products in App Store Connect before purchases work.

1. Open [App Store Connect](https://appstoreconnect.apple.com) → your app → **Monetization → Subscriptions**.

2. Create a subscription group if none exists (e.g. "Premium").

3. For **each product** created in Phase 3, add a subscription in the group:

   | What to enter | Value |
   |---|---|
   | Reference Name | Any name (e.g. "Monthly Premium") |
   | Product ID | *(the exact `--ios-product-id` used in Phase 3)* |
   | Duration | *(matching the `--period` used in Phase 3)* |

   After creating each subscription:
   - Set a price (any price works for sandbox)
   - Add at least one localization (display name + description)

4. Wait for status to show **Ready to Submit** (usually immediate). No App Review needed for sandbox testing.

---

## Part 2: Connect App Store to Adapty

This is required for Adapty to validate purchases and receive subscription events. Complete all three sub-steps.

### Step 2a: Provide Bundle ID and Apple app ID

1. In App Store Connect → your app → **General → App Information**.
2. Copy the **Bundle ID** from the General Information section.
3. Open [Adapty Dashboard → App settings → iOS SDK](https://app.adapty.io/settings/ios-sdk).
4. Paste the Bundle ID into the **Bundle ID** field.
5. Back in App Store Connect, copy the **Apple ID** (numeric, also on the App Information page).
6. In Adapty Dashboard → iOS SDK, paste it into the **Apple app ID** field.

### Step 2b: Generate and upload In-App Purchase Key

1. In App Store Connect → [**Users and Access → Integrations → In-App Purchase**](https://appstoreconnect.apple.com/access/integrations/api/subs).
   *(Requires Admin or Account Holder role.)*
2. Click **+** next to **Active**.
3. Enter any key name → click **Generate**.
4. Click **Download In-App Purchase Key**. Save the `.p8` file — it can only be downloaded once.
5. Back in the same In-App Purchase list, note the **Key ID** for the key you just created.
6. Note the **Issuer ID** shown above the key list.
7. In [Adapty Dashboard → App settings → iOS SDK](https://app.adapty.io/settings/ios-sdk):
   - Paste the **Issuer ID**
   - Paste the **Key ID**
   - Upload the `.p8` file
8. Click **Save**.

### Step 2c: Enable App Store Server Notifications

Server notifications are required for subscription events (renewals, cancellations, refunds) to reach Adapty.

1. In [Adapty Dashboard → App settings → iOS SDK](https://app.adapty.io/settings/ios-sdk), copy the **URL for App Store server notification**.
2. In App Store Connect → your app → **General → App Information → App Store Server Notifications**.
3. Paste the URL into both:
   - **Production Server URL**
   - **Sandbox Server URL**
4. Save in App Store Connect.

### Step 2d: App Store Connect API key *(only for the dashboard push-to-stores path)*

Skip this unless the user chose to create products **from the Adapty dashboard and push them to the App Store** (Step 4, path C). Linking products that already exist does not need it.

> **This is a different key pair from the In-App Purchase Key in Step 2b.** Both are generated in App Store Connect under Users and Access, and both label their fields **Issuer ID** and **Key ID**, so they are easy to confuse. The In-App Purchase key lets Adapty *validate* purchases; this one lets Adapty *write* products into App Store Connect. Having one does not give you the other.

1. In App Store Connect → **Users and Access → Integrations → App Store Connect API**, generate a key with access to your app.
2. In [Adapty Dashboard → App settings → iOS SDK](https://app.adapty.io/settings/ios-sdk), add it under **App Store Connect API key**.

Full steps: https://adapty.io/docs/app-store-connection-configuration.md

> **The first product you push must be submitted for review manually** in App Store Connect. It is a one-time gate per app — later products skip it — and the status updates in Adapty on its own once review finishes. Until then that product is not purchasable, so sandbox testing waits on it.

---

## Part 3: Give the flow a design *(Flow Builder only — skip for Custom paywall)*

A placement serves a flow, and the flow needs a design before anything renders on a
device. There are five ways to get one, and **the first is the one to offer here** —
you are already an agent in a terminal, which is exactly what it is for:

1. **With this toolchain.** Load the **`flow-generator`** skill, describe the flow in
   plain language, and it authors the config, writes it through the Adapty CLI, publishes
   it, and attaches a placement — so it hands back the developer ID this integration
   needs, already live. https://adapty.io/docs/flow-generator-skill.md
2. **From a template.** Dashboard → Template library → **Use as template** on a card.
   Each template is a complete multi-screen flow, editable element by element.
3. **From a Figma design.** Select frames in Figma and send them to Adapty.
4. **From scratch.** A single blank screen, built from the elements library.
5. **From a legacy paywall.** Recreate an old Paywall Builder paywall as a flow, keeping
   its layout, text and products — the right route when one already exists.

All five: https://adapty.io/docs/paywall-builder-templates.md

Whichever route is taken, **the flow must be published** before its placement serves it.
A flow with unpublished edits sits in `dirty` status and the placement keeps serving the
last published version — so the dashboard shows the new design while the device shows the
old one, with no error anywhere.

> Editing an existing screen in plain language is the **AI Editor**, a different tool from
> anything above: https://adapty.io/docs/flow-ai-editor.md

## Next: run the purchase

Store products exist, the store is connected to Adapty, and the flow has a design. Making
the purchase actually happen — test accounts, device state, running it, verifying it
reached Adapty, and diagnosing it when it does not — belongs to the `purchase-testing`
skill. Hand off there rather than walking the user through it here.
