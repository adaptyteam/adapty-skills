# Custom elements: a view from the app, inside a flow screen

A **custom element** is a box on a flow screen that the app fills with its own native view. The
flow carries the box, a **Type** and an **ID**; the app's code matches the pair and draws whatever
it wants there: a Lottie or Rive animation, a map, an interactive chart, a camera preview, any
view the app already has. When the app does not draw it, the flow shows the box's own children,
the **fallback**.

Users rarely say "custom element". They ask for a thing the builder has no element for. This
file owns when that thing becomes a custom element, how to build one, and what to tell the user.
The per-use-case templates are in [custom-elements/](custom-elements/). Everything particular to
a platform comes from its docs pages, listed once in [Docs per platform](#docs-per-platform).

## When the request becomes a custom element

Read the request through this table before you call anything "not in the builder yet". The
first row that fits wins.

| The user wants | Build |
| :--- | :--- |
| a picture, or an animation that plays the same for everyone (confetti, a looping hero, a recorded demo) | an `image` (an animated WebP plays) or a `video` — no app code, and the file can change without an app release. **Not a custom element** |
| an animation that reacts: fills to the user's number, answers a tap, follows a state (a plant that grows with the streak, a mascot that waves on tap) | a custom element: [lottie.md](custom-elements/lottie.md) or [rive.md](custom-elements/rive.md) |
| a map, places near the user | a custom element: [map.md](custom-elements/map.md) |
| a chart of the user's data, a chart the user drags along or taps | a custom element: [chart.md](custom-elements/chart.md) |
| the camera: a live preview, a scanner, a mirror | a custom element: [camera.md](custom-elements/camera.md) |
| any other view the app already has or can build: a 3D model, a native wheel, a game, a widget preview | a custom element with the generic shape below; no template |
| something a button **does**: sign in, create an account, ask for a permission on its own, open the app's own screen | a custom action, not a custom element. The element cannot run an action (below) |
| a value the app knows, shown as text: a name, a streak number, a balance | a custom tag (flow-schema.md trap 25), not a custom element |

A custom element and the other routes combine: the streak number as a custom tag in the title,
and the plant that grows to it as a custom element below.

## What it can and cannot do

What it is, read from the builder, the transformer and the SDKs:

- **The app draws everything inside the box.** The flow sends the app only the Type and the ID.
  The data the view shows (the streak, the weights, the location) comes from the app's own code,
  never from the config. Nothing in the flow, not a variable, a quiz answer or an input value,
  reaches the view.
- **It cannot act on the flow.** The element has no interactions: a tap inside the native view
  does not navigate, purchase, close or set a variable. The builder offers no Interactions tab
  for it, and the transformer deletes any it finds. Keep every button with a flow action
  **outside** the box.
- **Taps inside the view stay inside the view.** A map pans, a chart answers a drag, a Rive
  mascot reacts. A link the view opens goes to the system browser.
- **The builder canvas shows the fallback, never the native view.** No render does, nor the
  Adapty mobile app's preview; only a device with an app build that serves the Type shows the
  real thing.
- **Users see the fallback** when their app version has no view for this Type, when their app's
  Adapty SDK is older than custom element support, when the Type or ID is spelled differently
  from the app's code, and when the app chooses not to draw (a missing file, a denied
  permission). So the flow can be published before the app release.
- **Platforms:** the native view is served by the Adapty SDK 4.4 and later in a native iOS or
  Android app. The cross-platform SDKs (Flutter, React Native, Unity, Kotlin Multiplatform,
  Capacitor) are **not yet** supported and show the fallback. Say this when the app is not native
  iOS or Android, and build the fallback as the real design for those users.
- **The native view changes only with an app release.** The fallback, the Type, the ID and the
  box's size change with a flow publish.

## The shape

```json
"ce_plant": {
  "id": "ce_plant", "type": "custom-element",
  "props": {
    "customType": "lottie_animation", "customElementId": "streak_plant",
    "width": {"type": "fill"}, "height": {"type": "fixed", "value": 220},
    "layout": {"direction": "vertical", "alignH": "center", "alignV": "center",
               "distribution": {"type": "gap", "gap": 0}, "clipContent": false},
    "position": {"type": "relative"}
  }
}
```

The fallback is the element's ordinary hierarchy children, laid out by its `layout`:
`{"id": "ce_plant", "children": [{"id": "img_plant_still"}]}`. Build it with
`flowkit.custom_element()`, which enforces every rule below:

