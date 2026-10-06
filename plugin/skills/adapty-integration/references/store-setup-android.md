# Android Store Setup: Before Your First Sandbox Purchase

All code is written and builds. Before you can test purchases, several external things must be configured. Work through them in order — each step depends on the previous one.

Present this entire checklist to the user with the **exact product IDs and placement IDs from Phase 3 already filled in**. The user follows the steps; you answer questions.

---

## Part 1: Create products in Google Play Console

Adapty products need matching products in Google Play Console before purchases work.

> **Prerequisite:** Google Play Console will not let you create in-app products or subscriptions until a signed AAB with the `com.android.vending.BILLING` permission has been uploaded to any track. If the **Subscriptions** and **In-app products** pages are empty or disabled, do **Part 4, Step 2** first (upload a signed AAB to a closed track), then come back here. This is a one-time gate — after the first upload you can create products normally.

1. Open [Google Play Console](https://play.google.com/console) → your app → **Monetize → Products**.

2. For **subscriptions**, go to **Subscriptions → Create subscription**:

   | What to enter | Value |
   |---|---|
   | Product ID | *(the exact `--android-product-id` used in Phase 3)* |
   | Name | Any name (e.g. "Monthly Premium") |
   | Description | Short description |

   After creating the subscription:
   - Add a **base plan** — the base plan ID must match the `--android-base-plan-id` used in Phase 3
   - Set a billing period matching the `--period` used in Phase 3
   - Set a price (any price works for testing)
   - Activate the base plan

3. For **one-time products (non-consumable)**, go to **In-app products → Create product**:

   | What to enter | Value |
   |---|---|
   | Product ID | *(the exact `--android-product-id` used in Phase 3)* |
   | Name | Any name |
   | Price | Any price |

   Activate the product after creation.

---

## Part 2: Connect Google Play to Adapty

This is required for Adapty to validate purchases and receive subscription events. Complete both sub-steps.

### Step 2a: Upload a Google Play Service Account key

Adapty uses a Service Account key to communicate with Google Play. If you don't have one:

1. Open [Google Cloud Console](https://console.cloud.google.com) → select or create the project linked to your Google Play account.
2. Go to **IAM & Admin → Service Accounts → Create Service Account**.
3. Give it a name (e.g. "Adapty"), click **Create and Continue**.
4. Skip role assignment → click **Done**.
5. In the service account list, click the account you just created → **Keys → Add Key → Create new key → JSON → Create**.
6. The `.json` file downloads automatically. Save it — you'll upload it to Adapty.
7. In [Google Play Console → Setup → API access](https://play.google.com/console/developers/api-access):
   - Link to the Google Cloud project from step 1 (if not already linked)
   - Under **Service accounts**, find the account you created → click **Grant access**
   - Grant these permissions: **View financial data**, **Manage orders and subscriptions**
   - Click **Apply**
8. In [Adapty Dashboard → App settings → Android SDK](https://app.adapty.io/settings/android-sdk):
   - Upload the `.json` key file
   - Click **Save**

### Step 2b: Enable Real-Time Developer Notifications (RTDN)

RTDN is required for subscription events (renewals, cancellations, refunds) to reach Adapty.

1. In [Adapty Dashboard → App settings → Android SDK](https://app.adapty.io/settings/android-sdk), copy the **Google Cloud Pub/Sub topic** value.
2. In [Google Play Console → Monetize → Monetization setup](https://play.google.com/console/developers/app/monetize-setup):
   - Paste the topic into the **Real-time developer notifications** field
   - Click **Send test notification** to verify the connection → you should see a success message
   - Click **Save**

> If "Send test notification" returns an error, the Service Account likely doesn't have Pub/Sub permissions. In Google Cloud Console → IAM, add the `Pub/Sub Publisher` role to the service account.

### Step 2c: What the push-to-stores path needs *(only if products are created from the Adapty dashboard)*

Skip this unless the user chose to create products **from the Adapty dashboard and push them to Google Play** (Step 4, path C). Linking products that already exist does not need it.

> **Unlike iOS, there is no second key.** Apple's push path needs an App Store Connect API key separate from its In-App Purchase key; Google Play's push works off the **same service account** from Step 2a. What enables it is one of the four permissions granted there: **Manage store presence** — that is the write grant. If only the read and order permissions were granted, reads and validation work while the push fails.

So there is nothing extra to configure here — just confirm Step 2a granted all four permissions, not a subset.

> **The AAB gate still applies.** Google Play blocks in-app product creation for an app until a signed AAB carrying `com.android.vending.BILLING` has been uploaded to a track. That restriction belongs to Play rather than to any one UI, so expect it to refuse a dashboard push as well — treat it as applying until you see otherwise. Upload the build first (Part 1's prerequisite note), then push.

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
