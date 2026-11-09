# Template: a Rive animation that reacts

Rules, shape and the reply: [custom-elements.md](../custom-elements.md). This file holds only what
is particular to Rive.

**Fits** an animation that answers the user or shows their data: a mascot that waves when tapped,
a slider or a knob the user drags inside the animation, a health or energy bar at the user's
level, a rewards counter with their coins. Two things drive it: the file's **state machine**
answers touches inside the box, and **data binding** carries the app's values into the file (a
number, a text, a choice from a list, an image), so it reacts to the user's own data.

**Does not fit** a one-way animation that plays the same for everyone: an animated WebP `image`
or a `video`. And not a control the **flow** has to read: a tap inside the Rive view never selects
an answer, navigates or sets a variable. A choice the flow branches on stays a flow element
(`selectable`, a button), and the animation beside it only illustrates.

## The box

| Field | Value |
| :--- | :--- |
| Type | `rive_animation`, for every Rive box in the app |
| ID | the `.riv` file's name in the app, such as `mascot` for `mascot.riv` |
| Height | fixed, from the reference |
| Width | `fill` |

```python
fk.custom_element('rive_animation', 'mascot', fixed_h=240,
                  align_h='center', align_v='center',
                  fallback=[fk.image(fk.PLACEHOLDER, fixed_h=240, fit='fit')])
```

**Fallback:** a still of the character in its resting state, as an `image` with `fit='fit'`.

**Placement:** never inside a `carousel`, or any container that answers a swipe, when the user
drags inside the animation.

## What the app's view does

- Adds the Rive runtime for Apple platforms (the `RiveRuntime` package) and the `.riv` file to the
  app bundle, named after the ID.
- For the Type `rive_animation`, plays the file named by the ID with its state machine, so taps
  and drags inside it work with no code beyond showing it.
- When the animation shows the user's data, sets the properties of the file's view model from
  where the app holds that data: the level, the coin count, the chosen item. The property names
  are a contract between the file and the code: ask the designer for them, and list them for the
  user.
- Draws nothing when the file is missing.

Docs: https://adapty.io/docs/flow-custom-elements.md (no Rive recipe yet; the Lottie recipe
https://adapty.io/docs/custom-element-lottie-animation.md shows the same setup with a different
player). Rive's own data binding: https://rive.app/docs/runtimes/data-binding, and its demos with
sample files: https://rive.app/docs/runtimes/demos.

## On the device

Tap and drag inside the animation and check each state; check that a swipe there does not move
anything else on the screen.