```python
fk.custom_element('lottie_animation', 'streak_plant', fixed_h=220,
                  fallback=[fk.image(fk.PLACEHOLDER, fixed_h=220, fit='fit')])
```

- **`customType`**: lowercase letters, digits and underscores only, never empty. Any other
  spelling stops the publish. Name it for the **kind** of view, so one app-side branch serves
  every box of it: `lottie_animation`, `map`, `line_chart`, `camera_preview`.
- **`customElementId`**: names **this** box, and the app may use it to pick the content: a
  Lottie file name, which chart. Use the same character set. Two boxes on one screen never share
  a Type and ID pair (the builder warns, and the app could not tell them apart); across screens
  and flows the same pair is the same view.
- **`customType` and `customElementId` live in base `props` only**, never in `propsByState`.
- **Height is `fixed`.** A native view that sizes itself to its space, a map, a chart, a camera,
  collapses to almost nothing in a `hug` box. Take the height from the reference, or from the
  template. Width is usually `fill`.
- **No `interactions`** on the element.
- **The fallback is required, and it is the design for every user the app does not serve.** A
  box with no children shows those users an empty area of its size. Make the fallback a finished
  piece: a still picture of the native view, styled to the box (`image` with the box's height and
  `objectFit`), or a short text block; for a picture nobody has a file for yet, the styled
  placeholder and ask from [media.md](media.md).
- **Fallback children are `relative` or `absolute`**, never `fixed`, and never a `bottom-sheet`,
  `sliding-sheet` or `footer`: the transformer refuses them and the whole box is dropped.
- **Keep essential UI outside the box.** Users see the native view **or** the fallback, never
  both: a Continue button or a price inside the fallback disappears for exactly the users whose
  app draws the view.
- **Not inside a carousel or another container that answers a swipe** when the view answers a
  drag (a map, a chart, a Rive mascot): one drag moves both.
- **Not inside a product card or another selectable element:** when the selection changes, the
  native view can lose its state (a played animation restarts, a map recentres).
- **`clipContent: true`** in `layout` clips the native view to the box's `borderRadius`. Set it
  whenever the box has rounded corners and the view fills it (a map, a camera).

`verify-config.py` reports each of these.

## What you tell the user

A custom element is a route the user takes **with an app release**, so the reply says so once,
in this shape. The shape to follow, not words to copy:

> The plant is a **custom element**: a box on the screen that your app fills with its own
> Lottie animation, so it can grow to each user's real streak. Flow Builder has no Lottie element
> of its own yet.
>
> - **In the flow now:** a 220 pt box on the Streak screen, Type `lottie_animation`, ID
>   `streak_plant`. Until your app draws it, users see a still picture of the plant there.
> - **In your app:** a view for that Type and ID that plays the Lottie file up to the streak.
>   It needs Adapty iOS SDK 4.4 or later and ships with your next app release; older versions keep
>   the picture. How it is set up: https://adapty.io/docs/custom-element-lottie-animation
>
> I can add that view to your app. Want me to?

- Name the **Type and ID** exactly: the user types them into code or sees them in the builder.
- Say what users see until the app draws it (the fallback), and that it ships with an **app
  release**.
- Name the app's own SDK (iOS or Android) in the "In your app" line. When the app is neither,
  say that its platform shows the fallback for now.
- Link the recipe for the app's platform from [Docs per platform](#docs-per-platform), or its
  setup page when the template has no recipe, without `.md`. With no app yet, link the general
  page https://adapty.io/docs/flow-custom-elements.
- **Offer the app code, and on a yes write it** (below). Never a snippet in the reply in place of
  the change.
- List the custom element in the phase 5 summary like any other element, and never call it
  "not possible": the builder has no element for the thing, the app can draw it.

## On a yes: the app's view

The app side is this skill's, like a custom tag's: `adapty-integration` gets the SDK into an
app, and a custom element comes later in the app's life. Read the Type and ID list off the bytes
you wrote, never from memory:

```bash
jq -r '[.screens[], (.components // {} | .[])] | .[] | (.elements.map // .map) | .[]
  | select(.type == "custom-element") | "\(.props.customType)\t\(.props.customElementId)"' flow.json
```

1. **Find the app's code.** Usually the workspace you are in; if no app project is reachable,
   ask for its path rather than guess one.
