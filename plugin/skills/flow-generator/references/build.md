# Building a new flow

`SKILL.md` phase 2 for a new flow, or a screen whose design, products or assets you resolve. Read each part at the moment it applies.

## Creating the flow

**New flow** — `flows create`, then seed its config from one the user already has
(`flows list` → `config get`) so theme, fonts, locales and products are real — in **Rebuild** mode
(below) the reference's style then replaces the seed's theme. Its first
`config update` omits `--expected-updated-at`. **A new flow is the safe default for anything the
user calls new**, because `config update` replaces everything and generating over a flow with
content discards that content. **Run `flows create` once per new flow**, as one explicit command with
its `--app`, never in a loop: it does not deduplicate and there is no delete, so a second call leaves
a second flow in the user's account for good. Then `flows get` the id to confirm it landed in that
app. Keep
the id it prints, and on any retry (a failed save, a read-back that looks wrong, a later turn)
write to that id. Coming back without it, look for the name in `flows list` before creating.

## Were you given a design, and whose is it?

**Were you given a design, and whose is it?** Answer it out loud: it decides where each part of
the screen comes from.

| What you were given | Mode | Structure from | Style and copy from |
| :--- | :--- | :--- | :--- |
| Their own design: their Figma, a screenshot of their own app, or an explicit "rebuild / match / copy this exactly" | **Rebuild** | the reference | the reference |
| Someone else's design with the mode said: "in my style", "inspired by", "adapt this for my app" | **Adapt** | the reference | **the app** |
| No design | **You choose** | a teardown skill (below) | the app |

**When the request names neither mode — "build the same onboarding", "something like this" — ask
before you build**, one question, and wait:

> Do you want an exact copy of this, or the same structure in your app's own style and words?

A wrong guess costs a whole build and a flow that cannot be deleted; the question costs one turn.
**Only when nobody can answer** (an unattended run, or the user said not to wait) take **Adapt**
and say so in one line.

**In Adapt, the reference gives the shape and the app gives everything else.** Take the sequence,
the sections, the component patterns and the hierarchy from the reference. Take the palette, type
scale and weights, corner radii, button and card treatment, icon style and spacing rhythm from the
app, and **write the copy for the app**: its name, its products, its voice. Never ship another
brand's name, its claims, its offers or its social proof.

**Take the app's style from its code** when the session is in its repo (theme, colour assets,
button and card components, strings), **else from its own flows** — the ones its placements show
first. With neither, ask once; with no answer, use the reference's style and say so.

**In every mode, keep Adapty's fluid layout discipline** (`width: fill`, `height: hug`,
`position: relative`): never hardcode fixed dimensions or offsets to match a screenshot's pixels,
because fixed geometry breaks across devices (team-diagnosed). In **Rebuild**, compare against the
reference file rather than your memory of it (phase 4). **No design means you are choosing it** —
"build me a paywall", "build me an onboarding", "make one that converts" — and the request map only
turns nouns into element types; it says nothing about what sells. Before choosing, ask once
whether they have a reference screenshot or an app whose look to follow, in the same message as
your other phase-2 asks, never as a round of its own; on a no, no answer or an unattended run, the
teardown below is the reference.

## When you choose the design: the teardown is the reference

**When you are the one choosing, a teardown skill is the reference, and which one is decided by
what you are building — not by which you reached for last time.**

