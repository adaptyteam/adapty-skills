# Adapty Mail tasks

Every section assumes you have the project id and have read `onboarding_status` (see `SKILL.md`,
"Before the first change"). Show the user what each step returned before the next one. Anything
marked **ask** goes through the confirmation in `SKILL.md`.

## Launch a flow

1. **Trigger.** Ask which moment the emails start from, in the user's words, and map it:

   | The user says | Trigger | Campaign purpose | Destination type |
   |---|---|---|---|
   | Installed, never bought | never_purchased | never_purchased | web_paywall |
   | Turned off auto-renew, trial or paid | renewal_cancelled | renewal_cancelled | web_paywall |
   | Payment failed, grace period | billing_issue | billing_issue | web_paywall |
   | Subscription or trial ran out | expired | expired | web_paywall |
   | Got a refund | refunded | refunded | web_paywall |
   | Just bought: get them into the app | purchased | app_activation | deep_link |
   | Just bought: where to cancel | purchased | cancellation_page | cancellation_page |

   Users on a trial are not "never purchased": a trial counts as active. Confirming new
   addresses is double opt-in, see "Settings", never a hand-built flow.
2. **Brand.** `brand_get`. None yet: ask for the App Store or Google Play URL (the first source
   must be a store listing), `brand_source_add`, then poll `brand_source_list` until `in_flight`
   is empty. Show the name, voice and colours; fix with `brand_update`.
3. **Destination.** `destination_list`; reuse one of the type above. Otherwise ask for the HTTPS
   URL and `destination_create`. A destination freezes once a campaign uses it.
4. **Campaign.** `campaign_generate` in English (`language: en`), 3 to 5 emails unless the user
   asks otherwise, `wait_seconds: 50`; poll `campaign_generation_get` while it runs (two to three
   minutes; the run expires after 15). Summarize the plan and each email's text, then
   `campaign_create_from_generation` with a name and the destination. Never fetch the HTML to
   pass it along.
5. **Review.** Offer `campaign_send_test` to the user's own address. Rewrite one email with
   `campaign_generate_email` (the old text is gone) or edit it with `campaign_email_update`.
6. **Segment.** `segment_list`. All users is `00000000-0000-0000-0000-000000000000` and always
   last. A new segment's filters lock after its first use, so get them right before saving.
7. **Flow.** `container_list` for the flow of that trigger. **Ask** with the block, then
   `container_save` with every segment that stays, in order.
8. **Report.** `onboarding_status` shows the flow launched. Say what still blocks sending (data
   sending, a verified domain) and that a live campaign can gain languages and change text but not
   add or remove emails; `campaign_duplicate` makes an editable copy.

Sends go out between 08:00 and 21:00 in the recipient's time zone. A flow change applies to people
who hit the trigger after it; text changes reach everyone still in the sequence.

## Translate a campaign

English is always the source and never a target. `campaign_meta` lists the language codes.

1. `campaign_list`; agree which campaigns and languages. Skip archived ones.
2. Per campaign and language: `campaign_localize` with `persist: true`, `wait_seconds: 50`; poll
   `campaign_localization_get` with `persist: true` until `completed` or `failed`. One language at
   a time per campaign; different campaigns may run side by side.
3. A 409 means the English changed after the run started; a 404 means the run expired. Start it
   again in both cases.
4. Check with `campaign_get` and `language` set to the new code; offer a test send of one email.

A recipient gets their device language, then the language without its region, then English.
Portuguese and Chinese each have two codes: offer both. Regenerating a whole sequence deletes its
translations.

## Sending domain

1. `domain_list`. Five domains at most per project. Already there: go to step 4.
2. Ask for the domain they own: the registrable domain, not a host, ASCII only. `domain_preview`
   checks it and shows the hosts (`mail.` for sending, `go.` for links). **The sending subdomain
   cannot change later without deleting the domain,** so confirm it now.
3. `domain_confirm` with the same values. Repeating it is harmless.
4. `domain_dns_records`; walk the user through publishing each record at their DNS provider, or
   `domain_dns_export` (csv, godaddy, cloudflare, route53) for an import. One SPF record per host:
   replace an existing one, never add a second. On Cloudflare the records must be "DNS only", not
   proxied. DMARC is recommended and does not block verification.