2. **Check the platform, and fetch its pages** from [Docs per platform](#docs-per-platform): the
   setup page, and the template's recipe when it has one. Fetch only that platform's column. The
   pages own every platform detail: the SDK version, the resolver and its registration, the
   library, where the file goes, the permission declaration, the device test. This file owns the
   rules they serve. A platform with no column gets no code: say its users see the fallback until
   its SDK supports custom elements, and stop. An app below the SDK version the setup page names
   needs the update first: say so, ask before touching the dependency, and on a yes apply the
   SDK update page.
3. **Find where the app shows flows.** None: the app does not render flows yet, which is SDK
   integration, so offer `adapty-integration` instead. Then pick where the view is registered:
   - **App-wide, once at launch: the default.** Every flow and A/B test that uses the Type then
     gets the view with no app release. Add a case to the app's existing app-wide registration
     when it has one.
   - **For one flow, when its configuration is fetched:** only when the view needs data the app
     has only when it opens that flow, such as answers from an earlier flow
     ([chart.md](custom-elements/chart.md)). Those values are fixed at the fetch, and this
     registration replaces the app-wide one in that flow, so it hands every other Type on to the
     app-wide one.
4. **Write the view** the template's "What the app's view does" describes, in its own file, with
   the library the recipe names added the way the project adds packages; a template with no
   recipe uses the platform's usual library for it.
5. **Register it for the Type**, as the setup page says. Match the Type and ID letter for
   letter, return no view for any other pair and whenever the view's file or data is missing, so users see the fallback. A permission
   returns no view only when it was denied before the screen opened; when it is not answered
   yet, the view asks for it, and when the user denies it on the screen, the view stays and says
   how to allow it in Settings. Data that comes from the app (the streak, the level) is read
   where the app already holds it, and the view observes it, so the screen shows the current
   value each time it opens; a value copied in at registration stays as it was. Ask when you
   cannot find the data, never pass a sample value.
6. **Build if the project lets you,** and show the diff in one line per file. Add any
   permission declaration the pages name.

Keep the change to the view, its registration and what they need. The app's models and its
other screens are not this skill's to edit.

## Docs per platform

Agents fetch these `.md` URLs; the user gets the same URL without `.md`. A recipe's Type, ID and
fallback conditions are the template's; its code is the platform's.

| Page | iOS | Android |
| :--- | :--- | :--- |
| Setup: the view, the resolver, app-wide or per-flow registration, the device test | https://adapty.io/docs/ios-flow-custom-elements.md | https://adapty.io/docs/android-flow-custom-elements.md |
| Recipe: [Lottie](custom-elements/lottie.md) | https://adapty.io/docs/custom-element-lottie-animation.md | https://adapty.io/docs/android-custom-element-lottie-animation.md |
| Recipe: [chart](custom-elements/chart.md) | https://adapty.io/docs/custom-element-interactive-chart.md | https://adapty.io/docs/android-custom-element-interactive-chart.md |
| Recipe: [map](custom-elements/map.md) | https://adapty.io/docs/custom-element-map.md | https://adapty.io/docs/android-custom-element-map.md |
| SDK update to 4.4 | https://adapty.io/docs/migration-to-ios-sdk-44.md | https://adapty.io/docs/migration-to-android-sdk-44.md |

A new platform or recipe is a new column or row here, never a new file. Where a page does not
show a call, read the SDK source at the release tag the app depends on
([iOS](https://github.com/adaptyteam/AdaptySDK-iOS), [Android](https://github.com/adaptyteam/AdaptySDK-Android),
search it for "custom element") rather than guess a signature. What the pages do not say yet:

- **iOS:** flows need iOS 16, so an app that targets iOS 15 wraps its flow code in an
  availability check when it updates to 4.4.
- **Android camera:** CameraX returns the camera provider as a Guava future, and the Adapty UI
  module brings Guava at runtime only: add `com.google.guava:guava` (the `-android` version the
  Adapty UI module resolves to) as the app's own dependency, or the app does not compile.

## Checking it

A render can confirm the box's size and the fallback's look, nothing else. When `flows config
preview` refuses a screen holding the box, render a copy with the box's `type` set to `stack` (its
props and children unchanged) to check the layout, and say the render is that stand-in. Say in the
honest-scope line what no render shows: the native
view is checked on a device, with a build that serves the Type, on a registered test device so
the published flow is not cached. The app-side checks, in plain words, are in each template.
