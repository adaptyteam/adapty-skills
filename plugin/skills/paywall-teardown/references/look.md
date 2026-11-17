# The look

How a screen you design should look. Read it in Design, after the archetype and before the
first element. It sets the look for the whole flow when an onboarding comes with the
paywall: one direction, every screen.

## The app's design comes first

**The style of a flow is the app's style.** When the app has a design, take its style from it —
background, accent, type scale and weights, corner radii, button and card treatment, icon style —
from wherever you can see it: its code when you are in its repo (theme, colour assets,
components), its existing flows (the ones its placements show first), screenshots of the app, or
brand colours and fonts the user gave you. Do not invent a style then: the app has already
chosen. A near-black screen with a neon accent is exactly right for an app that looks like that.

**The style is fixed; the layout is not.** A brand settles colours, type and corners. It does not
settle how a question lays out its options, what the paywall is built around, or what the
signature element is. Where the app already has a screen of the same kind — a quiz, a paywall —
follow its layout too. For everything it does not have yet, invent the layout the same way as a
look, inside the brand: four layout concepts, each from its own rolled starting point (step 2
of [Inventing the look](#inventing-the-look-when-the-app-has-none)), that all use the app's
colours, type and corners, each written as the four answers in
[Inventing the paywall's layout](#inventing-the-paywalls-layout); drop the most obvious; roll
among the three left with the command in
[Inventing the look](#inventing-the-look-when-the-app-has-none). Name the one you built and offer
the other two, plus the standard layout as a test arm (step 6).

**Invent the whole look only when the app has no design you can see**: a new app, nothing in the
session, nothing given. Say in the reply that you chose the look because there was nothing to
take it from, and ask for the app's design so the next build can follow it.

## A look nobody chose is a defect

What fails is not a style; it is the same style for every app. With no app design and no
direction, every build lands on one of two looks:

- a white or off-white background, one accent colour, the system font at default weights, a small
  uppercase label over a bold heading and a grey subhead, cards with an icon in a tinted square, a
  full-width rounded button pinned at the bottom, and an empty image box at the top;
- told to avoid that: a near-black or navy screen with one neon accent, heavy headings and sharp
  corners — for a fitness app and a document scanner alike.

Either is fine when it is the app's design or what the roll drew. Either is a defect when it is
what you reached for by default.

## What you can make without a single asset

No photo is not a reason for a plain screen. The builder draws all of this:

- **Type as the hero.** A 44–64 pt heading, heavy weight, tight letter spacing, two or three
  words per line. A big number the user typed ("3 days a week") set larger than anything else.
- **Colour blocks and gradients.** A full-bleed coloured top half, a gradient background, a
  gradient button or card border, a dark screen.
- **Icons as illustration.** One icon at 96–160 pt in the fill weight, on a coloured circle or a
  gradient, instead of six small icons in tinted squares.
- **Shapes as product.** A "page" card, a progress ring, a calendar strip, a stack of three
  tilted cards — the app's output drawn from stacks, borders and radius.
- **Layouts other than a list.** A 2×2 grid of choices, a horizontal row of five for a scale, a
  carousel, a sliding sheet over a full-bleed colour, a statement centred on an empty screen.
- **A radius that means something.** Sharp corners (0–6) read precise and serious; large ones
  (20–28) read friendly and soft. Pick the scale on purpose and keep it to the three values in
  [One design system](#one-design-system-for-the-whole-flow).

An empty image box is not a design. When you have no asset, design the space with the above
instead, and name what a real image would add in the asks.

## Inventing the look when the app has none

The first look you think of is the one every run thinks of, and a list of styles to pick from only
makes a bigger set of the same answers. So when there is no app design to follow, invent the look:
several concepts of your own, drawn from this app's world, then a roll among them.

1. **Write the app's promise and audience in one line**, from the brief: who it is for and what it
   gives them ("strength at home for busy adults", "clean PDFs from phone photos").
2. **Roll a starting point for each concept before you think of any.** Left alone, every run
   invents nearly the same four concepts for an app, so a roll among them still lands on the same
   screen. Run this and use the four starting points it prints, one per concept, in order:

   ```bash
   python3 -c "import random; print(random.sample(['an object the user holds', 'a place where the app gets used', 'a material or texture', 'a moment in the user\'s week', 'a ritual or habit', 'a document or form', 'a tool of the trade', 'a time of day or season', 'a game or toy', 'a journey or vehicle', 'a sign, label or signal', 'a collection', 'a prize or reward', 'the problem the app removes', 'a person the user works with', 'the weather or the sky', 'a container', 'a piece of furniture'], 4))"
   ```

   **Invent four concepts, each from something in the app's world that fits its starting
   point** — for a plant-care app, "a container" gives a seed packet, "a time of day" gives
   morning light on a windowsill. When two starting points still lead to the same concept,
   change the second one. For each, write:
   - **Name and source:** two or three words, and the thing it comes from.
   - **Colour:** background, surface, text, accent and selected state, as hex values.
   - **Type:** sizes, weights, case and letter spacing for heading, body and button.
   - **Question screen:** how the question and its options are laid out — not "cards" or "a
     list", but what this concept does with them.
   - **Paywall:** the four answers in
     [Inventing the paywall's layout](#inventing-the-paywalls-layout), built from what the
     archetype table in `SKILL.md` allows (you may combine archetypes).
   - **Corners, spacing, and one signature element** that no other concept has.
3. **Make them really different.** Any two concepts differ on at least four of colour, type,
   question layout, paywall composition, corners and signature element. None may be either look
   in [A look nobody chose](#a-look-nobody-chose-is-a-defect).
4. **Drop the most obvious one** — the concept closest to how a typical app in this category looks.
5. **Roll among the three left, with a command, not in your head.** A model asked to pick at random
   picks its favourite. Run this and build the concept it picks (0, 1, 2 in the order you wrote
   them):

   ```bash
   python3 -c "import random; print(random.randrange(3))"
   ```

   Never roll again for a result you like better, and never overrule the roll with a fact about the
   category — all three were invented for this app.
6. **In the reply, name the concept in one plain line and list the other two in one line each**, as
   looks you can rebuild it in. Then offer the standard layout — the obvious concept you dropped
   (see [Inventing the paywall's layout](#inventing-the-paywalls-layout), rule 3) — as the version
   to A/B test against: it is what most top apps use, nobody has shown the invented look sells
   better, and a test is how the user finds out. On a yes, build it in the same design system as
   the one you built — same colours, type and corners — so the test compares layouts, not looks.
   The shape, not words to copy: "I built it as a seed packet: kraft paper, stamped type, answers
   as tick boxes. I can also do it as a garden journal or as windowsill light, or build the
   standard layout most top apps use, so you can A/B test the two."

## Inventing the paywall's layout

A layout concept is the structure of the whole screen, not a way to draw the benefit list. Four
concepts that each redraw only the benefits (as a table, as task rows, as a sticker grid) are one
screen four times: header, benefits block, plan cards, full-width button, fine print. For each
concept, write these four answers; together they are the concept:

- **What the screen is:** one thing from the app's world the whole screen pretends to be, not "a
  paywall with X".
- **Top half:** what fills it — a scene, one big statement, the user's own number, the plans
  themselves, the app's core loop before and after.
- **Where the plans live:** inline under the value, in a pinned bar, inside the scene as objects
  in it, behind tabs, or as the top half.
- **Where the value lives:** rows, a table, objects in the scene, one sentence, a progression.

Then hold the set to three rules:

1. **Any two concepts differ in both the top half and where the plans live.** Two that differ
   only in how the benefits are drawn are the same concept.
2. **At least one concept is a scene from the app's world**: its character, its currency or its
   core loop, built from what the builder draws — icons on shapes, stacks, gradients, big type
   ([What you can make without a single asset](#what-you-can-make-without-a-single-asset)). When
   the app has a character, that concept shows it as one real illustration at a real size —
   never an icon on a coloured circle, which reads as clip art. With no file of the character,
   draw it and upload it (`flow-generator`'s `references/media.md`, the draw-and-upload ladder)
   on a run nobody can answer, or ask for the file when someone can; say in the reply that it is
   a stand-in and ask for the real art.
3. **The obvious concept is a structure, not a name.** A concept is the obvious one when its top
   half is a heading or statement (with or without an icon or badge above it), its value is a
   block under that, and its plans sit inline under the value — whatever it is called and however
   the block is drawn: a sticker sheet, a checklist, a table, a grid of tiles. The commonest
   paywall in the stores is this structure with a fixed set of parts: a short headline, a
   feature checklist, two plan cards with the annual one pre-selected, a button that names the
   free trial, a "cancel anytime" line under it, and usually no image. That is how a typical app
   sells, not evidence that it sells better or worse, and a concept made of those parts in a new colour or
   style is the obvious one too. Check all four concepts against this before you drop one; every
   concept that matches it is dropped, and you write a new one in its place until three are left
   that do not. It is dropped from the build, not from the reply: offer it as the version to A/B
   test against ([Inventing the look](#inventing-the-look-when-the-app-has-none), step 6).

**How to build a scene.** A scene is not a card with a grid in it; a grid in a box is the obvious
structure in costume. Four things make it a scene, and none of them is an arrangement:

- **It owns its part of the screen,** edge to edge — no card border around it.
- **One subject is large** — the character or the core object, clearly the biggest thing.
- **Features are things in that world,** not rows of icons: a watering can, a seed packet, a
  second plant — set in order, one line or one column of the same size, never scattered.
- **The plans belong to the scene** — standing on it, held by it, hanging from it, printed on it —
  not a separate section after it.

Everything else is the concept's to choose, and **the first choice is the viewpoint**: the
default one — a sky over the subject standing bottom-left, objects floating around it, the plans
on a ground band below — is the obvious scene, and every scene drifts there. Pick a different
view for each scene concept, for example:

- **Close-up:** the subject's face or one object fills the screen; the plans sit in the frame.
- **Inside:** the room the subject lives in, seen from within — a stall, a desk, a shelf — with
  features on its walls or shelves.
- **From above:** a map, a paddock, a board laid flat, with the plans as two places on it.
- **A moment:** the core loop caught mid-action — a plant being watered and a new leaf opening — with
  the plans as what comes next.

A scene can be quiet: one object or one illustration on a plain background, with everything
else ordinary, is still a scene.

**Different is not enough; it has to look good.** Whatever the concept, the built screen meets
all of these, and the back pass checks them on the render:

- **One focal element, clearly the largest thing on the screen** — the scene, the character, the
  plans, the statement. Everything else is visibly smaller.
- **The app's card treatment goes on what the user taps.** Outlines, hard shadows and filled
  cards mark plan cards and buttons; other content sits on the background or in one container.
  No box inside a box, no outlined tags inside an outlined card.
- **Say each thing once, at a readable size.** A feature is named in one place, in one short
  line; body text no smaller than the body preset, captions only for legal and billing lines.
- **A short headline.** Six words or fewer in the language you write it in; most paywall
  headlines run about five. A longer one is usually two ideas, so move the second into one
  subhead line.
- **One idea, shown in one place.** The concept lives in the signature element — the headline, the
  plan cards, one illustration — and the rest of the screen is plain and ordered. Not every
  element dresses up as part of the world: if the features, the plans and the background all play
  a role in it, the screen is a costume, not a design.
- **Few colours.** A background, one surface, the ink, and one accent for the button and the
  selected plan. Items of the same kind share one colour; features in five different colours are
  noise.
- **Everything on one grid.** Items of the same kind are the same size, aligned to the same edges
  and spaced evenly. Nothing tilted, scattered or at uneven heights — an idea the screen can only
  carry by breaking the grid is too loud for a paywall.
- **Content before decoration on the first screen.** When a bar is pinned to the bottom, the
  plans, the button and the value the user is paying for are visible without scrolling. Space
  that holds nothing — a decorative shape's empty curve, padding around an emblem — is cut first;
  if the value still does not fit, cut it to its strongest three lines rather than push it below
  the fold. A deliberately long, scrolling paywall is a different layout and is exempt.
- **Every part of the screen is designed.** Either fill it on purpose — a full-bleed scene, a
  colour block, type that runs edge to edge — or frame the content with space that is clearly
  meant. A leftover band between two blocks, or content cut off under a pinned bar, is a defect.

The shape, not words to copy — four concepts for a plant-care app:

| Concept | What the screen is | Top half | Plans | Value |
| :-- | :-- | :-- | :-- | :-- |
| Seed packet | the back of a seed packet | the packet front, big plant name | the "packet sizes" printed on the back | the growing instructions |
| Greenhouse shelf | a shelf that fills up | pots appearing on the shelf, one per Plus feature | a pinned bar under the shelf | the pots themselves |
| Watering calendar | this month's schedule | a month grid with a drop on each reminder day | two tabs under the grid | one sentence |
| Plans first | the choice itself | two large plan cards | the top half | one line under the button |

## One design system for the whole flow

A flow is one product, so every screen is built from the same few parts. Before the first screen,
fix these, write them as named values in the build, and use nothing else:

- **Colours:** background, surface, text, muted text, accent, selected, and a divider. A screen
  that needs a new colour is a sign the system is wrong; change it everywhere.
- **Type:** five presets — display, title, body, caption, button. No size or weight outside them.
- **Corners: exactly three radii** — one for small controls and chips, one for cards and plan
  cards, and full rounding for pills — or square everywhere. A fourth value is a defect.
- **Spacing:** one scale (for example 4, 8, 12, 16, 24, 32); screen margins and the gap between
  options are the same on every screen.
- **One component per screen type, built once and reused:** the option row of a single-choice
  question, the tile, the scale row, the input, the primary button, the secondary link, the plan
  card. Two single-choice text questions must look identical — same heading position, same option
  style, same button — and differ only in their words. Variety comes from using a different screen
  type, never from restyling the same one.
- **The paywall uses the same system:** its plan cards are the option cards' family, its button is
  the flow's button, its corners and type are the flow's.

**In the back pass, put screens of the same type side by side** and compare them part by part. Any
difference you did not mean is a defect, and so is a radius, colour or type size outside the
system.
