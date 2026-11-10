# The version history of a flow

Read this when the user asks about an earlier version of a flow: to see the versions, to look at
one, to go back to one, or to try one in a separate flow.

`SKILL.md` owns the edit itself (phase 2: fetch, phase 5: the approval and the write). This file
owns the history: what it keeps, how to read it, and the two ways to work from an earlier version.

## What the history keeps

- **Each published version, and the draft.** A flow has one draft or none. Each publish adds a
  version; each save to the draft changes the draft in place. **The history keeps no draft saves**,
  so the content of a draft before a save comes back only from the copy phase 2 kept.
- **A version never changes when you read it, restore it or duplicate it.** A restore writes the
  draft; a duplicate makes a new flow.
- **Nothing here publishes.** After a restore the users still see the live version until someone
  publishes; that stays the user's decision.

## When the CLI has no history commands

Before the first command of this file, check that it exists:

```bash
$ADAPTY flows versions --help      # before a list, get, preview, restore or rename
$ADAPTY flows duplicate --help     # before a duplicate
```

If `--help` says the command does not exist, try it once as `npx --yes adapty@beta flows versions
--help` (or `flows duplicate --help`). If that works, use that form for the reads (list, get,
preview); a restore, a rename or a duplicate with it runs only after you tell the user it is a beta
release and they say yes. Never decide it from a version number. If it is still missing:

- **No `flows versions`:** this CLI cannot read or restore the history. The draft from before your
  first write comes back from the phase-2 backup (`SKILL.md` phase 5, "Restoring from the backup").
  Say that an earlier published version cannot be read from this CLI.
