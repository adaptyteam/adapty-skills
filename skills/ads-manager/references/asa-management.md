# Apple Search Ads — Managing Campaigns

Everything under `adapty asa` is scoped to the company behind the token, not to one app.
No command in this file takes `--app` to select scope — the one exception is `--app` as a
list filter, covered in [Scope filters](#scope-filters). Ids are the UUIDs printed by the
matching list command; never invent one.

All `list` commands paginate: `--page` (default `1`), `--page-size` (default `100`, max
`1000`) — prefer one big page over a pagination loop. Counting entities costs nothing
extra: every list response carries `meta.pagination.count`, so `--page-size 1` answers
"how many X do I have" without walking pages.

Every `list` and `get` command in this file returns metadata only, no metrics. Every number
— spend, ROAS, or anything else — comes from `asa metrics`.

## Account and discovery

| Command | Notes |
|---|---|
| `asa whoami` | Company, how access was granted, Apple connection state. Run this first. No connected Apple Ads account or no active Ads Manager subscription answers `402 ads_manager_subscription_required` on every other `asa` command. |
| `asa connect [--no-wait]` | Prints the Apple authorization link and waits for the link to be completed; `--no-wait` returns immediately instead of waiting. |
| `asa apps list` | Apps promoted in Apple Search Ads; pagination only. Its rows supply `--adam-id` for `campaigns create`. |
| `asa orgs list` | Apple Search Ads organizations; pagination only. Each row carries two identifiers, not interchangeable: `internal_id` (a UUID) and `org_id` (Apple's numeric id). `--org` on `campaigns create` takes `internal_id` — passing the numeric `org_id` fails with "Invalid org ID format." Each row also carries `payment_model` (`LOC`/`PAYG`), which tells you whether campaigns in that organization need Invoicing Options — see [Line of credit](#line-of-credit-organizations). |

## Campaigns

| Command | Flags | Notes |
|---|---|---|
| `asa campaigns list` | scope filters only | Metadata only. |
| `asa campaigns get <id>` | positional UUID | Metadata only. |
| `asa campaigns create` | `--org`, `--name`, `--adam-id`, `--country` (repeatable), `--daily-budget`; optional `--status` (`ENABLED`/`PAUSED`, no default), `--budget` (lifetime), `--target-cpa`, `--bidding-strategy`, `--supply-source` (repeatable, default `APPSTORE_SEARCH_RESULTS`), `--billing-event` (`IMPRESSIONS`/`TAPS`, default `TAPS`), `--ad-channel-type` (`DISPLAY`/`SEARCH`, default `SEARCH`), and the five `--invoice-*` flags together (`--invoice-advertiser`, `--invoice-order-number`, `--invoice-contact-name`, `--invoice-contact-email`, `--invoice-billing-email`) | `--org` takes the UUID (`internal_id`) from `asa orgs list`, not that row's numeric `org_id`; `--adam-id` comes from `asa apps list`. `--status` has no default — pass `--status PAUSED` to launch without spending until you enable it. `--target-cpa` must be lower than `--daily-budget`. The response carries `serving_status` and `serving_state_reasons`; on `NOT_RUNNING` the command prints the reason and the command that fixes it — see [Max Conversions](#max-conversions-campaigns) and [Line of credit](#line-of-credit-organizations). |
| `asa campaigns update <id>` | at least one of `--name`, `--status`, `--country`, `--daily-budget`, `--budget`, `--target-cpa`, `--bidding-strategy`, or the five `--invoice-*` flags together | The `--invoice-*` flags replace the stored Invoicing Options as a whole — pass all five, since a partial set exits `2` before anything reaches Apple. |
| `asa campaigns bulk-create` | exactly one of `--file` (JSON structure, `-` for stdin) or `--from-file` (Apple Ads template); `--org-id` required with `--from-file`; optional `--preview`, `--no-wait`, `--poll-interval` (default `5`), `--timeout` (default `900`) | Creates a whole structure as one queued operation — see [Bulk operations](#bulk-operations). |
| `asa campaigns bulk-status <operation-id>` | positional UUID, printed by `bulk-create`; pagination flags page the per-object log | One operation's counts and the per-object log, each failure with its reason. |
| `asa campaigns bulk-list` | optional `--status` (`pending`/`running`/`success`/`partial`/`failed`, repeatable), `--app` (UUID), `--created-from`/`--created-to` (`YYYY-MM-DD`); pagination | This company's bulk operations, newest first, one row per operation with its verdict — no per-object detail. Use it to recover an `operation_id` you lost, then read it with `bulk-status`. A cheap catalog read. |

### Bulk operations

`bulk-create` replaces a loop over `campaigns create` + `ad-groups create` + `keywords add`. The
structure nests: `campaigns[]`, each with `negative_keywords[]` and `ad_groups[]`, and each ad group
with `keywords[]`, `negative_keywords[]` and `ads[]`. The command counts those nodes and shows the
counts in its confirmation prompt, so read that line before answering.

Two inputs, and they take different org identifiers. `--file` is the JSON structure — the request body
itself — and `--file -` reads it from stdin. `--from-file` takes a native Apple Ads template
(`Campaign_And_Adgroup_Template.xlsx` or a keywords `.csv`), converts it server-side first, and needs
`--org-id`: **the numeric `org_id`, not the `internal_id` UUID that `campaigns create --org` takes.**
That is the one place in this file where a command wants Apple's number. Conversion problems print with
their sheet, row and column; an error there exits `2` and creates nothing.

`--preview` prints the converted structure and stops without creating anything. Preview every template
before submitting it: a bulk operation has no undo, and there is no delete in the `asa` topic, so a
structure that is half wrong leaves objects you cannot remove. The printed preview is also the fastest
way to get a starting JSON file — save it, edit it, submit it with `--file`.

By default the command polls until the operation reaches `success`, `partial`, or `failed`, printing
progress as the counts change. `partial` lists every object that was not created with Apple's reason,
and the objects that did succeed stay. `--no-wait` prints the `operation_id` and returns, for a
structure too large to sit through. `--timeout` (default `900` s) only ends the *polling* — the
operation keeps running on the server, and the command tells you to read it later with `bulk-status`.
A timeout is therefore not a failure and not a reason to resubmit.

The 15-item practice for `keywords add` does not govern a bulk structure, which is one operation with
per-object failure reporting rather than an all-or-nothing batch. What replaces it is the preview.

### Max Conversions campaigns

A campaign created with `--bidding-strategy MAX_CONVERSIONS` succeeds and then sits at
`serving_status: NOT_RUNNING`, `serving_state_reasons: ["AUTOMATED_KEYWORDS_REQUIRED_AD_GROUP_MISSING"]`,
until it owns an **automated ad group**. The two writes are one unit — never create the campaign alone:

```sh
adapty asa campaigns create --org <org-uuid> --name <name> --adam-id <adam-id> --country <code> --daily-budget <amount> --bidding-strategy MAX_CONVERSIONS --idempotency-key <run>-camp
adapty asa ad-groups create --campaign <campaign-uuid> --name <name> --automated --idempotency-key <run>-ag
```

`--automated` sends `automated_keywords_required: true` and `automated_keywords_opt_in: true`, so it
cannot be combined with `--automated-keywords`. Apple schedules and runs that ad group itself: it sends
no `start_time` (`--start-time` alongside it exits `2`), it must stay `ENABLED` (`--status PAUSED` exits
`2` — pause the campaign instead), and `--default-bid` becomes optional. A plain ad group does not
satisfy the requirement, not even with `--automated-keywords`.

### Line of credit organizations

When an organization's `payment_model` is `LOC` it bills by line of credit, and Apple requires
Invoicing Options on every campaign in it. Without them the campaign is created and sits at
`serving_status: NOT_RUNNING`, `serving_state_reasons: ["MISSING_BO_OR_INVOICING_FIELDS"]`. Pass all
five flags in one call — a partial set exits `2` before anything reaches Apple:

```sh
adapty asa campaigns create --org <org-uuid> --name <name> --adam-id <adam-id> --country <code> --daily-budget <amount> --invoice-advertiser <advertiser> --invoice-order-number <number> --invoice-contact-name <name> --invoice-contact-email <email> --invoice-billing-email <email> --idempotency-key <run>-camp
```

The same five flags on `campaigns update <id>` set the Invoicing Options on a campaign that already
exists. They map to `loc_invoice_details`: advertiser → `client_name`, order number → `order_number`,
contact name → `buyer_name`, contact email → `buyer_email`, billing email → `billing_contact_email`.
Read `payment_model` from `orgs list` before a launch; do not assume `PAYG`.

## Ad groups

| Command | Flags | Notes |
|---|---|---|
| `asa ad-groups list` | scope filters only | Metadata only. |
| `asa ad-groups get <id>` | positional UUID | Metadata only. |
| `asa ad-groups create` | `--campaign`, `--name`, `--default-bid` (optional with `--automated`); optional `--automated` | Apple also requires a pricing model and a start time; the CLI defaults `--pricing-model` to `CPC` (the only other option is `CPM`) and `--start-time` to today if you don't pass them. `--automated` creates the automated ad group a Max Conversions campaign needs — see [Max Conversions](#max-conversions-campaigns). |
| `asa ad-groups update <id>` | at least one field | The campaign is resolved server-side and is never passed on update. |

## Ads

| Command | Flags | Notes |
|---|---|---|
| `asa ads list` | scope filters only, **no `--app`** | Ads hang off ad groups, not apps directly — filter by `--ad-group` or `--campaign` instead. Metadata only. |
| `asa ads get <id>` | positional UUID | `serving_state_reasons` in the response explains a non-running ad. |
| `asa ads create` | `--ad-group`, `--creative-id`, `--name` | The creative id comes from `asa creatives list`. |
| `asa ads update <id>` | `--name` and/or `--status` | The creative and the parent ad group are fixed at creation and cannot be changed. |

## Keywords

| Command | Flags | Notes |
|---|---|---|
| `asa keywords list` | scope filters only | Metadata only. Filter by `--ad-group` — unfiltered, this is the widest read in the surface. |
| `asa keywords recommend` | `--adam-id` (Apple App Store ID from `asa apps list`), `--type` (`brand` / `generic` / `competitor`) required; optional `--country` (two-letter ISO code, repeatable, default every country in the pool) | A read: ready-made keyword pools that Adapty computes for one of your apps — the same sets the dashboard's campaign setup uses. It takes no scope filters and no pagination. `brand`: the app's own brand terms, their spelling variants, and organic terms that carry the brand; the text output also prints `brand_terms`. `generic`: non-brand terms the app and its top organic competitors rank for, minus every known brand term; `relevance_tier: top_organic` marks terms where the app already ranks in the organic top 10. `competitor`: one pool per competitor selected for the app in the dashboard's Autopilot setup — empty until someone selects competitors there, so an empty `pools` list is an answer, not an error. Read `status` before the list: `ready` is usable, `building` means retry in about a minute, `empty` is a real answer, `failed` means retry another day. A cold `brand` or `generic` call builds the pool during the request and can take tens of seconds — see [Request budgets](#request-budgets). Terms carry `country`, `popularity`, `score` and `median_organic_rank`, but no bid and no match type: those are the user's decision, then `asa keywords add` loads the chosen terms at 15 per call. |
| `asa keywords add` | `--ad-group` plus `--text` (repeatable) and/or `--from-file`; optional `--bid`, `--match-type` (`BROAD`/`EXACT`, default `BROAD`), `--status` (`ACTIVE`/`PAUSED`, default `ACTIVE`) | Batch call, capped at 100 keywords per call — the skill's own practice caps a single call lower, at 15 (see `SKILL.md`'s `## Never`). `--from-file` reads one keyword per line, trims each line, drops blank lines, and combines the result with any `--text` values. Default match type is `BROAD`, which widens spend beyond exact matches; pass `--match-type EXACT` to narrow it. |
| `asa keywords update <id> [<id>...]` | one or more positional ids | The same change (e.g. `--bid`, `--status`) is applied to every id in the list. `--text` is only valid when a single id is given — you cannot bulk-rename keyword text. |

## Negative keywords

| Command | Flags | Notes |
|---|---|---|
| `asa negative-keywords list` | scope filters only | Metadata only. `ad_group_id` is empty (`null`) on campaign-level rows; `--campaign-level-only` keeps only those rows. |
| `asa negative-keywords add` | exactly one of `--ad-group` / `--campaign`, plus `--text` (repeatable); optional `--match-type` (`BROAD`/`EXACT`, default `EXACT`), `--status` (`ACTIVE`/`PAUSED`, default `ACTIVE`) | `--all-ad-groups` applies the negative keyword to every ad group in the campaign and requires `--campaign`. Same 100-item batch cap as `keywords add`, and the same 15-per-call practice (see `SKILL.md`'s `## Never`). Default match type here is `EXACT` — the opposite of `keywords add`'s `BROAD` default. |

## Product pages

| Command | Flags | Notes |
|---|---|---|
| `asa product-pages list` | see Scope filters | Read-only, metadata only. |
| `asa product-pages sync [--adam-id]` | `--adam-id` optional | Queued rather than awaited; the response's `replayed` field is what tells the two outcomes apart. `replayed: false` means this call just queued a sync (the CLI prints "Sync queued."). `replayed: true` means one was already running and this call queued nothing new (the CLI prints "Already running; nothing new was queued."). The response also carries `state`, `sync_id`, and `accepted_at`. |

## Creatives

| Command | Flags | Notes |
|---|---|---|
| `asa creatives list` | see Scope filters | Yields the Apple `creative_id` that `ads create` needs. |

## Automations

| Command | Flags | Notes |
|---|---|---|
| `asa automations list` | pagination only, no scope filters | `status` in the response is `1` for active, `0` for stopped. |
| `asa automations get <id>` | positional UUID | Same `status` convention as `list`. |
| `asa automations create` | `--file rule.json` (or `--file -` for stdin); for an `add-as-keyword-to` rule also the action flags below | `--run-now` queues the rule's first run immediately after creation. The CLI checks that the file carries exactly one `actions` entry and exits `2` otherwise, on every create — the API stores one action and one condition per rule, and the one-condition half is enforced server-side, not here. |
| `asa automations update <id>` | one or more of `--stop`, `--start`, `--name`, `--file`, or an action flag | If you pass `--file`, that file must not carry `internal_id` — the CLI treats a JSON body with `internal_id` in it as an error, since that field is server-assigned. An action flag makes this a read-modify-write; see below. |
| `asa automations run <id>` | `--dry-run` optional | Queued; the command prints a run id. `--dry-run` evaluates the rule and logs what it would do without touching Apple. |
| `asa automations runs <id>` | positional UUID | Past runs for this automation, dry runs included. |

### The add-as-keyword action flags

**Never hand-write an `add-as-keyword-to` action's `params`, and never copy one from another
rule.** `params` is a union the API resolves by *shape*, with no discriminator: a key
belonging to a different action makes it pick that action's variant, silently drop the rest,
and still answer `200`. The classic result is a rule that reads "Add as keyword to 0 ad
groups" — the ad group is right there in the JSON, under the wrong key, and the rule does
nothing every time it runs. On this action the ad groups live in `targets.internal_ids`,
never in `ids`.

Pass these flags instead and let the CLI build the block. They fill in or override
`actions[0].params`, and they exit `2` on the mistakes the API would have accepted: an
action that is not `add-as-keyword-to`, a flag that does not belong to the rule's
`operate_with`, and a params block left incomplete — no target ad groups, no match type, no
bid source, or `set_to` with no bid. The error names the missing flag and why it is needed.

| Flag | Lands in | Values |
|---|---|---|
| `--target-ad-group` | `targets.internal_ids` | repeatable UUID; **required** — a rule with none does nothing |
| `--match-type` | `match_type` | `BROAD`, `EXACT`; **required**, the API has no default |
| `--cpt-bid-type` | `cpt_bid.type` | `ad_group_default_bid`, `set_to`, `search_term_current_cpt`, `keyword_current_bid`; **required**, the API has no default |
| `--cpt-bid` | `cpt_bid.value` | the bid itself with `set_to` (required there); a **percent markup** on the entity's own bid with `search_term_current_cpt` / `keyword_current_bid`; rejected outright with `ad_group_default_bid` |
| `--negate` / `--no-negate` | `negate` | `--negate ad-group` or `--negate campaign` adds the term as a negative at that level; `--no-negate` leaves none. Mutually exclusive, `search-term` rules only |
| `--skip-enable-duplicates` | `skip_enable_duplicate_keywords` | boolean, default off — `search-term` rules only; off means an existing keyword in the target ad group gets *enabled* |
| `--pause-original` | `pause_in_original_ad_group` | boolean, default off — `targeting-keyword` rules only |

Which flags apply is decided by the rule's own `operate_with`, and the wrong half is
refused rather than ignored:

| `operate_with` | Applicable |
|---|---|
| `search-term` | `--target-ad-group`, `--match-type`, `--cpt-bid-type`, `--cpt-bid`, `--negate`/`--no-negate`, `--skip-enable-duplicates` |
| `targeting-keyword` | `--target-ad-group`, `--match-type`, `--cpt-bid-type`, `--cpt-bid`, `--pause-original` |

Any other `operate_with` — `campaign`, `ad-group` — has no `add-as-keyword-to` action, so
these flags exit `2` there too.

**On `update`, an action flag turns the call into a read-modify-write.** The CLI fetches the
rule, rebuilds `actions[0].params` from the flags and writes the whole `actions` list back,
because the API replaces `actions` wholesale. Two things follow: an edit someone made in the
dashboard between the read and the write is overwritten, so say so before running it; and
this is also the way to *repair* a rule whose stored `params` carry the wrong shape, since
the rebuild keeps only what fits and takes the rest from the flags.

```sh
$ADAPTY asa automations create --file rule.json \
  --target-ad-group <ad-group-uuid> --match-type EXACT \
  --cpt-bid-type search_term_current_cpt --negate ad-group \
  --idempotency-key <key>
```

## Scope filters

Filters narrow the query itself, not the printed page: an unfiltered `asa keywords list`
pages through the whole account, while one ad group's list is a handful of rows. Always
scope a read.

| Filter | Lists that accept it |
|---|---|
| `--campaign-group` | campaigns, ad groups, ads, keywords, negative keywords, search terms, product pages, creatives — not `apps list`, `orgs list`, or `automations list` |
| `--app` | campaigns, ad groups, keywords, negative keywords, search terms, product pages, creatives |
| `--campaign` | ad groups, keywords, negative keywords, search terms, ads |
| `--ad-group` | keywords, negative keywords, search terms, ads |
| `--status` | campaigns, ad groups, ads (`ENABLED`/`PAUSED`), keywords (`ACTIVE`/`PAUSED`) |
| `--search` | campaigns, ad groups, keywords, negative keywords, search terms, ads — not product pages, creatives, `apps list`, `orgs list`, or `automations list` |
| `--campaign-level-only` | negative keywords only |

Id filters (`--campaign-group`, `--app`, `--campaign`, `--ad-group`) are repeatable and take
UUIDs. `--app`, `--campaign`, and `--ad-group` take the UUIDs printed by the matching list
command (`apps list`, `campaigns list`, `ad-groups list`). There is no `campaign-groups
list` — organizations and campaign groups are the same thing here, so `--campaign-group`
takes the `internal_id` UUIDs printed by `asa orgs list`. An id owned by another company
matches nothing — the page comes back empty rather than erroring, so an empty result is
not proof the entity doesn't exist anywhere, only that it isn't yours.

`asa ads list` has no `--app` filter, because ads hang off ad groups, not apps — use
`--ad-group` or `--campaign` to scope it instead.

## Status

```
Campaigns, ad groups, ads:  --status ENABLED | PAUSED
Keywords:                   --status ACTIVE  | PAUSED
```

The keyword enum is different from every other entity's — `ACTIVE`/`PAUSED`, not
`ENABLED`/`PAUSED`. There is no `DISABLED` value anywhere in the `asa` surface, on any
entity.

## Request budgets

Every `asa` command is rate limited per company, not per token:

| Commands | Budget |
|---|---|
| catalog lists and gets, automation reads | 120/min |
| `keywords list` | 30/min, burst 5 per 10s, its own 2-concurrent pool, 60s server timeout |
| `keywords recommend` | 10/min, one in-flight `brand`/`generic` build at a time, `Retry-After: 5` on `cli_analytics_busy` |
| all writes | 20/min |
| template conversion (`bulk-create --from-file`) | 10/min, one conversion at a time |
| `whoami` | 60/min |

`keywords list` is the heaviest metadata read in the surface — its own budget is on top of
the account-size reason to filter it in Scope filters. `metrics`, `metrics overview`,
`search-terms list`, and `competitors summary` share a separate analytics pool with its own
budget and its own `429 cli_analytics_busy`; that pool and its numbers live in the metrics
reference, not here. `keywords recommend` answers the same `cli_analytics_busy` code from a
different, one-slot pool of its own: a busy `brand`/`generic` build answers with this
section's `Retry-After: 5`, not the metrics pool's numbers.

A budget running out answers `429 cli_rate_limit_exceeded` with the wait in `Retry-After` —
a different code from `cli_analytics_busy` (that other pool's concurrency cap) and from
`cli_cooldown_active` (the token-wide escalation described next). The CLI already waits
out and retries the first 429 of any command on its own — the exact `Retry-After`, up to
60 seconds, cool-downs excluded — so a 429 that reaches you means the retry also failed and
the budget is genuinely exhausted; don't loop, wait for the window to reset or reduce the
call. Twenty rejections within 5 minutes escalate any of these commands into
`429 cli_cooldown_active`, a cool-down scoped to the token (5m → 30m → 3h) that stops every
`asa` command from that token, not just the one that tripped it.

## Writes and idempotency

- Every mutating command prints the exact request body it will send and waits for
  confirmation. `--yes` skips the prompt. Under `--json` or in a pipe, the command refuses
  rather than hanging.
- Every write sends an `Idempotency-Key`. It is auto-generated per invocation; one network
  error is retried automatically with the same key, so a request that died on the wire is
  never applied twice.
- `--idempotency-key <key>` pins the key yourself. A repeat with the same key and body
  within 24 hours replays the stored result and prints "Already applied earlier — showing
  the stored result." instead of creating a second entity.
- Same key, different body: `422 cli_idempotency_key_reuse`. Concurrent duplicate:
  `409 cli_idempotency_in_progress`.
- Keyword and negative-keyword calls are batches: one bad id fails the whole batch before
  Apple is called; Apple may still reject individual items within an otherwise valid batch,
  each with its own reason.
- Money flags take a bare amount (`--daily-budget 50`); `--currency` defaults to `USD`.
- There is no delete command in the `asa` topic.