5. `domain_check_verification` after they publish; one check per 10 seconds. It also runs on its
   own, so once propagation is over a failing record is a DNS problem, not a timing one.
6. Suggest a sender name and a reply-to address (`email_settings_update`): **without a reply-to,
   replies to the emails are lost.** Note that leaving reply-to out of the call clears it.

Page: https://adapty.io/docs/mail-sending-domain

## Read performance

1. `analytics_dimensions` first: it gives the dimensions, the ids to filter by and which can be
   grouped or broken down.
2. `analytics_breakdown` for a table, `analytics_timeseries` for a trend (`day`, `week`,
   `month`). `date_to` is inclusive; `breakdown` must differ from `group_by`.
3. For a test: `ab_test_get` for its variation ids, then `analytics_ab_test_funnel`.

Read it right:

- Revenue is in USD and attributed by **last click within one hour**; renewals are never
  credited. It is not lifetime value.
- Opens include Apple Mail Privacy Protection preloads: compare clicks and conversions, not opens.
- Clicks count the call to action, hero image and logo only.
- Name the date range and say counts settle over a few hours.

Page: https://adapty.io/docs/mail-analytics

## A/B test

1. Every variation is a whole campaign of the same purpose; weights add up to 100.
   `ab_test_create` makes a draft that sends nothing.
2. The test runs on one segment row of a flow. The segment must already be in the flow, then
   **ask** and `ab_test_launch`; one live test per row.
3. To end it, read the funnel (above), recommend a winner with the numbers, then **ask** and
   `ab_test_finish` with the winner's campaign. Without a campaign the row is removed. A finished
   test never runs again.

Assignment is random per trigger event, not fixed per user; people already in a sequence stay in
their variation. A different subject line is a second campaign, not a smaller test.

## Why no email

For one person: `profile_list` to find them (by email), then `profile_get` and `profile_journey`.
Check in this order and stop at the first that explains it:

1. Suppressed: unsubscribe, bounce, complaint, or failed address verification. Name the reason;
   only Adapty support can lift it.
2. Already in another marketing flow: a person runs one at a time.
3. Bought or subscribed: the sequence ended, as designed.
4. Held by sending limits during domain warm-up.
5. The trigger never fired: no purchase events reach Mail, or the profile arrived before setup
   was finished.
6. No segment row matched: compare their attributes with the flow's rows, top to bottom.
7. Double opt-in on and the address not confirmed.
8. Outside the 08:00 to 21:00 window in their time zone: it is still scheduled.

For "nothing sends at all": `onboarding_status` (data last received, domain verified, flow
launched), then `container_list` (is there a flow, with a campaign under All users), then
`domain_list` (sending paused?). Apple private-relay and non-ASCII addresses never become profiles.

Page: https://adapty.io/docs/mail-suppression

## Deliverability

`domain_health_scores` (30 days of bounce, complaint and delivery rates and their scores),
`domain_health_bounces`, `domain_health_inbox_placement`, `domain_health_warmup_tier_stats`.
Warm-up moves up the sending tiers on volume alone and never down; there is nothing to speed it up.
Never promise inbox placement. Pausing a domain (`domain_sending_set`) keeps everything and is the
first move when complaints spike: **ask** first.

Page: https://adapty.io/docs/mail-domain-health

## Settings

- **Double opt-in:** `double_opt_in_get`. Turning it on needs a web paywall destination, writes
  and **launches** a confirmation flow for every new profile, and applies only to profiles created
  after that. **Ask** first. Emptying that flow while it is on means new profiles never get
  marketing. Page: https://adapty.io/docs/mail-double-opt-in
- **Segments:** `segment_meta` for the fields and operators. Filters are ANDed, one per field;
  "either A or B" is two segments in two rows. `segment_update` replaces the whole filter list.
  Page: https://adapty.io/docs/mail-segments
- **Sender name and reply-to:** `email_settings_list`, then `email_settings_update` with both
  values.
- **Images:** `media_image_upload` returns a public URL for a logo or an email image.
