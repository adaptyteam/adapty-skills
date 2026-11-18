# Retention messages: bodies, limits, numbers, refusals

Open this when you write a message, edit one, read its numbers or meet a refusal. The commands and
the yes rules are in `SKILL.md`.

## A message

`messages get` returns `data`: `message_id`, `name`, `type` (`default` or `promo`), `state`
(`in_review`, `live`, `rejected`, `inactive`), `title`, `body`, `image` (`url`, `file_name`,
`alt_text`, or `null`), `header_position` (`above_body` or `above_image`), `products[]` (`id`,
`store_id`, `title`, `period`, `association`: `type` `promo_offer` or `plan_switch`, `id`,
`store_id`, `title`, or `null`), `bullet_points[]` (`bullet_id`, `image`, `alt_text`, `text`),
`localizations[]` (`locale`, `title`, `body`, `status`, `bullet_points[]` with `text`).

`title`, `body` and the bullet texts are the English (`en-US`) source; `localizations` never holds
`en-US`. A message has no environment field: `--mode` is asked only where the server needs it.

A message goes live only after Apple approves every language, English too; until then it stays
`in_review`, and a language Apple has not approved falls back to English. `rejected`: Apple
turned down at least one language; offer a changed version.

## Limits

- `name`, `title`, `body` required. `title` up to 66 characters, `body` up to 144, `alt_text` up
  to 150, a bullet text 1–66 after trimming spaces. Every language has the same limits.
- Up to 5 bullet points, default messages only. Each language has a text for every bullet point.
- `locale` 2–35 characters, no repeat, never `en-US`.
- Header image (default messages only): PNG, 3840 px wide, 160–2160 px tall, no transparency, up
  to 10 MB. Bullet icon: PNG, 1024 × 1024 px, no transparency, up to 10 MB. The CLI checks each
  file before it asks or sends anything; a bad file is exit 2 naming the file and the rule.
- A default message takes no offer; a promo message links one offer or plan switch to each
  product and takes no image and no bullet points. `header_position` and `type` never change.

## Create: the CLI file