| What you are building | The reference | What it returns |
| :--- | :--- | :--- |
| One screen that sells — a paywall | **`paywall-teardown`** | An **archetype** (the screen's composition) plus the patterns this vertical needs |
| A sequence — onboarding, welcome, quiz, activation | **`onboarding-teardown`** | A **skeleton** (the sequence's shape) plus the patterns, placed per screen |
| Both — an onboarding that ends on a paywall | **Both.** `onboarding-teardown` owns the sequence and the seam; `paywall-teardown` owns the paywall screen itself | Run the sequence one first: it decides what the paywall must reflect |

Invoke it before you write anything. Both name the values they refuse to invent — a rating, a
review count, an outcome stat, a discount, a hero asset, and for a sequence the thing the app must
really deliver behind a personalized promise. **Put those asks to the user before you write the
config**, and leave the element out rather than filling it with a plausible number: a missing
element is recoverable, a fabricated rating is a lie in front of real buyers. Build the shape it
names and **do not substitute one you built last time** — that is how two unrelated verticals got
the same screen. It also grades the result in phase 4, where a correction is still free. And when
the user wants to know how *good* a flow is rather than to change it, that answer is a teardown,
not a transform.

## In a build there is nobody to interview

**In a build there is nobody to interview.** `onboarding-teardown`'s six questions are its
front door when a user brings a flow to it; invoked from here they are answered from the brief,
the config and the catalog, and whatever is left becomes one batched ask alongside the others
above. Do not start a six-turn questionnaire in the middle of a build.

## Products: catalog first, store ids second, create last

**Products are the user's to pick — catalog first, store ids second, create last.** For any
screen that sells, resolve the products **before the design**, in this order, and never skip a
step silently:

1. `$ADAPTY products list` and show what exists — title, period, store bindings — and ask which
   of these belong on the screen. Most accounts already have the right products. An offer on a
   card (a trial, an intro or promo price) is bound by its `id` from `product-offers list`, and an
   App Store trial by no offer at all
   ([products.md → Where offer ids come from](products.md#where-offer-ids-come-from)).
2. Only if nothing fits: ask for their **store product ids** (App Store product id; Google
   product id **plus base plan id** for subscriptions) — this skill creates a product only with
   them, since one with no binding sells nothing until a push creates it in the store
   (`adapty-integration`, path C), so asking later just stalls the create.
3. Only then `products create`, behind its own confirmation gate
   ([products.md → Creating a product](products.md)).

Before the design, because the catalog *gates* it: a trial timeline needs a verified offer, a
period switcher needs plans differing only by period, a price variable needs a matching period.
And picking for them is not a shortcut — it decides what they sell, and it is the one choice on
the screen a screenshot cannot show.

## Something only the app knows: a custom tag

**Something only the app knows is a custom tag, and it costs app code.** The user's name, a
coin balance, a streak, a level, days left, the plan they are on — anything the flow cannot work
out by itself. Users ask for what it shows, never for "a custom tag". **First check the flow does
not already ask for it**: a value the user typed or picked on an earlier screen is an input's
`<customId>.value` or a group's `selectedOptionId`, and showing that needs no app code at all.
Otherwise declare it with `flowkit.app_value()`, show it with `Var`, and settle two things here,
batched with the product questions: the **name** the app's code will pass (theirs, if they
already have one) and the **fallback** — what every user sees until the app supplies the value.
With nobody to ask, choose both and say so. Text only — branching on one is not buildable
([flow-schema.md → trap 25](flow-schema.md#25-a-value-only-the-app-knows-is-a-custom-tag--shown-in-text-never-read-by-logic)).

## Assets: upload the file, then build with its URL

**Assets are resolved here too — upload the file, then build with its URL.** The upload reads a
**path**, so **an image you can only see is not an image you have**
([media.md → Getting the file](media.md#getting-the-file-the-upload-needs-a-path-not-a-picture)).

For every asset the screen needs, one of three states, decided before you write the element:

1. **You have a path that reads** — one they gave you, or a project file you found and *named*.
   A PNG or JPEG over 500 KB is converted first, and you upload the WebP and say so:
   `python3 references/weigh-config.py webp <file> media/<name>.webp`. A GIF does not upload and an
   animated WebP plays one frame, so motion is a `video` element
   ([media.md → The video placeholder](media.md#the-video-placeholder)).
   Upload it now as [media.md → The call](media.md#the-call) says — `--json` into a record file,
   **three** values off it, `previewValue` included — and bind them in one of
   [the two shapes](media.md#binding-the-url-two-different-shapes). **An asset you uploaded
   earlier is rebound from its record file, or lifted out of a config that already binds it —
   never re-uploaded, and never bound as a bare URL you remembered**
   ([When you have a URL and no preview](media.md#when-you-have-a-url-and-no-preview)).
2. **You can see the image but have no path** (pasted, attached), or they named one they have not
   sent — **ask for a path**, once, batched with your other asks. Never guess one: a guess that
   misses fails loudly, and a guess that *hits* ships the wrong picture in a screen that renders
   perfectly. A URL they pointed at is fetchable, but say what you are downloading first.
3. **Nobody has a file** — a **styled empty `image`** where the graphic occupies a box:
   `borderRadius`, `objectFit`, and a **fixed size taken from the reference**, on the element
   itself, so the upload lands styled and the layout is checked at the size the asset will fill.
   Where it has no box of its own — a texture, a glow — leave it out rather than approximating it.
   Either way it goes on the missing-assets list, never into a paragraph. **Never a made-up URL**
   (trap 5). If the reference itself contains the graphic on a *flat* backdrop, you may be able to
   cut it out instead — [`references/crop.py`](crop.py), which refuses rather than
   guessing when the backdrop is textured or the box is wrong.

**A clip is in none of those three states**: the upload refuses a video, so emit a sourceless
`video` element — `flowkit.video(fixed_h=…)` or the catalog's `video-hero` / `video-card` — and
say in words that they upload it in the builder
([media.md](media.md#the-video-placeholder)).

**Upload before the preview loop, not after it, and upload each asset once.** A placeholder does
not occupy the space the real asset will, so a screen previewed with placeholders is a screen whose
layout was never checked — and the upload does not deduplicate, so re-running it per iteration
litters the user's media library permanently
([media.md](media.md#geometry-what-changes-when-the-asset-lands)).

## The missing-assets block

The missing-assets block goes out in phase 2, batched with the product questions, because a path
they hand over turns a placeholder into a finished screen. **A drawing of yours that is already
uploaded is not missing:** it goes only in the drawings line, never as a row of the table, and
when nothing but drawings and fonts is left, drop the header, the table and the routes and print
only those lines. **The upload routes are not symmetric** — offering both on every row recommends
a path that ends in a refusal:

> **`<n>` assets missing — the screen ships with placeholders until these land.**
>
> | | what | where it goes | size |
> |---|---|---|---|
> | 1 | `<what it is, in their words>` | `<where on the screen>` | `<w>`×`<h>` |
>
> Tell me which, per asset or for all of them:
> - Send me a path — I'll upload and bind it. Images only.
> - Upload it yourself at https://app.adapty.io/flows/`<FLOW_ID>`/builder — the placeholder is
>   already styled, so it lands finished.
> - Design around it — I'll replace that region with something the format can build, and say
>   what I chose. Right when the reference is someone else's screen and that asset was never going
>   to be yours.
>
> Until you answer, they ship as placeholders.
>
> `<only if you drew stand-ins:>` `<n>` are **drawings of mine**, already uploaded so the screens
> look finished — `<which>`. They are stand-ins, not your art: replace each one the same way, by
> path or in the builder.
>
> `<only if a clip is missing:>` `<what>` is a **video**, and there is no upload path for a clip —
> not one I can take either, so this one is yours whichever route you pick. The element is on the
> screen already, sized `<w>`×`<h>` to match the design: open
> https://app.adapty.io/flows/`<FLOW_ID>`/builder, click it and upload the file. Nothing else
> about the screen changes.
>
> `<only if a face is missing:>` `<what>` is set in a `<description>` this account lacks; I'm
> using `<substitute>`, which `<how it differs>`. Fonts are **builder-only** — I can't upload one:
> https://adapty.io/docs/using-custom-fonts-in-flow-builder.md — upload it, set the iOS and
> Android font name on every face (the flow will not publish without the iOS one), save the flow in
> the builder, then tell me the family name and I'll point the theme at it. The uploaded file is for
> the editor preview only: **your app must bundle the font file too**, as that page shows.
