# Media assets: uploading an image, a video or a font and binding it into a config

`flows media upload` puts a local image file on Adapty's CDN and prints the URL to reference from
a flow config; `flows media upload-video` does the same for a clip
([Uploading a video](#uploading-a-video)). Given a file, an image or a video in an authored flow
is yours to place rather than a user ask; so is a font file, through `fonts upload`
([Uploading a font](#uploading-a-font)).

The image claims below hold against **production**, except the refusal texts
in the tables: those are the texts of the current CLI, and an older CLI refuses the same files
with a `validation_error`. The video limits are the command's own refusals. Where a claim rests
on a render rather than on the endpoint, it says so.

## The call

```bash
$ADAPTY flows media upload --app <APP_UUID> ./hero.png
```

```
Image uploaded!
ID: 516395
Name: hero-600x400.png
URL: https://public-media.adapty.io/public/1e/5b/1e5bbbb4-.../hero-600x400.png
```

The file argument is positional and required; `--app` is the only flag that matters. The printed
URL can answer `200` in the same second, but a preview rendered right after the upload can draw
the new image blank: render again before you judge a missing asset.

**Upload files one at a time.** Parallel uploads hit `http_429`, and the CLI does not retry an
upload, so on a rate-limit error pause, then upload the files that failed, one at a time; wait as
long as the error says when it names a time.

**A config needs three values from this command and the human output carries only two.** The
JSON body has a fourth key, `preview_base64` — a base64 WEBP thumbnail, thousands of characters
even for a small source — which the human output suppresses. That is the value a config binds as
`previewValue`, and without it the image draws as a transparent 1×1 until the full asset
downloads (see below). So take `--json`, and **redirect it to a file so the blob never lands in
your context**:

```bash
mkdir -p media
$ADAPTY flows media upload --app "$APP" ./hero.png --json > media/hero.json
MEDIA_ID=$(jq -r .id media/hero.json)
MEDIA_URL=$(jq -r .url media/hero.json)
MEDIA_PREVIEW=$(jq -r '.preview_base64 // empty' media/hero.json)   # may legitimately be empty
```

Reading the file with `jq` keeps the cost at one short string per variable; `cat`-ing it, or
running the command without the redirect, puts the whole thumbnail in front of you for nothing.

**That file is the asset's record, so keep it for the whole run.** `preview_base64` comes back
from this call and from nothing else, and the upload does not deduplicate — re-running it to
recover a value mints a *second* asset with a different id and URL, and leaves the first behind
where no CLI command can remove it. So when you bind an asset you uploaded earlier, read its
three values out of its file. Looking one up later is a file read, not a command.

**A response that hands you an id and a URL and no preview is not telling you the field is
optional.** It is telling you that value was not kept for you. Bind the asset without it and the
screen ships with a hole in it, exactly as if you had never had it — so treat a missing preview
as a value to go and find ([When you have a URL and no preview](#when-you-have-a-url-and-no-preview)),
never as a fact about the format.

### When the upload warns that an image is heavy

The `--json` answer also carries `size` (bytes of the file sent) and `warnings`: an item with
`code` `heavy_image`, a `title` and a `message` when the sent file is over 1 048 576 bytes (1 MiB). Read it off the
record: `jq -c '.warnings // empty' media/hero.json`. No `warnings` key (an older server): say
nothing about the weight of the upload.

On a `heavy_image` warning:

1. Tell the user which image is heavy, its weight as the warning's `title` says it, and that it
   slows the first load of its screen. Offer **one** reduction step, named by width and quality,
   and ask. The width is the weigh's: 3× the box the image fills, 1290 px for full width
   ([below](#weighing-a-config-before-a-write-or-a-publish)); it stays, only the quality drops.
2. Only on their yes: reduce the file they gave you, upload it, and put it in place of the old one
   (`swap` on a config that already binds it; else bind the new record):
   ```bash
   python3 references/weigh-config.py webp media/hero-src.png media/hero-2.webp --max-width 1290 --quality 72
   $ADAPTY flows media upload --app "$APP" media/hero-2.webp --json > media/hero-2.json
   python3 references/weigh-config.py swap draft.json "<old url>" media/hero-2.json
   ```
3. The new answer still warns: say the new weight (its new `title`) and offer the next step, a
   lower quality (72, 62, 52) at the same width. Each step needs its own yes. On a no, the
   current image stays. After a step, say what changed (the same width, a lower quality), not
   that the image or the screen looks the same: a local render does not show the user's device.

The weight of this offer is always the warning's `title` (the file sent). The weigh's Load time
line before a save measures the stored file and can give another number: keep the two apart, and
ask the reduction step here, right after the upload, not inside the save question.

The weight never blocks a save or a publish. An example of the ask's shape, not words to copy:

> The photo on Welcome is heavy (Large image — 3 MB), so that screen loads slower the first time.
> I can keep it 1290 px wide at quality 72 and use it instead. Do it?

## Over MCP: the upload link or base64

Two tools put an image in the media library. Each answers the same record as the CLI's `--json`
(`id`, `url`, `name`, `preview_base64`), and each send makes a new asset. Pick from these facts:

- **`uploads_create`** (the app, the file name and `kind` `flow_image`) answers a 3-minute
  `upload_url`, its `expires_at`, `max_bytes` and the `curl -T` command that sends the file. The
  send stores the image and answers its record: the `id` and `url` the config binds. Run that
  command from your sandbox on the file, with the answer going to the record file, never to your
  context:

  ```bash
  mkdir -p media
  curl -sS -T /mnt/user-data/uploads/hero.png "<upload_url>" -o media/hero.json -w '%{http_code}\n'
  ```

  `201` is the uploaded asset; any other code is the refusal of the upload, in the file
  ([What it accepts](#what-it-accepts)). The link takes more sends until it expires, and each one
  adds an asset, so send each file once. After it expires, create a new one. The image bytes never
  pass through the conversation.
- **`flows_media_upload`** takes the file as base64 text in a tool argument, so it suits only
  small images.

If the sandbox cannot reach the link (a `403` from the sandbox proxy, not from Adapty), the user has to allow `*.adapty.io` once: pass on the `if_blocked` text of the `uploads_create` answer in your own words, with its link.

## Getting the file: the upload needs a FILE, not a picture

The upload reads a file. **An image you can only *see* is not an image you have** — a screenshot
or hero the user pasted or attached into the conversation reaches you as pixels in your context,
and you cannot re-emit the bytes you were shown. Checked on a Claude Code install, pasted images
are not persisted to disk (`~/.claude/paste-cache` held text only), and this has to hold across
harnesses anyway — this skill runs on agents whose attachment handling differs. A chat with a
code sandbox is the exception: there an attachment is also a file.

So resolve every asset to a file, in this order:

1. **A path the user gave you** — typed (`./assets/hero.png`), or dragged into the terminal, which
   most terminals insert as a path. Confirm it reads before you build around it.
2. **An attachment in your sandbox.** When you can run commands in a sandbox next to the chat
   (claude.ai and the Claude apps with code execution), a file the user attached is in it: in
   claude.ai under `/mnt/user-data/uploads/`. List that folder and take the file whose name and
   type match the attachment; with more than one candidate, name the one you took. Send it as
   [Over MCP: the upload link or base64](#over-mcp-the-upload-link-or-base64) says, or with
   `flows media upload` when the CLI is your way.
3. **A file already in the project** — look for it (`assets/`, `public/`, `design/`) and name what
   you found, so a wrong guess is the user's to catch rather than yours to hide.
4. **A URL the user pointed at** — downloadable, but a download is a side effect: say what you are
   fetching and from where, and get a yes before you fetch. Then upload the downloaded file.
5. **Pasted or attached only, with no sandbox and no path** — **ask for one.** "I can see the hero
   but I can't upload what I can't read from disk — save it anywhere and give me the path." One
   ask, batched with your other asks; until it arrives the element's catalog entry has empty
   `values`, exactly as if no asset existed.

**Never guess a path, and never substitute a file that merely looks right.** A guess that misses
fails loudly and safely — exit 2, `Cannot read file: ./hero.png`. The damaging version is the guess
that *hits*: uploading `assets/hero.png` because the name matched, when the user meant the image
they pasted, produces a screen that renders perfectly with the wrong picture in it, and no check in
this skill can tell. If you searched for the file rather than being handed it, say which file you
used.

## What it accepts

| Input | Result |
|---|---|
| PNG, JPEG, WEBP | uploads |
| GIF | refused: `GIF is not supported.` |
| HEIC | refused: not an image type here; ask for a PNG or JPEG export |
| a video file (`.mp4`, `.webm`, `.mov`) | refused: `This is a video file. Use flows media upload-video.` ([Uploading a video](#uploading-a-video)) |
| animated WEBP | uploads, and is served as one still frame: motion is a [`video`](#uploading-a-video) |
| **SVG** | **`ApiError: http_500`, reproducible**; through the MCP server it has come back as `INVALID_ARGUMENT` — see below |
| Anything else that is not an image | refused with the list of the image types |
| up to 20 MiB | uploads; over 1 MiB the answer carries a [`heavy_image` warning](#when-the-upload-warns-that-an-image-is-heavy) |
| over 20 MiB | refused: `File size must not exceed 20 MiB.` (`media_file_too_large`, HTTP 413) |

**The size cap is on file bytes, not on dimensions:** a **3000×2000** PNG at 22 KB uploads fine. The upload link of
[Over MCP](#over-mcp-the-upload-link-or-base64) states its own limit in `max_bytes`.

**SVG is rejected in practice even though both sides claim to support it.** `.svg` is in the CLI's
own MIME map and `SVG` is in the server's permitted-format list, and it still returns `http_500`
on every attempt. So the upload path does **not** replace authored icon SVG: a **monochrome** glyph
stays inline in `_meta.icons` with real `raw` markup, needs no upload at all, and is strictly
better there — see the next section for why. Rasterizing a monochrome glyph to get it past this
endpoint is a downgrade, not a workaround.

**Exit codes:** `0` on success, `1` on any API refusal, `2` on an unreadable local file
(`Cannot read file: ./nope.png`). Read the exit code, not the presence of output.

**The upload is not idempotent and does not deduplicate.** The same bytes uploaded twice produce
two different ids and two different URLs (516395 and 516396). So **upload once per asset and reuse
the URL** through the whole preview loop; re-running the upload each iteration silently litters the
app's media library with duplicates that nobody will be able to tell apart.

## When a graphic cannot be an element, draw it and upload it

The format cannot express every graphic. A multicolour or gradient glyph, an illustration, a radial
glow, a chart, a mesh — none of these is a `text`, a `fill`, an `icon` or a stack of them. **Draw it,
rasterize it, upload it.** That is a real capability now, and leaving a hole in the screen or
substituting a lookalike is worse.

It is a **last** resort, not a first one, because everything an element does an image stops doing.
Work down this ladder and take the first rung that fits:

1. **A monochrome glyph → an `icon` element with `raw` SVG in `_meta.icons`.** Real exports write
   these with `fill="currentColor"`, so the glyph takes its colour from the element's `colorId` —
   which is what makes it follow the theme. Never rasterize this rung. **Do not author the markup
   either**: a `phosphor` name resolves from the renderer's own bundle, so an invented name draws
   blank with correct `raw` sitting right there (flow-schema.md trap 23). Search the bundle —
   `python3 references/icons.py --search arrow` — and let `flowkit.icon()` declare it.
2. **A flat or linear-gradient surface → a `fill`** (with `stops`), on a stack you already have.
3. **A composition → stacks**, using the layout vocabulary before padding or docking.
4. **Nobody has a file → a styled empty `image` and an ASK** (trap 5). This is rung 4, not the
   last rung — see below for what skipping it costs.
5. **Only when the ask cannot be answered:** cut it out of the reference
   ([`crop.py`](crop.py), below), or draw and rasterize it. A crop first, since their pixels beat
   your approximation of them.

**Why the ask outranks both.** Do not order these rungs by fidelity-if-it-works — the real
comparison is crop **versus asking**, and asking wins on the thing that matters:

| | what the user ends up with |
| :--- | :--- |
| placeholder + ask | their **real, full-resolution** asset |
| crop | a **1x** crop of their mockup — lower resolution than their own source, and damaged if keying eats a region that matches the backdrop |
| draw | your guess at someone's design, wearing a finished look |

A reference is nearly always the user's *own* design, so they already have the file — and cropping
someone else's design is excluded on provenance anyway. **So for every legitimate case, asking
strictly dominates.** Crop and draw are for the narrow case where the ask cannot be answered: an
unattended run, or a graphic that exists only inside a flattened mockup.

**Asking reaches the correct outcome without touching `crop.py`; cropping first produces the
worst artifact.** The rung is real; it is just not where you go first.

### Cutting a graphic out of a reference

`crop.py ref.png out.png --box x0,y0,x1,y1 [--key] [--fit WxH]` — stdlib, PNG in / PNG out,
8-bit non-interlaced (a macOS screenshot qualifies, a JPEG does not). `--key` floods the backdrop
away from the border inward, ramps alpha across the anti-aliased band and unpremultiplies it, so
the cutout composites with no rim. Alpha survives the upload round trip (see above), so
a transparent crop is a shipping-grade asset.

It **refuses** rather than guessing, and the refusals are the useful part:

| It says | It means |
| :--- | :--- |
| border is not a flat backdrop | either the box clips the graphic (widen it) or the backdrop is a texture or gradient, which cannot be keyed at all — there is no single colour to remove and a flat screenshot records no alpha |
| N% removed, no graphic in this box | the coordinates are wrong; a reference with a device frame needs its screen bounds located first ([preview.md](preview.md)) |
| Nx into a WxH pt box | the box is in points and the asset scales into it, so a crop from a 1x phone screenshot is soft on a 2x/3x device. Ask for a higher-resolution export; never upscale |

**The one failure it cannot detect is the one you must look for yourself**, which is why `--key`
also writes `out.contact.png` — the cutout over black, over white and over grey. **Look at it.**
A graphic that *contains* the backdrop colour loses that part of itself, because the flood walks
through any region of the key colour that touches the silhouette's edge. Measured on a real
reference sheet: a US flag survived intact (its white stripes are enclosed by red) while the
Finnish, Canadian and French flags beside it came back as their coloured parts alone. An enclosed
region is safe; one that reaches the edge is not, and no threshold separates the two.

Two limits that are about provenance rather than pixels. A crop is right when the reference is
**the user's own design** — cropping a competitor's wordmark into their media library is lifting a
brand asset, not a fidelity win. And a crop is still an upload, so it is still an asset in their
library that no CLI command can remove: crop once, and crop the *visible artwork* rather than a
canvas with margin baked in.

### Three things never become an image

**Text — drawn by you OR cropped from a reference.** Never bake words into a bitmap: a rasterized
price is the exact "renders perfectly, ships a lie" failure,
and a missing typeface is a named ask, never a reason to draw the sentence.

**An asset that will never arrive has an exit, and it is not a crop.** When the reference is
someone else's screen the user cannot supply the file at all, so the placeholder is permanent —
that is the case for the missing-assets block's third route, *design around it*
([fidelity.md](fidelity.md)). It is the user's call to make, never yours to assume.

> **The crop rung is the easy way to break this.** The rule covers a crop as well as a drawing:
> crop a whole server-list card out of a reference and you bake in `SERVER LOCATIONS`,
> `United States`, `21.170.236.49`, `Connected` and `Ready` — untranslatable, and the server names
> and IP are **live app data that must never be a picture**. It renders perfectly and nothing
> objects.
> **Crop a graphic, never a region containing text or data.** If the region you want is mostly
> text, it is a composition, not an asset — build it, and crop only the graphic inside it.

> **The bar is text-or-data, not *any* text.** A **designed lockup** may be an image: an `image`
> element's catalog entry is keyed by **locale**, so a per-locale lockup is expressible, and
> `verify-config.py`'s parity walk checks every catalog entry, image entries included. Do not downgrade a lockup to a solid-colour `text` lookalike to avoid baking
> words. See [fidelity.md](fidelity.md) for lettering whose treatment is unreachable.

**Lettering that carries a variable or a price stays a `text`, always** — an image cannot carry
one. If its *treatment* is also unreachable, that is the one place a solid-colour downgrade is
correct, and it ships disclosed.

**Anything selectable.** A group member must be a `product`, a `selectable` or a `tab-item`; an
`image` carrying a `groupId` is inert. So plan cards, toggles and tab bars cannot be pictures of
themselves, however much easier the picture looks.

**Anything whose colour must follow the theme — unless you upload a dark file too.** A bitmap
with a baked-in background breaks the moment the app switches to dark mode, while every colour
around it flips: themed colours carry `light`/`dark` per entry in `theme.colors`, and two of the
four corpus fixtures define a dark variant for **every** colour they declare (14/14 and 11/11).
An image can follow the appearance only with a second file:

- **An `image` element takes `imageDark`** beside `image`, and a `video` takes `videoDark`
  beside `video`. Both are catalog refs of the same kind as their light field, keyed by locale.
  The device shows the dark file in dark mode and the light one otherwise; either alone shows
  in both. `flowkit.image(url, dark=dark_url, dark_preview=..., dark_media_id=...)` emits it. A
  dark entry with no default-locale value shows the light file in dark mode wherever that
  locale is missing, with a warning.
- **A background** follows the appearance through a theme colour written as a layer stack — one
  image for light, another (or a gradient) for dark — with the screen or card filled by a
  reference to that colour ([flow-schema.md](flow-schema.md), trap 26). The image layer takes
  the same `{id, url, previewValue}` as an image fill, and `flowkit.image_fill()` emits it.

Upload both files either way. When the user has only one, design the graphic so it works on
both surfaces, which is why:

### If you do rasterize

- **Transparent background, no baked surface.** Measured: alpha survives the upload — the CDN
  re-encodes the file but the served PNG is still RGBA — and it composites cleanly over a dark
  screen with no matte or white box. A transparent glyph is the only bitmap that is theme-safe,
  because the screen's own background shows through it.
- **Draw at 2–3× the box** and size the element in points; the box is in points and the asset
  scales to it, so the source resolution is free. *Not* confirmed on a device — the preview
  renderer is not a retina device — so treat crispness on hardware as something the device check
  confirms.
- **Rasterize with the Chrome `shoot.sh` already uses** — no Pillow needed. Draw the SVG with a
  tight `viewBox` (no padding around the artwork, so the box is the artwork and nothing needs
  trimming), wrap it in a page with a transparent background, and screenshot at the drawn size:

  ```bash
  printf '<html><body style="margin:0;background:transparent"><img src="art.svg" style="display:block;width:%spx;height:%spx"></body></html>' 900 600 > art.html
  "$CHROME" --headless=new --hide-scrollbars --default-background-color=00000000 \
    --force-device-scale-factor=1 --window-size=900,600 --screenshot="$PWD/art.png" "file://$PWD/art.html"
  ```

  The output path must end in `.png` or Chrome writes nothing, and the size is the SVG's own
  `width`/`height` at 2–3× the box. Upload each PNG once and reuse the URL.
- **Say that you drew it.** A rasterized graphic looks finished, which is the emoji hazard one
  level up: nothing downstream flags an agent-drawn illustration, so name it as yours and as
  replaceable, or the user ships your sketch believing a designer made it.

## Binding the URL: two different shapes

An uploaded URL has two consumers, and they take **different shapes**. Getting this wrong is a
silent defect — no gate catches it (see below).

**An `image` element** holds a ref, and the `IImage` goes into its catalog entry, per locale:

```json
{"id": "el_PSJTQ6QeQt", "type": "image", "props": {
  "image": {"_lid": "lc_9"},
  "width": {"type": "fixed", "value": 242}, "height": {"type": "hug"},
  "objectFit": "fit", "borderRadius": {"tl": 20, "tr": 20, "bl": 20, "br": 20}}}
```
```json
"lc_9": {"kind": "image", "values": {"en": {
  "id": "516395", "url": "https://…/hero.png", "previewValue": "UklGRhQJAABXRUJQVlA4…"}}}
```

To bind an upload to an element that already exists, write the `IImage` into that entry's
`values[<defaultLocaleId>]` and keep the ref. To bind it to a new element, write the element in
the inline form — `"image": {"_localizable": true, "values": {"<defaultLocaleId>": {…}}}`, which
is also what `flowkit.image()` emits — and run `localization.py catalog` over the document
([flow-schema.md](flow-schema.md#localization-the-catalog)).

**A background fill** on a screen's or stack's `props.fill` takes the image **flat**, with no
ref and no catalog entry, as one layer of the fill array — what `flowkit.image_fill()` emits. An
image layer holds only `type`, `image` and `customMediaID`; a colour is a layer of its own
([flow-schema.md](flow-schema.md#a-fill-is-a-layer-stack-bottom-to-top)):

```json
"fill": [{"type": "image",
          "image": {"id": "516395", "url": "https://…/hero.png",
                    "previewValue": "UklGRhQJAABXRUJQVlA4…"}}]
```

**Upload an opaque file for a background fill.** On a device, the transparent part of a fill's
image shows black, and an opaque file fixes it. Whether a colour layer under the
image shows through instead is not verified: the preview draws it, a device may not. So with a
transparent file, tell the user the transparent area can show black on a phone, and ask for an
opaque version or a device check of that area. A screen-sized background
belongs here, not in an `image` element positioned `absolute` or `fixed`: that one takes the
taps of everything beside it ([flow-schema.md](flow-schema.md), trap 9).

**A photo over a flexible-height band: crop the file to the band's shape.** An image fill draws
at the file's natural aspect, so a hero stack whose height grows leaves a gap under the photo.
The fix: crop the file to the band's rendered aspect (`crop.py --box` for a PNG),
upload it, and put it in that stack's own `fill`; render the tallest device to check the edge.

Because the element form is localizable, **a different asset per locale is expressible** — the
entry's `values` is keyed by locale id exactly like copy. A fill's image can be localized too: its
`image` may be a `{_lid}` ref to an `image` catalog entry instead of the flat value, and that is
how the Flow Builder stores one — it rewrites the inline image of a fill or a theme colour into a
ref when the flow is opened, so a re-fetched config shows refs where you wrote URLs.
`localization.py catalog` mints refs for elements only, so a background that must change per
language is simplest as an element; a fill ref you write needs its catalog entry beside it.

**Write the `id` as a string.** The command prints a number and `--json` returns a JSON integer
(`"id": 516395`), while the schema's `Image` declares `id` as a required `string` and every real
builder export carries it quoted. Stringify it as you bind it.

**A script that swaps URLs matches image objects (`{id, url}`), never the key `url`:** an Open URL
action's `payload.url` can be a `{_lid}` ref, an object whose per-locale values sit in the catalog,
and a walker that expects a string there crashes.

## `previewValue`: what the user sees before the image arrives

`Image` is `{id, url, previewValue?}`, and the third field is what the renderer paints **while
the full asset downloads** — a tiny base64 thumbnail, blurred up to fill the box, so the screen
is composed from the first frame. Leave it out and the renderer has nothing to paint, so it
substitutes a **transparent 1×1**: the layout is right and the picture is a hole, for as long as
the download takes. On a fast connection that is a blink. On a slow one it is the whole first
impression of a paywall.

Bind it exactly as the upload returned it:

- **Bare base64, no `data:` prefix.** `preview_base64` is a half-size WEBP; the renderer's own
  1×1 fallback is bare base64 too. A data URI is not the same string and does not belong here.
- **Omit the key only when the upload itself returned nothing.** `preview_base64` is nullable —
  preview generation can fail — and the field is optional, so that document is legal. Never write
  `null` or `""` to fill the slot, and never reach for this bullet to cover a value you had and
  lost: *the upload gave me none* and *I did not capture it* are different situations that produce
  the same JSON, and only the first one is finished work. Say which one it was.
- **It rides with the asset, not with the element.** The same three-field `Image` goes into an
  element's catalog entry and flat inside a fill, so a background needs it just
  as much — more visibly, since a background is usually the largest thing on the screen.
- **Bind it once per asset, never once per locale.** An image element's catalog entry holds the
  default locale, plus a locale only when that locale gets a different file. Every other locale
  already shows the default's file. Copying the `Image` into each locale repeats the preview in
  the published config for every locale, which is how a flow of a few images grows to tens of
  megabytes and times out at publish. See `flow-schema.md` trap 1.
- **A config is where it is stored.** Because the whole `Image` is written into the flow, an
  asset already bound somewhere carries its preview there, and that is what makes a lost one
  recoverable — see below.

## When you have a URL and no preview

Reuse is the ordinary way to get here: the asset went up an hour ago, or into another flow
entirely, and what you are holding now is a URL. Work down this ladder and take the first rung
that fits. **Do not skip to the bottom** — rung 3 mints a duplicate nobody can delete, and rung 4
is work you hand back to the user.

| What you have | What to do |
|---|---|
| **An upload you ran** | Its record file has all three values. Read them back out of it. |
| **The asset bound in some flow** | Fetch that config and lift the preview out by URL — one read, nothing minted, and the value is the API's own. |
| **The local file, and no record** | Re-upload it with `--json`. You get a *second* asset with a different id and URL: bind the new one everywhere on this screen, and say in the handoff that the media library now holds a duplicate. |
| **Only the URL** | Hand it back: the user re-uploads that image in the builder, which writes the field for them. Name the elements, so they know which. |

Rung 2 is the one worth a recipe, and it is how you reuse an asset across flows — read it out of
the config that already binds it rather than uploading the file again:

```bash
$ADAPTY flows config get <FLOW_ID> --app "$APP" --json > other.json
jq -r --arg u "$MEDIA_URL" \
  '[.. | objects | select(.url? == $u and (.previewValue? // "") != "")][0].previewValue // empty' \
  other.json
```

Redirect and `jq` for the same reason as the upload: a config runs to six figures of characters,
and the value you want is one string inside it. The walk is over the whole document because the
same asset binds two ways — a per-locale `values` entry on an element, flat inside a fill — and
either one carries the field.

**An empty result is the common case, and it means the agent that bound it dropped the field —
not that the field is optional.** Only an asset bound *with* a preview can hand one back, so
anything written before this rule, and anything the dashboard's paywall conversion moved over,
comes back empty. Fall through to the next rung; do not conclude anything about the format.

That is also the line `verify-config.py` draws. It reports the images **your draft added** and
stays quiet about ones that arrived with the config — not because an inherited one cannot be
fixed, but because fixing it means editing an asset someone else bound, which is a change to
report and offer rather than to make silently.

## No publish gate catches an image defect. Only the render does.

On one config, five ways — real URL with a string `id`, with a numeric `id`, with no
`id` at all, with no `previewValue`, and with an empty entry:

- **`flows config validate` returns `valid: true` for all four.** An image is not part of the
  publish gate, so **a flow whose hero is still an empty placeholder publishes cleanly** and ships
  an "Upload Image" checkerboard to real users.
- **The schema step catches the shape defects and nothing else.** A numeric or missing `id` is a
  finding there, because each locale's value is typed as an `Image`. A missing `previewValue` and
  an empty `values` map are legal shapes, so it passes both.
- **The render is the only check that sees any of it**, and only once a real URL is in place.

That is the whole argument for the ordering in the workflow: the image is verified by looking at a
screenshot, so the asset has to be in the config **before** the preview loop, not after it.

## Geometry: what changes when the asset lands

`objectFit` has exactly **two** legal values, `fit` and `cover` — not the CSS set. Measured render
boxes for one 600×400 (1.5:1) asset in a 242-wide slot:

| `height` | `objectFit` | drawn box | what happens |
|---|---|---|---|
| `hug` | either | **242×161** | height derived from the **asset's** aspect; `objectFit` has no visible effect, and a `value` left on the `hug` size is dead |
| `fixed: 300` | `cover` | 242×300 | the box wins, the asset is cropped to fill it |
| `fixed: 300` | `fit` | 242×161, centred | the box wins, the asset letterboxes inside it, leaving **139 px of dead band** |
| *empty `values`* | — | **242×256** | the placeholder checkerboard, near-square whatever the real asset's aspect is |

Three consequences an author acts on:

**`cover` needs a box that no `hug` sizes, its own or a parent's.** Under a `hug` width or inside a
`hug` parent, iOS draws it a few points tall: give it a `fixed` height, or use `fit`.

**A placeholder does not occupy the space the real asset will.** The empty map draws **95 px taller**
than the same element with the real 3:2 image — on a 932 px screen, a tenth of the height, and
everything below it moves. A layout previewed with placeholders is a layout that has not been
checked. Upload first.

**Crop transparent margins off before you upload: the BOX is the asset, so padding baked into a
PNG becomes layout.** An `image` box is filled by the whole canvas, alpha included, so a glyph
centred in a generously-padded export draws smaller than its box and pushes its neighbours away by
the difference. In a six-asset set exported from a design file the opaque
ink is **65–87%** of the canvas height (`ink/canvas` of 0.649, 0.706, 0.707, 0.724, 0.735, 0.870),
so a 302 px box draws a 196 px illustration and spent **106 px on nothing**. Sizing the box to the
*visible* artwork then requires dividing by that ratio per asset, which is guesswork; cropping to
the alpha bounding box first makes the box the artwork and the arithmetic disappear.

```bash
python3 -c "from PIL import Image; im=Image.open('in.png').convert('RGBA'); \
im.crop(im.getchannel('A').getbbox()).save('out.png')"
```

Two riders. **Crop before the first upload, not after** — the upload does not deduplicate and
`flows media` has no delete, so a re-crop leaves the uncropped copies in the user's library
permanently (disclose them). And
because the box is in **points** while the asset scales to it, upsample the crop 2–3× on the way
out: it costs bytes (keep the file at 1 MiB or less, where the upload does not warn) and keeps the
artwork crisp on a retina device, which no preview render can confirm.

**`hug` reflows and `fixed` does not.** With `hug`, the element's height is a function of the file
you upload, so swapping a 3:2 asset for a 4:5 one silently rewrites the screen. With `fixed`, the
box holds and the asset absorbs the mismatch — `cover` by cropping (choose it when the subject is
centred and the edges are expendable) and `fit` by leaving bands (which on a dark screen read as a
spacing bug rather than as an image, so prefer `cover` unless the whole asset must be visible).

## Still out of reach

- **SVG upload** — `http_500`, or `INVALID_ARGUMENT` over MCP (above). Icons stay authored inline in `_meta.icons`.
- **A clip nobody has a file for, or a CLI with no `upload-video`.** The element is not out of
  reach: place a real `video` element with `customMediaID`/`video` unset. It renders a styled
  **"Upload Video"** placeholder (like an empty `image`), publishes clean (`validate` →
  `valid: true`), and the user binds the clip in the builder. **Never** substitute a `stack` with
  a Play icon — that ships a lookalike of a different element type (flow-schema.md trap 5).
  See [The video placeholder](#the-video-placeholder).
- **A font nobody has a file for.** A typeface name alone is a named ask, not a silent
  substitution; with the files, the upload is yours: [Uploading a font](#uploading-a-font).
- **Deleting or listing uploaded media.** `flows media` only uploads, so an upload cannot be
  undone from the CLI — one more reason not to re-upload per iteration.

## Uploading a video

Given a clip file (a path, as for an image: [Getting the file](#getting-the-file-the-upload-needs-a-file-not-a-picture)),
upload it once and keep the `--json` record, exactly as for an image:

```bash
mkdir -p media
$ADAPTY flows media upload-video ./intro.mp4 --app "$APP" --json > media/intro.json
```

Over MCP there is no video upload tool yet: use the CLI, else [the placeholder](#the-video-placeholder).

**The command is newer than `flows media upload`.** When `$ADAPTY flows media upload-video --help`
says there is no such command, try `npx --yes adapty@latest flows media upload-video --help` once
(and the beta, as `SKILL.md` says for any missing command). Still missing, or the upload fails
with HTTP 404 (`http_404`, exit 4): say that video upload is not available yet, and use [the placeholder](#the-video-placeholder) — the user uploads the clip in the builder.

| Input | Result |
|---|---|
| `.mp4` or `.webm`, at most 30 s, width and height each at least 640 px, at most 50 MiB | uploads |
| another extension (`.mov`, an animated `.webp`) | `Only mp4 and webm videos are allowed.` |
| GIF, under any extension | `GIF is not supported.` |
| longer than 30 s | `Video duration should not exceed 30 seconds` |
| width or height under 640 | `Video resolution should be at least 640x640` |
| over 50 MiB | `File size must not exceed 50 MiB.` |

Each refusal stores nothing. Ask for a clip that fits, in the user's words: an mp4 or webm, 30
seconds or less, at least 640 px on its shorter side. The call returns after the server has
transcoded the clip, so a long clip takes a while: wait for it, and never run it twice for one
file — the upload does not deduplicate.

**The record holds five values, and the config binds four.** `{video_url, preview_url,
preview_base64, width, height}`: `video_url` is an HLS playlist (it ends in `master.m3u8`),
`preview_url` a still frame the renderer shows until the clip plays, `width` and `height` the
pixel size of the largest rendition, with the clip's aspect ratio. `preview_base64` is not part of
a video value; leave it in the file. The video value is:

```json
"video": {"_localizable": true, "values": {"<defaultLocaleId>": {
  "videoUrl": "<video_url>", "previewUrl": "<preview_url>", "width": 1080, "height": 1920}}}
```

`flowkit.video(fixed_h=220, source='media/intro.json')` reads the record and emits it, and
`dark_source=` the dark file's record (`videoDark`). Bind the default locale only, as for an
image ([flow-schema.md](flow-schema.md) trap 1), then run `localization.py catalog` over the
document. Give the element a fixed height from the design all the same: the clip absorbs the
mismatch (`cover` crops it, `fit` leaves bands). Render the screen after the bind to check the
layout; that the clip plays is a device check, so say it was not checked on a device.

## The video placeholder

Everything here holds against the real transform service and the render. The placeholder is
for a clip nobody has a file for, and for a CLI with no `upload-video`
([Uploading a video](#uploading-a-video)): then the upload is the user's, in the builder, so the
placeholder is what gets handed over.

**It is publishable, and it reaches a device.** An unset `video` returns `valid: true, issues:
[]` in three forms — fully styled, with an empty entry, and bare with nothing but a
`position`. The transform service maps `video`.

**A fixed height is the one thing that matters, and `hug` is the trap.** With `height: fixed`
the box is honoured to the point — `fixed_h: 200` draws exactly 200. With `height: hug` the
placeholder draws an arbitrary **256pt**: the renderer's default, the same box an empty `image`
draws, and no function of a clip nobody has uploaded yet. So a hug-height video means the
layout that was previewed and approved is not the layout that ships, and everything below the
video moves when the file lands. `flowkit.video()` therefore has no default for `fixed_h`, and
`verify-config.py` warns on a hug height.

**The checkerboard ignores `borderRadius` — author it anyway.** Corner profiles are flat at
`borderRadius: 16`, and an empty `image` at the same radius draws **identical**, so this is
the placeholder drawing unclipped rather than anything video-specific. Do not "fix" the square
corners you see in the preview by deleting the radius: it is what the clip lands into, and the
radius is also what makes the box read as part of the design instead of a default block. The
same goes for the size and the margins — take them from the surrounding design, the way you
would for an `image`, because the user can restyle this element like any other media element and
should not have to.

**What the element has no room for.** `VideoProps` carries `animation`, `border`,
`borderRadius`, `customMediaID`, `effects`, `height`, `loop`, `margin`, `objectFit`, `opacity`,
`position`, `rotation`, `video`, `visibility`, `width` — and **no `fill`, no `align`, no
`layout`**. To place it, position the parent stack.

**Not observed in any real export.** 0 `video` elements across the 12 tracked and raw configs,
so this shape is authored from the schema plus the render checks above — evidence tier 3, not a
read off builder output. Treat the device check as load-bearing rather than ceremonial.

**Once the user has uploaded the clip, read the config back and check every locale.** `video` is a
catalog ref like an image's, and its value — `{previewUrl, videoUrl, width?, height?}` — is kept
per locale. A builder upload can land only under a non-default locale; every other
language then falls back to the empty default and shows no clip. So after their upload,
`flows config get`, follow the element's `video` (and `videoDark`) ref into
`localization.content`, and confirm the default locale holds a `videoUrl`. If only another locale
does, ask the user to switch the builder to the default language and upload it there.

**Weigh the clip, and say what to upload.** The builder transcodes the upload to HLS (one
rendition, no smaller variant), so the file's size is roughly what every phone downloads, and the
transcode drops transparency: a transparent WebM plays on an opaque box, so ask for a clip whose
background is the design's own. `weigh-config.py` reads
a bound clip's size with a HEAD request and flags one over 5 MB. For a file the user has not
uploaded yet: `stat -f%z clip.mp4` (macOS) or `stat -c%s clip.mp4` (Linux) for the bytes, and,
when `ffprobe` is installed, its codec, size, bit rate and whether it has an audio track:

```bash
ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,bit_rate -of compact clip.mp4
```

A stock Mac has no `ffprobe`, and neither `mdls` nor `afinfo` reads a clip's
streams, so without it report the bytes and say the rest was not checked. `avconvert`, which a
Mac does have, is not a way to shrink one: its presets set the resolution, and a 720p preset makes a
4.3 MB clip 11 MB. What to ask for: H.264, at least 640 px and about 720 px on the shorter side
(the upload refuses less than 640), under 5 MB, and no audio track on a silent loop — the
element has no mute setting, so a track is weight at best.

## Uploading a font

Given the brand's font files (a path each, `.ttf` or `.otf`, one file per weight and style or
one variable file), the upload is yours, through the `fonts` commands of the CLI. Over MCP there
is no font tool yet: run these with the CLI, else the user uploads the files in the builder
([Custom fonts](https://adapty.io/docs/using-custom-fonts-in-flow-builder.md)). No file, only a
typeface name: that is a named ask in the [missing-assets block](build.md#the-missing-assets-block),
never a silent substitution.

**Check each command before its first call:** `$ADAPTY fonts <command> --help` for `list`,
`upload` and every other one you run. When it says there is no such command, try
`npx --yes adapty@latest fonts <command> --help` once (and the beta, as `SKILL.md` says for any
missing command). Still missing: say this CLI cannot manage fonts yet and the user uploads them
in the builder, with the link above.

1. **Look first.** `$ADAPTY fonts list --app "$APP" --json`. A family with the brand's name that
   already has the faces the design needs is the one to use: upload nothing.
2. **Upload all the files in one call, and keep the report:**

   ```bash
   mkdir -p media
   $ADAPTY fonts upload ./Brand-Regular.otf ./Brand-Bold.otf --app "$APP" --json > media/fonts.json
   ```

   Every path is read before the first file is sent: a path that cannot be read stops the whole
   package with exit 2 and nothing sent. Correct the path, then run the whole package again.
   The server reads the family name inside each file: the file joins the family of that name
   (any case) or creates it. `files[]` has one entry per file, with its `result`: `created`,
   `added`, `partly_added` (`kept_faces` are the pairs the family already had), `replaced` and
   `kept` stored or skipped it; `refused` carries `error_code` and `message`, and `next_step`
   when the CLI has one; `failed` means the package stopped at that file (an auth failure, exit 3;
   a network failure, exit 5; or an answer the CLI could not read, exit 4), and `not_sent` marks
   the files after it, which were never sent.
   Exit 4 also means a file was refused, after the report of every file. Send again only the
   files that were refused or not sent, never a stored one.
   - **A `failed` file is uncertain, the last or only file too:** a lost or unreadable answer can
     follow a stored file. Never send it again blind, and check before anything else:
     `$ADAPTY fonts list --app "$APP" --json`. A new face of that file proves it was stored. On a
     `--choice replace` try, a face that is still there proves nothing, because it existed before:
     compare its `file_id` with the one `fonts list` showed before the try. When that still does
     not settle it, tell the user the result is not known and stop: no resend, and do not treat
     the replace as done. Send the file again only when `fonts list` shows it was not stored.
     `flows_to_publish` is then `null`: run `$ADAPTY fonts usage <FAMILY_ID> --app "$APP" --json`
     for each family the package may have changed. When only the usage read failed (every file
     has its result), run `fonts usage` for the families the report names.
   - **A collision** (`refused` with `conflicts` and `choices`): faces of the family the file
     joins already have its weight and italic, or faces anywhere in the app already have its iOS
     name. `conflicts` lists every one of them. Those faces can draw in the app's other flows, so
     the choice is the user's. Offer the choices only when the refusal carries them.
     **`--choice replace` replaces every face that collides at the moment it runs,** which can be
     more faces than the user saw: it checks the collisions again by itself and replaces all it
     finds (and when nothing collides any more, it stores the file as a plain upload). So right
     before you ask, note the `file_id` of the listed faces (`fonts list`) and run that file alone
     again without `--choice`. **When that run stores the file** (`created`, `added` or
     `partly_added`), the collision is gone and the file is in: stop there, report the stored
     faces and go on with the face checks. Never follow it with `--choice replace`: that could
     overwrite the face just added. When it fails, use the `failed` point above. Only when it is a
     fresh refusal with choices, take its `conflicts`: show each listed face with its family,
     say that the file goes on all of them (each flow that uses them gets the new file at its
     next publish) and that the old files cannot be restored, and ask: replace all, or skip the
     file (`--choice keep`). On a yes, run that file alone with `--choice replace` at once, then
     show the user its `replaced_faces` from the report, and say plainly when they differ from the
     faces they agreed to, or when the run stored the file as a plain upload instead. A user who
     agrees to some faces only: `fonts faces replace` per face, as the next points say.
   - **Any other refusal:** read its `message`, and use `next_step` when it is there; relay it (a
     WOFF or WOFF2 file: ask for the `.ttf` or `.otf`). A variable file whose faces are all in the
     family (`font_faces_already_exist`) has no choice; its `next_step` names
     `fonts faces replace`, one face at a time: see the next point.
   - **`fonts faces replace <FACE_ID> <FILE>`** overwrites a stored face's file, and the old file
     cannot be restored. Show the user which face of which family gets which file and say the old
     file cannot be restored; run it with `--yes` only after their yes. Without a terminal and
     without `--yes` it stops with exit 6 (`confirm_required`) and changes nothing: that is a
     missing yes, never a failure to work around.
3. **Check the faces and their names** in the `family` of each entry (or `fonts list` again).
   For each face the design draws with:
   - **Weight and italic.** `metadata_status` `needs_review` or `legacy_unconfirmed` means the
     server could not read the pair from the file. Take it from the file's style name or ask,
     then `$ADAPTY fonts faces update <FACE_ID> --app "$APP" --weight 700 --italic false`.
   - **The iOS name** (`font_alias_ios`) is the PostScript name read from the file. None (the
     upload's `warnings` names the face): publishing refuses a face a text draws with that has
     none. A static file's name is the one it carries. A variable file's instance often declares
     none, and iOS then registers it under the name [flow-schema.md](flow-schema.md) trap 8 gives
     (`<file PostScript name>_<instance style name>`, the hint the builder offers): ask the user
     to confirm the name their app registers, set it with `--ios-name`, then validate again.
   - **The Android name** (`font_alias_android`) is never read from the file: it is the file name
     in the app's `res/font/` folder, without the extension: a lowercase letter first, then
     lowercase letters, digits and `_` only (the CLI refuses any other). Ask the user for the
     name their app uses, or propose one (`brand_bold`) and say the file in the app must have
     that name; set it with `--android-name` (it applies to every face of the same file).

   A change to a family that flows use answers with `flows_to_publish`. `null` means the package
   stopped at a file, the last or only one included, or only the usage read failed;
   `flows_to_publish_error` gives the reason and the next step, and the `failed` point of step 2
   says what to do in each case. Before a change to such a
   face, `fonts usage` names those flows: ask first, and name them in the handoff, because each
   needs a `flows publish` to get the change. `fonts usage` lists only flows that name the
   family by its id; a flow that names it by its name is not listed, so name the family by id.
4. **Name the family in the config, never a face.** On an element:
   `"props": {"font": {"family": {"type": "user", "id": "<family id>"}, "weight": "bold"}}`. On a
   `theme.typography` preset the same two keys sit in `settings`, not in a `font` object:
   `"settings": {"family": {"type": "user", "id": "<family id>"}, "weight": "bold", "size": 30}`.
   Italic only on a rich-text span. Publishing draws the exact weight and style, else the nearest
   weight in the same style, then in any style, the lighter on a tie ([flow-schema.md](flow-schema.md) trap 8).
   Never write `_meta.fonts` by hand. Then `flows config validate`: it resolves the family
   against the app's fonts.
5. **Publish and wait** as [publish.md](publish.md#running-flows-publish) says. `flows publish`
   reads the app's fonts first and, when the copy in `_meta.fonts` is out of date, saves the
   config with the current fonts (the line `Fonts refreshed: …`), then publishes. Poll
   `flows get` until `published` or `publication_failed`. It stops before any write when the font
   read fails, or when a font name in the config matches several families (exit 2: name the
   family by id, or ask the user to rename one). When the copy needs a save, the config answer
   must also carry an integer `updated_at` and a `remote_configs` list; without them it stops
   before any write (`malformed_response`). A current copy needs no save and publishes without
   them. A save that fails stops before the publish: read the config again. A publication that
   fails after the save leaves the saved config.
6. **Say the bundle line every time.** Adapty does not send the font file to the device: the app
   must bundle the same files, under the iOS and Android names above, or users see the system
   font ([Add the font files to your app's bundle](https://adapty.io/docs/using-custom-fonts-in-flow-builder.md)).
   The upload is for the builder and the preview.

## Weighing a config before a write or a publish

Run `python3 references/weigh-config.py draft.json` on the bytes you are about to write (`SKILL.md` phase 5).

It weighs the config itself (mostly image previews, one per image per locale that has its own
value) and asks the asset host for each file's size and pixel size; nothing is downloaded whole.
**Exit 1 fills the weight slot of the ask below** with the three sentences it prints under "Say
this"; its details are for the user's questions and for the fixes. Exit 0 drops the slot. Files it
lists as not measured get one more sentence: their size was not checked. The weight never blocks a save: it is the user's call. On their yes to a fix, apply it
to the draft, run phase 3's gates and the weigh again, and re-render a screen whose image changed:

- **A copy of the default's image in another locale:** delete it. Nothing on screen changes
  ([flow-schema.md](flow-schema.md) trap 1).
- **A heavy PNG or JPEG** (a heavy GIF is the builder's: its WebP would play one frame, so offer
  a `video` from an mp4 of it instead): download it, convert it, upload the WebP and rebind every place
  that uses it. `--max-width` is 3× the widest box it fills, in points; the default, 1290, fits a
  full-width image. The old file stays in their media library: the upload cannot delete.
  ```bash
  mkdir -p media && curl -sSfo media/hero-src.png "<url the weigh printed>"
  python3 references/weigh-config.py webp media/hero-src.png media/hero.webp [--max-width <px>]
  $ADAPTY flows media upload --app "$APP" media/hero.webp --json > media/hero.json
  python3 references/weigh-config.py swap draft.json "<url the weigh printed>" media/hero.json
  ```
- **An image with its own file in many languages:** offered in the slot like the others, as one
  choice between two routes. On "one image": move the words into a text element and show that
  screen like any other change. On "split": build one flow per language group here and hand the
  audiences to the `audiences` skill.
- **A heavy video:** theirs to re-encode; say the size it should get under, and on the new file
  upload it again ([Uploading a video](#uploading-a-video)) and rebind the element.