- **No `flows duplicate`:** the copy cannot be made safely from this CLI. Never make it with
  `flows create` and a write ([Look at one version](#look-at-one-version) says what that drops;
  the one exception is an archived flow the user will not restore,
  [SKILL.md phase 2](../SKILL.md#2-new-flow-or-existing-flow)). Ask the user to copy the flow in
  the dashboard (its copy action makes the same copy; for an A/B test copy of a `dirty` flow, tell
  them to copy the live content), then find the copy's id in `flows list` and go on with it.
  Before a restore, `flow.draft-before-restore.json` (step 4) still keeps the draft.

## Unsaved changes come first

Before you switch your work to another version (restore it, or duplicate it and edit the copy),
check that your working file holds nothing the draft does not:

```bash
# the summary "0 removed, 0 changed, 0 added" means nothing is unsaved
python3 references/diff-config.py flow.working.json draft.json
```

No working files (nothing fetched in this run): nothing is unsaved; go on. Any other summary is
work the user has not saved. Never drop it silently: ask one question with
three answers, and wait.

> You have changes that are not saved to the flow yet: <one line of what they are>.
> 1. Save them first, then go to <version title>.
> 2. Discard them and go to <version title>.
> 3. Stay on the current work.

That is the shape, not words to copy. On 1, run phase 5 (the approval ask and the write), then
come back here. On 2, go on; your next fetch replaces `draft.json`. On 3, do nothing.

A look at a version (the list, `versions get`, `versions preview`) changes no file of yours and
needs no question.

## Read the list

```bash
$ADAPTY flows versions list <FLOW_ID> --app <APP_UUID> --json            # newest first
$ADAPTY flows versions list <FLOW_ID> --app <APP_UUID> --search "friday" --json
```

Each row has `flow_version_id`, `version`, `name` (null when not named), `title` (the name, or
"Version N"), `state` (`draft`, `live` or `previous`), `is_current`, `publication_status`,
`published_at`, `created_at`, `updated_at` (an integer in ms: the restore token) and
`last_edited_by`. `--search` keeps the rows whose title has the text, in any case.

**Show the date by state:** `published_at`, else `created_at`, for `live` and `previous` (a
`previous` row that was never published has no `published_at`); `created_at` for the draft. Show
each row as its title, its state, that date and who changed it last, never its id. A draft that
publishes or failed to publish says so beside it.

**A flow that was never published has one row, the draft, or none.** There is no earlier version
to go back to: say "History will appear after the first publish." and use the phase-2 copy.

## Look at one version

```bash
$ADAPTY flows versions get <FLOW_ID> <FLOW_VERSION_ID> --app <APP_UUID> --output version.json
$ADAPTY flows versions preview <FLOW_ID> <FLOW_VERSION_ID> --app <APP_UUID>   # a link for the phone
```

`get` gives the full content of the version (every layout, the remote configs, the paywalls) with
`--json` or in the `--output` file; its text prints only the row and the `preview_url`. `--output`
replaces an existing file only on a yes (`--yes` without a terminal). `preview` prints the bare
device-preview link of that version (`--json`: `flow_version_id` and `preview_url`), so the
user can open it on a phone without a restore; give it to them as
[preview.md → Offering the device-preview QR](preview.md#offering-the-device-preview-qr) says.
`mobile-preview.mjs` shows only the saved draft.

**Never send a version's content with `config update`.** That write takes one layout and would
drop the rest: bring a version back with a restore.

## Restore a version

A restore copies the whole version (screens, products, translations, media, variables, every
layout, the remote configs) into the draft. The live version and the source version do not change.

1. **Check for unsaved changes** ([above](#unsaved-changes-come-first)).
2. **Read the list** and let the user pick the version by its title and date.
3. **No `draft` row:** restore. It makes a new draft and asks nothing:

   ```bash
   $ADAPTY flows versions restore <FLOW_ID> <FLOW_VERSION_ID> --app <APP_UUID> --json
   ```

4. **A `draft` row:** the restore replaces that draft, and the history does not keep it. Ask
   first, with the draft row you just read:

   > Your flow has a draft, "<draft title>", last changed <the draft row's `updated_at`, as a
   > date> by <its `last_edited_by`>. Restoring
   > "<version title>" replaces it, and the draft cannot come back from the history. To keep the
   > draft, I can duplicate it to a new flow first. Replace the draft?

   Offer the duplicate only when `flows duplicate` exists; when it is missing, offer the copy in the
   dashboard instead ([When the CLI has no history commands](#when-the-cli-has-no-history-commands)).

   That is the shape, not words to copy. On a yes (after the duplicate, if they asked for it),
   keep a copy of the draft you replace, then send the draft row's `updated_at` as the token.
   Never overwrite an earlier copy: a second restore in the run writes
   `flow.draft-before-restore-2.json`, the next one `-3`, and so on.

   ```bash
   $ADAPTY flows config get <FLOW_ID> --app <APP_UUID> --json > flow.draft-before-restore.json
   $ADAPTY flows versions restore <FLOW_ID> <FLOW_VERSION_ID> --app <APP_UUID> \
     --yes --expected-updated-at <updated_at of the draft row> --json
   ```

   Without a terminal, `--yes` and the token are both needed: a missing one stops with exit 6
   `confirm_required` and sends nothing. Over MCP, `flows_versions_restore` takes
   `replace_draft: true` and `expected_updated_at` from the same row. The yes is the user's, asked
   before the call. The answer is the new draft (`flow_version_id`, `title` and its content).

5. **Go on from the result.** Fetch the new draft as phase 2 does (`flows config get` into
   `flow.working.json`, its `.config` into `draft.json`): that is the write base for any next
   edit, never the file from before the restore. **Never overwrite `flow.backup.json`:** it can be
   the only copy of the draft the restore replaced. Keep the new copy as
   `flow.backup.after-restore.json` and use it as the baseline of later diffs and `before` renders
   (`BASELINE=flow.backup.after-restore.json` for `gates.sh`). When a draft was replaced, tell the
   user the name of the file that holds it (the `flow.draft-before-restore` file of this restore,
   or `flow.backup.json`).
6. **Show the draft** (a render, or the device preview of the draft) and say that users still see
   the live version until a publish. Do not publish. On an explicit request to publish, follow
   [publish.md](publish.md).

**The answers that stop a restore:**

| Answer | What it means | What you do |
| :-- | :-- | :-- |
| `flow_draft_exists` | The flow got a draft and you sent no replace | Read the list again and ask the step 4 question |
| exit 6 `confirm_required` | The CLI found a draft and had no yes or no token | Read the list again and ask the step 4 question; never re-run with the token from the message on your own |
| `flow_config_conflict` | Someone saved the draft after you read the list | Read the list again, show the new last change, ask again; never retry with a fresh token on your own |
| `expected_updated_at_required` | A replace without the token | Send the `updated_at` of the draft row |
| `flow_publishing` | The draft is publishing now | Wait until `flows get` no longer reads `publishing`, then read the list again |
| `flow_archived` | The flow was deleted in the dashboard | Say: "The flow is archived. Restore it from the archive in the dashboard first." |
| `flow_version_products_deleted` | The version sells a product that was deleted | Say so and let the user pick another version |
| `flow_version_already_draft` | The picked version is the draft already | Nothing to restore; say so |

Each of them changes nothing.

## Roll back a bad publish

"Go back to how it was before yesterday's change" is a restore of the version that was live
before:

1. Read the list. The `live` row is the bad publish; the newest `previous` row with a
   `published_at` and `publication_status` `published` was live before it (a `previous` row that
   never finished a publish was never live). Show both and let the user confirm the pick.
2. Restore it ([Restore a version](#restore-a-version)), with the question when a draft exists.
3. Show the new draft and say: users see the bad version until you publish this draft.
4. The user decides the publish. Publish only on their explicit request.

## Duplicate a version to a new flow

For "try this old version in a separate flow", a redesign next to the original, a new flow that
starts from an existing one, or to keep a draft before a restore replaces it. Check the command
first ([When the CLI has no history commands](#when-the-cli-has-no-history-commands)).

```bash
# without --version: the draft, else the live version
$ADAPTY flows duplicate <FLOW_ID> --app <APP_UUID> --version <FLOW_VERSION_ID> --json
```

**Pick the content of the copy first.** Without `--version` the copy takes the draft when the
flow has one. Read the list:

- **An A/B test copy:** `--version` with the `flow_version_id` of the `live` row, so the copy
  differs from the live arm only by the change you make next.
- **To keep a draft before a restore:** the `flow_version_id` of the `draft` row.
- **Any other copy of a `dirty` flow** (a `draft` row and a `live` row): tell the user that the
  flow has unpublished changes, and ask which content the copy starts from, the draft or the live
  version. Use the `flow_version_id` of the row they pick.
- **The user picked a version** ("try this old version"): its `flow_version_id`. No `draft` row and
  no pick: leave `--version` out, and the copy takes the live version.

The new flow is named "<name>_copy", is not published, and has one draft with the content of that
version (every layout, the remote configs, the paywalls). The source flow, its draft and its
history do not change. Go on with the edit on the new flow: phase 2 as an existing flow, with the
new flow's `id` from the answer (the flow object, with its `name`).

`flow_version_products_deleted` means that version sells a product that was deleted: say so and
offer another version. `flow_archived` is the same as for a restore.

## Rename a version

Only on request:

```bash
$ADAPTY flows versions rename <FLOW_ID> <FLOW_VERSION_ID> --app <APP_UUID> --name "Black Friday"
# --name "" gives back the title "Version N"
$ADAPTY flows versions rename <FLOW_ID> <FLOW_VERSION_ID> --app <APP_UUID> --name ""
```

A rename does not change the content or the token, so the next draft write has no conflict.

## Metrics and revenue of a flow

The `growth-advisor` skill owns them, the never-published check included: offer it.
