# Template: a map

Rules, shape and the reply: [custom-elements.md](../custom-elements.md). This file holds only what
is particular to a map.

**Fits** a live map: places near the user (gyms, stores, meeting points), the user's own location,
a route. The user can pan and zoom inside it.

**Does not fit** a map that is only decoration: a picture of a map, as an `image`.

## The box

| Field | Value |
| :--- | :--- |
| Type | `map` |
| ID | what the map shows, such as `fitness_centers` |
| Height | fixed, never `hug`: a map has no height of its own and collapses. 240–320 pt reads well on a phone |
| Width | `fill`, with `borderRadius` and `clip=True` when it sits in a card |

```python
fk.custom_element('map', 'fitness_centers', fixed_h=280, corner=fk.radius(16), clip=True,
                  fallback=[fk.image(fk.PLACEHOLDER, fixed_h=280, fit='cover',
                                     corner=fk.radius(16))])
```

**Fallback:** a picture of a map in the app's style, `fit='cover'`.

**Around the box:** one line above the map that says why the app wants the location ("Find gyms
near you"). The system location prompt appears when the map opens, and this line is the context
for it. A flow element cannot ask for the permission itself.

**Placement:** never inside a `carousel` or another container that answers a swipe: a drag on the
map would move both.

## What the app's view does

- Asks for location access when the map appears, only if the user has not answered yet; the app
  needs its location usage description (`NSLocationWhenInUseUsageDescription`) in `Info.plist`.
- Finds the places itself and drops a marker for each one. The flow passes nothing.
- Draws nothing when the user denied location access, so users see the fallback rather than an
  empty map.
- Apple's newest map view needs iOS 17; on iOS 16 the app either uses the older map view or
  draws nothing.

Docs: https://adapty.io/docs/custom-element-map.md

## On the device

Allow location, check the markers, pan and zoom; deny location in Settings and reopen the screen
to see the fallback.
