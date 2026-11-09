# Template: a Lottie animation that follows the user

Rules, shape and the reply: [custom-elements.md](../custom-elements.md). This file holds only what
is particular to Lottie.

Lottie earns a custom element when the animation is a designer's illustration **and** it changes
per user. Two shapes do that:

- **An illustration that grows to the user's number.** A plant that grows with the streak, a
  character that climbs to the user's level, a jar that fills with the coins they saved. The app
  plays the file from its start to the user's progress and stops there.
- **A segment per user.** One file with named markers, such as `calm`, `focused` and `energized`;
  the app plays the segment that matches what it knows about the user: their plan, their goal, an
  answer from an onboarding that **finished before this flow opened**. The flow cannot hand the
  view an answer from earlier in the same flow, so a quiz answer reaches it only when the quiz is
  a separate flow the app showed first ([chart.md](chart.md), "Where the numbers come from", is
  the same two-flow shape).

**Does not fit:**

- An animation that plays the same for everyone: an animated WebP in an `image`, or a `video`.
  No app release, and the file can be replaced in the builder.
- A plain progress ring or bar: the app draws one natively in a few lines, with no Lottie file.
  It is still a custom element when the user asks for it, and the docs recipe below is one; say
  that a native view does the job, and build the box either way.

## The box

| Field | Value |
| :--- | :--- |
| Type | `lottie_animation`, for every Lottie box in the app |
| ID | the animation's name, which is also the file's name in the app, such as `streak_plant` for `streak_plant.json` |
| Height | fixed, from the reference; a square animation in a full-width box sits centred, so give the box `alignH`/`alignV` `center` |
| Width | `fill` |

```python
fk.custom_element('lottie_animation', 'streak_plant', fixed_h=260,
                  align_h='center', align_v='center',
                  fallback=[fk.image(fk.PLACEHOLDER, fixed_h=260, fit='fit')])
```

**Fallback:** a still frame of the illustration at a representative state (the plant half grown,
the mascot in its resting pose), as an `image` with `fit='fit'` at the box's height. Ask the user
for that frame with the other asset asks.

**Around the box:** the number the illustration shows (the streak, the level), in text beside it
as a custom tag. The text also reaches users who see the fallback.

## What the app's view does

Tell the user, in plain words; on a yes, this is what you write ([custom-elements.md](../custom-elements.md#on-a-yes-the-apps-view)):

- Adds Lottie to the app (the `lottie-ios` package) and the animation file to the app bundle,
  named after the ID.
- **Grows to a number:** plays the file from the start to the user's progress (0 to 1) once and
  stops; the app works the progress out from its own data. The file needs nothing grown on its
  first frame, fully grown on its last, and a steady pace with no easing, or halfway through the
  file is not half the progress: say so to whoever makes the file.
- **A segment per user:** plays the segment between the markers named for the user's state, and a
  default segment when the app does not know it. The marker names are a contract between the file
  and the code: list them for the user.
- Draws nothing when the file is missing, so users see the fallback instead of an empty box.

Docs: https://adapty.io/docs/custom-element-lottie-animation.md (the recipe fills a streak ring;
the setup is the same for any Lottie file).

## On the device

Open the screen at a few progress values (0, half, full), or once per segment, and check what
plays; remove the file from a build to see the fallback.
