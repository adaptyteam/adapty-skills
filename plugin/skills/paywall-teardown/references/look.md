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
look, inside the brand: four layout concepts that all use the app's colours, type and corners and
differ in question layout, paywall composition and signature element; drop the most obvious;
roll among the three left with the command in
[Inventing the look](#inventing-the-look-when-the-app-has-none). Name the one you built and offer
the other two.

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
2. **Invent four concepts, each from something in the app's world** — an object, a material, a
   place, a moment or a ritual from how people use it (for a plant-care app: a seed packet, a
   watering can, a garden journal, morning light on a windowsill). For each,
   write:
   - **Name and source:** two or three words, and the thing it comes from.
   - **Colour:** background, surface, text, accent and selected state, as hex values.
   - **Type:** sizes, weights, case and letter spacing for heading, body and button.
   - **Question screen:** how the question and its options are laid out — not "cards" or "a
     list", but what this concept does with them.
   - **Paywall:** how the plans, the offer and the button are composed, built from what the
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
   looks you can rebuild it in. The shape, not words to copy: "I built it as a seed packet: kraft
   paper, stamped type, answers as tick boxes. I can also do it as a garden journal or as
   windowsill light."

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