`messages create --app <app> --mode <sandbox|production> --file <message.json> [--image <header.png>] --yes`.
The file is the message body; a bullet point names its icon with `image_path` (relative to the
file's folder), never `image_index`:

```json
{
  "name": "Annual: stay",
  "type": "default",
  "title": "Before you go",
  "body": "Keep your plan and your saved progress.",
  "alt_text": "A calendar with a year of progress",
  "header_position": "above_body",
  "products": [{"store_id": "com.example.annual"}],
  "bullet_points": [{"image_path": "icons/progress.png", "alt_text": "A chart", "text": "Your progress stays"}],
  "localizations": [{"locale": "de-DE", "title": "Bevor du gehst", "body": "Behalte deinen Plan und deinen Fortschritt.", "bullet_points": [{"text": "Dein Fortschritt bleibt"}]}]
}
```

A promo product carries its link: `{"store_id": "<product>", "association": {"type": "promo_offer", "store_id": "<offer>"}}`
(or `plan_switch` with the other plan's store id), from the suggest commands.

Over MCP, `messages_create` takes the same fields as parameters (`message_type` for `type`), with
no image and no bullet points; add those afterwards with the CLI or the dashboard.

## Edit: changes only

Name only what changes. The CLI and the tool read the message, merge the change and write the
whole message; what is not named stays (every language, bullet point, icon, the image, the
products).

- Simple fields: `name`, `title`, `body`, `alt_text` (CLI also `--name`, `--title`, `--body`,
  `--alt-text`).
- `localizations[]` by `locale` (adds a new one or changes that one), with `bullet_texts` by
  `bullet_id`.
- `bullet_points[]` by `bullet_id` (`text`, `alt_text`); `products[]` by `store_id` (a new one is
  added; leave out `association` to keep it, `null` removes it).
- Removes, only explicit: `remove_localizations`, `remove_bullet_points`, `remove_products`,
  `remove_image` (CLI also `--remove-image`). Removing a bullet point removes its text in every
  language.
- CLI only: a new header image (`--image <png>`), a new icon (`image_path` on a saved bullet
  point), and a new bullet point: no `bullet_id`, with `image_path`, `text` and `texts` holding its
  text for every language of the message.

A CLI change file (`--file`) that changes the German body and a bullet text, adds a bullet
point and removes French; the file also takes the simple fields and `remove_image`, and refuses a
key it does not know:

```json
{
  "localizations": [{"locale": "de-DE", "body": "Dein Plan und dein Fortschritt bleiben.", "bullet_texts": {"<bullet_id>": "Dein Fortschritt bleibt"}}],
  "bullet_points": [{"image_path": "icons/sync.png", "text": "Sync everywhere", "texts": {"de-DE": "Überall synchron"}}],
  "remove_localizations": ["fr-FR"]
}
```

Refused before anything is sent (exit 2): nothing to change, one object named twice or both
changed and removed, a new image with `--remove-image`, a text for a language or a bullet point the
same change removes, `texts` on a saved bullet point, a new bullet point without `image_path` or
`text`, a field given both as a flag and in the file. Refused after the read, before the write:
removing a language, bullet point or product the message does not have, a `bullet_id` it does not
have, or a language missing a bullet point's text (the refusal names it). Over MCP, a new image or
a new bullet point is refused with the CLI command to name.

## The numbers

`messages list` returns `data[]` with `message_id`, `name`, `type`, `state`, `products_count`,
`started_at`, and six numbers over the message's whole life, plus `meta.pagination` (`page`,
`pages`, `count`) and `meta.exists` (whether the environment has any message at all, filters
aside). An Adapty test message is never in the list.

| Field | Dashboard column | What it is |
|---|---|---|
| `shown` | Shown | cancel-screen views, one per subscription per UTC day: retained, churned and still pending |
| `retained` | Retained users | views followed by a payment for the next period (or the offered switch) before a cancel or expiry |
| `saved_users` | Saved users | views with no cancel within 24 hours |
| `retention_rate` | Retention rate | retained ÷ (retained + churned) × 100; pending views are left out |
| `save_rate` | Save rate | saved users ÷ views older than 24 hours × 100 |
| `saved_revenue` | Saved revenue | what retained subscribers paid after the view, USD, before Apple's commission |

Rates have one decimal and are `0.0` when nothing is counted yet. Saved users above retained is
normal: a saved subscriber whose next payment has not come is not retained yet. A default message
shows fewer views than a promo one on the same product, because it is the fallback. More:
https://adapty.io/docs/retention-messaging-analytics

## Refusals the server sends

| `error_code` | It means | You do |
|---|---|---|
| `app_store_credentials_missing` | no App Store keys | the dashboard's App Store setup first |
| `apple_rm_api_access_denied` | Apple has not approved the app | Apple's request form, with `realtime-url get` |
| `realtime_url_unavailable` | the app has no App Store notification setup | the dashboard's App Store setup |
| `performance_test_required` | production before a passed test | run the test first |
| `performance_test_already_running` | a test runs | wait, read the status again |
| `active_sandbox_transaction_missing` | no active sandbox subscription | the user buys the longest plan in sandbox, then start again |
| `performance_test_request_rejected` | Apple refused the test | a new sandbox purchase, then try again |
| `apple_retention_messaging_error` | Apple failed to answer | try a read again later; never repeat a write blindly |
| `retention_product_claimed` | another message of this type has the product | pick another product, or deactivate the other |
| `retention_default_message_missing` | a promo on a product with no default | create the default first |
| `retention_dependent_promo_messages` | a promo needs a product this change takes away | change or deactivate the promo first |
| `retention_message_invalid_status_transition` | activate a message that is not inactive, or deactivate one that is not live | read its state; say so |
| `retention_bullets_not_allowed`, `retention_image_not_allowed` | bullets or an image on a promo | drop them |
| `retention_default_association_invalid`, `retention_promo_association_invalid`, `retention_message_type_immutable` | the wrong link for the type | fix the links |
| `retention_message_not_found` | no such message in this app | take the id from the list |
| `permission_denied` | not the user's app, or a read-only MCP sign-in | another app, or sign in with write access |
