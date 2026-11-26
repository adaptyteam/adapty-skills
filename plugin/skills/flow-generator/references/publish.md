# Publishing a flow

`SKILL.md` phase 5 owns the save and the closing callout. Read this before a publish you were asked to make, and before the callout of a flow a placement shows.

## Before a publish: read who the flow reaches

**Before a publish of a flow a placement shows, read who it reaches**: in this callout, and when
the user saved in the builder and asks what is next. The seven-day read of phase 6:

```bash
$ADAPTY flows metrics get "$FLOW" --app "$APP" --based-on placement \
  --date-from <seven days ago> --date-to <today> --date-type purchase_date --json
```

`unique_profiles_views` on each placement's node is how many people started the flow there; that
number goes in step 3. When the edit changes what buyers see (copy, plans, layout), the same line
offers an A/B test of a copy once, through **`ab-tests`**; publishing in place stays the default.
No placement shows the flow: leave the line out. When `flows metrics --help` says the command does
not exist, try `npx --yes adapty@beta flows metrics --help` once (use that form for the read if it
works); if it lacks it too, the line says the reach was not checked.

## Never publish with Terms or Privacy as inert text

**Never publish with Terms or Privacy as inert text.** That is the right draft default
([transforms.md](transforms.md) decision 10), but on a published paywall `flow-audit`
calls it a blocker and both stores reject it. Before a publish you were asked to make, get the
two URLs; without them, save, don't publish, and say why.

## Weigh before a publish too

**Weigh before a publish too,** on `flow.working.json`. A finding the user has not heard yet (the
flow was saved in the builder, or by another run) goes to them before the publish, with the fixes:
once it is published, every user downloads it. Findings they already answered at this save do not
come back.

## Running `flows publish`

**`flows publish --app <APP_UUID> <FLOW_ID>` is not in every build.** Per the rule in [SKILL.md → The CLI surface](../SKILL.md#the-cli-surface), decide
that by running `flows publish --help`, not from a version number — the command has left stable
once already, so a numeric floor is not a reliable test. Its own flags are `--app` plus `--yes`/`-y`, and the CLI's global `--json` on top of
them. Five facts shape how you call it: publication is **asynchronous**, so the response reads
`status: publishing` and never `published` — report it that way rather than claiming the flow is
live, and its `published_flow_version_id` is still the version that was live before, the rollback
point, not the one you are publishing; the confirmation prompt goes to **stderr**, so `--json` stdout stays parseable; `--json` or a
non-TTY **without** `--yes` refuses with **exit 2** (`Re-run with --yes`) instead of hanging, so a
headless run passes `--yes` only once the user has said yes in the conversation; a declined prompt
exits **1** (`Cancelled, nothing was sent.`); and a flow with no config exits **1**
with `Flow has no current version.`

**A successful publish tells you what to run next, and you run it.** In human mode it prints three
lines: that publication is asynchronous and the flow is *not* published yet, the `flows get` poll to
run until the status reads `published` or `publication_failed`, and the `flows config get` that
shows why if it fails. They are **suppressed under `--json`**, which leaves you holding
`status: publishing` and nothing else — poll anyway. **On `publication_failed`, `flows config get`
is the answer to *why*:** its envelope carries `publication_status`, `transform_error` and
`publication_error` alongside the config, and `transform_error` is the transform service's own
objection. It is a raw string — a JSON issues payload or a summary — with no CLI helper to parse it,
so read it and quote it rather than re-deriving a cause. Where the API does not send those fields
they are simply absent; that is not an error, and it does not mean the publish succeeded.
**`Flow transformation failed. Please contact support.` with a null `transform_error`** carries no
issue list, so nothing in it names the cause. One cause seen is a wrong
`_meta.screens[].products[].flowProductId` (an Adapty, vendor or store id where the derived one
belongs): recompute each with `flowkit.flow_product_id`
([products.md](products.md#a-price-variable-requires-a-product-element-on-the-screen--even-with-no-plan-card))
before you call it a support case.

**Handle a font save failure before retrying publish.** A failed save stops the command before
it sends the publish request. If the save response is unreadable or the connection fails during
the save, the save may have gone through. Run `$ADAPTY flows config get --app "$APP" <FLOW_ID>`
to see the stored config before you publish again.

While `flows get` reads `publishing`, an HTTP 503 or "busy" in `transform_error` means the
transform service is under load. Keep polling. If the publish request itself answers 503, run
`flows get`. If it reads `publishing`, keep polling. If it returns the status from before the
request, retry the publish once.

**A missing flow exits 4.** For a 404, verify the app and flow IDs with `flows get`. If the
flow exists and the API deployment lacks the publish route, point the user to the editor's
publish button. If the deployment refuses `flows update --name` with `Method "PUT" not allowed`,
point the user to the builder's rename field.
